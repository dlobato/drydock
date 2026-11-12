"""Authenticated management readiness, safe diagnostics, and immediate lab cleanup."""

import base64
import json
import signal
import ssl
import time
from contextlib import contextmanager
from ipaddress import IPv4Address
from urllib.request import Request, urlopen

from .core import (
    ALLOCATION_LABEL,
    ENV_LABEL,
    LAB_LABEL,
    UserError,
    now,
    readiness,
    wait_for,
)
from .lifecycle import delete_lab, lab_record, write_record


class Canceled(Exception):
    pass


def cancel(signum, frame):
    raise Canceled("Run canceled.")


@contextmanager
def cancellation():
    previous = {s: signal.signal(s, cancel) for s in (signal.SIGTERM, signal.SIGINT)}
    try:
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def snapshot(env, lab):
    record = lab_record(env, lab)
    if not record:
        raise UserError("Lab ownership record does not exist.")
    namespace = env.name + "-" + lab
    namespaces = env.objects("namespaces")
    owned = next((n for n in namespaces if n["metadata"]["name"] == namespace), None)
    if (
        not owned
        or not owned["metadata"].get("labels", {}).items()
        >= {
            ENV_LABEL: env.name,
            LAB_LABEL: lab,
            ALLOCATION_LABEL: record["allocation_id"],
        }.items()
    ):
        raise UserError("Lab namespace ownership does not match.")
    items = env.objects(
        "topologies.c9s.run,nodes.c9s.run,links.c9s.run,pods,services", namespace
    )
    names = set(record["switches"])
    errors = readiness(items, names, record["link_count"])
    if record["state"] != "running" or record["expires_at"] <= now():
        errors.append("lab is expired or not running")
    services = {
        s["metadata"]["name"]: s
        for s in items
        if s["kind"] == "Service" and s["metadata"]["name"] in names
    }
    if set(services) != names or any(
        s["spec"].get("type") != "ClusterIP"
        or not any(
            p["port"] == 443 and p.get("protocol", "TCP") == "TCP"
            for p in s["spec"].get("ports", [])
        )
        for s in services.values()
    ):
        errors.append("private eAPI services are missing")
    return record, items, errors


def connections(items, names):
    names = set(names)
    pods = [
        item
        for item in items
        if item["kind"] == "Pod"
        and item["metadata"].get("labels", {}).get("c9s.run/direct-workload") in names
    ]
    if (
        len(pods) != len(names)
        or {pod["metadata"]["labels"]["c9s.run/direct-workload"] for pod in pods}
        != names
    ):
        raise UserError("Exactly one switch Pod is required for each device.")
    inventory = []
    for pod in pods:
        metadata = pod["metadata"]
        name = metadata["labels"]["c9s.run/direct-workload"]
        address = IPv4Address(pod.get("status", {}).get("podIP", ""))
        if (
            not address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_unspecified
            or address.is_reserved
            or not metadata.get("uid")
            or metadata.get("deletionTimestamp")
        ):
            raise UserError(
                "Switch Pods require current identities and private IPv4 addresses."
            )
        inventory.append(
            {
                "name": name,
                "host": str(address),
                "port": 443,
                "tags": [name],
                "pod": metadata["name"],
                "pod_uid": metadata["uid"],
            }
        )
    if len({host["host"] for host in inventory}) != len(names):
        raise UserError("Switch Pod addresses must be distinct.")
    return sorted(inventory, key=lambda host: host["name"])


def eapi(host, password, commands):
    authorization = base64.b64encode(("labadmin:" + password).encode()).decode()
    request = Request(
        f"https://{host['host']}:{host['port']}/command-api",
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "runCmds",
                "id": "drydock",
                "params": {"version": 1, "cmds": commands, "format": "json"},
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Basic " + authorization,
        },
    )
    # shortcut: the private demo skips certificate verification by user agreement; revisit before wider use.
    with urlopen(
        request, context=ssl._create_unverified_context(), timeout=10
    ) as response:
        result = json.loads(response.read(1024 * 1024))
    if "error" in result:
        raise RuntimeError("eAPI rejected a diagnostic command.")
    return result["result"]


def probe(inventory, password, *, deadline=None):
    versions = {}
    for host in inventory:
        if deadline is not None and now() >= deadline:
            raise TimeoutError("Management readiness deadline elapsed.")
        result = eapi(host, password, ["show hostname", "show version"])
        if result[0].get("hostname") != host["name"]:
            raise UserError("Management API identity differs from the bundle.")
        versions[host["name"]] = result[1]["version"]
    return versions


def available_probe(env, lab, password):
    try:
        result = status(env, lab, password)
        if result["ready"]:
            return result["inventory"], result["eos_versions"]
    except Exception:
        return None


def scheduling_diagnostics(items):
    return [
        {"pod": item["metadata"]["name"], "reason": "Unschedulable"}
        for item in items
        if item["kind"] == "Pod"
        and not item["metadata"].get("deletionTimestamp")
        and any(
            condition.get("type") == "PodScheduled"
            and condition.get("status") == "False"
            and condition.get("reason") == "Unschedulable"
            for condition in item.get("status", {}).get("conditions", [])
        )
    ]


def status(env, lab, password):
    record, items, errors = snapshot(env, lab)
    scheduling = scheduling_diagnostics(items)
    deadline = record["expires_at"]
    if "ready_at" not in record:
        deadline = min(deadline, record["startup_deadline"])
    if now() >= deadline:
        errors.append("readiness deadline elapsed")
    if scheduling:
        errors.append("switch workloads are waiting for scheduling capacity")
    infrastructure_ready = not errors
    versions = {}
    inventory = []
    if not errors:
        try:
            inventory = connections(items, record["switches"])
            versions = probe(inventory, password, deadline=deadline)
            record, current_items, current_errors = snapshot(env, lab)
            errors.extend(current_errors)
            infrastructure_ready = not current_errors
            scheduling = scheduling_diagnostics(current_items)
            if connections(current_items, record["switches"]) != inventory:
                errors.append("switch endpoints changed during authentication")
                inventory = []
                versions = {}
        except Exception:
            errors.append(
                "an authenticated management API is unavailable or has the wrong identity"
            )
    observed = now()
    if observed >= deadline:
        errors.append("readiness deadline elapsed")
    if record["expires_at"] <= observed:
        phase = "expired"
    elif record["state"] in {"deleting", "deleted"}:
        phase = record["state"]
    elif "ready_at" not in record and record["startup_deadline"] <= observed:
        phase = "startup_timeout"
    elif not errors:
        phase = "ready"
        if "ready_at" not in record:
            record["ready_at"] = observed
            write_record(env, record)
    elif scheduling:
        phase = "waiting_for_capacity"
    else:
        phase = "management_unavailable" if infrastructure_ready else "starting"
    return {
        "lab": lab,
        "phase": phase,
        "ready": not errors,
        "errors": list(dict.fromkeys(errors)),
        "scheduling": scheduling,
        "record": record,
        "eos_versions": versions,
        "observed_at": observed,
        "inventory": [
            {
                **host,
                "namespace": env.name + "-" + lab,
                "transport": "private Pod-IP HTTPS",
            }
            for host in inventory
        ],
    }


def wait_ready(env, lab, password):
    try:
        while True:
            result = status(env, lab, password)
            if result["ready"]:
                return result
            if result["phase"] in {"startup_timeout", "expired", "deleting", "deleted"}:
                break
            record = result["record"]
            deadline = record["expires_at"]
            if "ready_at" not in record:
                deadline = min(deadline, record["startup_deadline"])
            time.sleep(max(0, min(10, deadline - now())))
    except (Exception, KeyboardInterrupt) as error:
        result = {"lab": lab, "ready": False, "error": type(error).__name__}
    result["cleanup"] = cleanup(env, lab)
    return result


def diagnostics(env, lab):
    # Never retain manifests, Secret data, startup configurations, or arbitrary container logs.
    record, items, errors = snapshot(env, lab)
    return {
        "lab": lab,
        "errors": errors,
        "scheduling": scheduling_diagnostics(items),
        "resources": [
            {
                "kind": item["kind"],
                "name": item["metadata"]["name"],
                "generation": item["metadata"].get("generation"),
                "status": {
                    key: item.get("status", {}).get(key)
                    for key in (
                        "readiness",
                        "phase",
                        "topologyReady",
                        "topologyState",
                        "observedGeneration",
                    )
                },
            }
            for item in items
        ],
    }


def cleanup(env, lab, timeout=1800, *, allocation_id=None):
    last = {}

    def attempt():
        nonlocal last
        try:
            last = delete_lab(env, lab, allocation_id=allocation_id)
        except UserError as error:
            return {"lab": lab, "deleted": False, "error": str(error)}
        except Exception as error:
            last = {"lab": lab, "deleted": False, "error": type(error).__name__}
        return last if last["deleted"] else None

    try:
        return wait_for(attempt, timeout, 15)
    except TimeoutError:
        return last
