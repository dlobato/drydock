"""Private ANTA transport, acceptance reports, and unconditional lab cleanup."""

import base64
from contextlib import contextmanager
from collections import Counter
from importlib.metadata import version
from ipaddress import IPv4Address
import json
from pathlib import Path
import signal
import ssl
import tempfile
from urllib.request import Request, urlopen
from uuid import uuid4
import xml.etree.ElementTree as ET

from .anta import prepare, converge
from .cloud import create_lab, delete_lab, lab_record, validate_request
from .core import UserError, ENV_LABEL, LAB_LABEL, NODES, now, readiness, save, wait_for


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
    if not owned or not owned["metadata"].get("labels", {}).items() >= {
            ENV_LABEL: env.name, LAB_LABEL: lab}.items():
        raise UserError("Lab namespace ownership does not match.")
    items = env.objects("topologies.c9s.run,nodes.c9s.run,links.c9s.run,pods,services", namespace)
    errors = readiness(items)
    if record["state"] != "running" or record["expires_at"] <= now():
        errors.append("lab is expired or not running")
    services = {s["metadata"]["name"]: s for s in items if s["kind"] == "Service" and s["metadata"]["name"] in NODES}
    if set(services) != NODES or any(s["spec"].get("type") != "ClusterIP" or not any(
            p["port"] == 443 and p.get("protocol", "TCP") == "TCP" for p in s["spec"].get("ports", []))
            for s in services.values()):
        errors.append("private eAPI services are missing")
    return record, items, errors


def connections(items):
    pods = [item for item in items if item["kind"] == "Pod" and
            item["metadata"].get("labels", {}).get("c9s.run/direct-workload") in NODES]
    if len(pods) != len(NODES) or {
            pod["metadata"]["labels"]["c9s.run/direct-workload"] for pod in pods} != NODES:
        raise UserError("Exactly one switch Pod is required for each device.")
    inventory = []
    for pod in pods:
        metadata = pod["metadata"]
        name = metadata["labels"]["c9s.run/direct-workload"]
        address = IPv4Address(pod.get("status", {}).get("podIP", ""))
        if (not address.is_private or address.is_loopback or address.is_link_local
                or address.is_unspecified or address.is_reserved or not metadata.get("uid")
                or metadata.get("deletionTimestamp")):
            raise UserError("Switch Pods require current identities and private IPv4 addresses.")
        inventory.append({"name": name, "host": str(address), "port": 443, "tags": [name],
                          "pod": metadata["name"], "pod_uid": metadata["uid"]})
    if len({host["host"] for host in inventory}) != len(NODES):
        raise UserError("Switch Pod addresses must be distinct.")
    return sorted(inventory, key=lambda host: host["name"])


def eapi(host, password, commands):
    authorization = base64.b64encode(("labadmin:" + password).encode()).decode()
    request = Request(f"https://{host['host']}:{host['port']}/command-api",
        data=json.dumps({"jsonrpc": "2.0", "method": "runCmds", "id": "drydock",
                         "params": {"version": 1, "cmds": commands, "format": "json"}}).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Basic " + authorization})
    # shortcut: the private demo skips certificate verification by user agreement; revisit before wider use.
    with urlopen(request, context=ssl._create_unverified_context(), timeout=10) as response:
        result = json.loads(response.read(1024 * 1024))
    if "error" in result:
        raise RuntimeError("eAPI rejected a diagnostic command.")
    return result["result"]


def probe(inventory, password):
    versions = {}
    for host in inventory:
        result = eapi(host, password, ["show hostname", "show version"])
        if result[0].get("hostname") != host["name"]:
            raise UserError("Management API identity differs from the bundle.")
        versions[host["name"]] = result[1]["version"]
    return versions


def available_probe(env, lab, password):
    try:
        record, items, errors = snapshot(env, lab)
        if errors:
            return None
        inventory = connections(items)
        return inventory, probe(inventory, password)
    except Exception:
        return None


def network_diagnostics(inventory, password):
    results = {}
    for host in inventory:
        commands = ["show ip bgp summary", "show bgp evpn summary", "show interfaces status"]
        if host["name"].startswith("leaf"):
            commands += ["show mlag", "show mlag config-sanity", "show vxlan vni"]
        try:
            results[host["name"]] = dict(zip(commands, eapi(host, password, commands), strict=True))
        except Exception:
            results[host["name"]] = {"error": "Read-only network diagnostics unavailable."}
    return results


def status(env, lab, password):
    record, items, errors = snapshot(env, lab)
    versions = {}
    inventory = []
    if not errors:
        try:
            inventory = connections(items)
            versions = probe(inventory, password)
        except Exception:
            errors.append("an authenticated management API is unavailable or has the wrong identity")
    return {"lab": lab, "ready": not errors, "errors": errors, "record": record,
            "eos_versions": versions, "observed_at": now(), "inventory": [
                {**host, "namespace": env.name + "-" + lab, "transport": "private Pod-IP HTTPS"}
                for host in inventory]}


def acceptance(results, expected):
    expected = Counter(expected)
    if not expected:
        return {"passed": False, "required": 0, "failures": [{"error": "No required tests."}]}
    observed = {}
    for result in results:
        observed.setdefault((result["name"], result["test"], result.get("description", "")), []).append(result["result"])
    failures = [{"name": name, "test": test, "results": observed.get((name, test, description), ["missing"])}
                for name, test, description in sorted(expected) if observed.get((name, test, description)) != ["success"] * expected[(name, test, description)]]
    failures += [{"name": r["name"], "test": r["test"], "results": [r["result"]]}
                 for r in results if (r["name"], r["test"], r.get("description", "")) not in expected and r["result"] != "success"]
    return {"passed": not failures, "required": sum(expected.values()), "failures": failures}


def reports(directory, results, expected):
    expected = Counter(expected)
    outcome = acceptance(results, expected)
    save(directory / "anta.json", results)
    suite = ET.Element("testsuite", name="Drydock ANTA", tests=str(sum(expected.values())))
    failures = 0
    for (name, test, description), count in sorted(expected.items()):
        observed = [r for r in results if (r["name"], r["test"], r.get("description", "")) == (name, test, description)]
        for index in range(count):
            case = ET.SubElement(suite, "testcase", classname=name, name=f"{test}[{index + 1}]")
            result = observed[index] if index < len(observed) else {"result": "missing", "messages": []}
            if result["result"] != "success" or len(observed) != count:
                failure = ET.SubElement(case, "failure", message=result["result"] if len(observed) <= count else "duplicate")
                failure.text = "\n".join(result.get("messages", []))
                failures += 1
    suite.set("failures", str(failures))
    (directory / "anta.xml").write_bytes(ET.tostring(suite, encoding="utf-8", xml_declaration=True))
    return outcome


def diagnostics(env, lab):
    # Never retain manifests, Secret data, startup configurations, or arbitrary container logs.
    record, items, errors = snapshot(env, lab)
    return {"lab": lab, "errors": errors, "resources": [
        {"kind": item["kind"], "name": item["metadata"]["name"],
         "generation": item["metadata"].get("generation"), "status": {
             key: item.get("status", {}).get(key) for key in
             ("readiness", "phase", "topologyReady", "topologyState", "observedGeneration")}}
        for item in items]}


def cleanup(env, lab, timeout=1800):
    last = {}

    def attempt():
        nonlocal last
        try:
            last = delete_lab(env, lab)
        except Exception as error:
            last = {"lab": lab, "deleted": False, "error": type(error).__name__}
        return last if last["deleted"] else None

    try:
        return wait_for(attempt, timeout, 15)
    except TimeoutError:
        return last


def test_flow(env, bundle, provenance, password, output, lifetime=120, ready_timeout=1200, test_timeout=600):
    validate_request(bundle, provenance, lifetime)
    if not password:
        raise UserError("Set DRYDOCK_LAB_PASSWORD to the bundle labadmin password.")
    if ready_timeout < 1 or test_timeout < 1 or ready_timeout + test_timeout >= lifetime * 60:
        raise UserError("Readiness and test deadlines must fit inside the lab lifetime.")
    lab = "lab-" + uuid4().hex[:12]
    directory = Path(output) / lab
    directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    result = {"lab": lab, "bundle_digest": bundle.digest, "provenance": provenance,
              "reports": str(directory), "passed": False, "tests": {"passed": False},
              "runtime": {"anta": version("anta"), "pyavd": version("pyavd"), "gke_requested": env.cluster_version,
                          "clabernetes": env.clabernetes_version}}
    save(directory / "run.json", result)
    rows = []
    # Ownership and this local identity exist even when create does not return.
    with tempfile.TemporaryDirectory() as private, cancellation():
        structured, expected = prepare(bundle, private, directory)
        try:
            create_lab(env, bundle, provenance, lifetime, lab)
            hosts, result["runtime"]["eos"] = wait_for(lambda: available_probe(env, lab, password), ready_timeout)
            save(directory / "inventory.json", {"anta_inventory": {"hosts": hosts}})
            try:
                result["tests"] = converge(hosts, structured, directory, expected, test_timeout, rows)
            finally:
                result["tests"] = acceptance(rows, expected)
                save(directory / "network.json", network_diagnostics(hosts, password))
        except (Exception, KeyboardInterrupt) as error:
            result["error"] = type(error).__name__
        finally:
            # Ignore repeated interrupts only while immediate cleanup runs; expiry survives SIGKILL.
            handlers = {s: signal.signal(s, signal.SIG_IGN) for s in (signal.SIGINT, signal.SIGTERM)}
            try:
                for name, action in (
                    ("report_error", lambda: reports(directory, rows, expected)),
                    ("diagnostic_error", lambda: save(directory / "diagnostics.json", diagnostics(env, lab))),
                ):
                    try:
                        action()
                    except Exception as error:
                        result[name] = type(error).__name__
                result["cleanup"] = cleanup(env, lab)
            finally:
                for signum, handler in handlers.items():
                    signal.signal(signum, handler)
    result["passed"] = (result["tests"]["passed"] and result["cleanup"].get("deleted", False)
                        and not any(key.endswith("error") for key in result))
    save(directory / "run.json", result)
    save(directory / "events.json", [{"event": key, "outcome": result[key]} for key in ("tests", "cleanup")])
    return result
