"""Kubernetes ownership records, switch workloads, and independent lab expiry."""

import base64
import json
import re
from copy import deepcopy
from uuid import uuid4

import yaml

from .core import ALLOCATION_LABEL, ENV_LABEL, LAB_LABEL, PAYLOAD_LIMIT, UserError, now


def object_meta(env, name, namespace=None, lab=None):
    metadata = {"name": name, "labels": {ENV_LABEL: env.name}}
    if namespace:
        metadata["namespace"] = namespace
    if lab:
        metadata["labels"][LAB_LABEL] = lab
    return metadata


def check_lab(lab):
    if not re.fullmatch(r"lab-[a-f0-9]{12}", lab):
        raise UserError("Invalid lab identifier.")


def lab_record(env, lab):
    check_lab(lab)
    records = env.objects(
        "configmaps", env.namespace, f"{ENV_LABEL}={env.name},{LAB_LABEL}={lab}"
    )
    if not records:
        return None
    record = json.loads(records[0]["data"]["record"])
    if record["id"] != lab or record["environment"] != env.name:
        raise UserError("Lab ownership record does not match its labels.")
    record["resource_version"] = records[0]["metadata"]["resourceVersion"]
    return record


def write_record(env, record, create=False):
    version = record.pop("resource_version", None)
    obj = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": object_meta(env, record["id"], env.namespace, record["id"]),
        "data": {"record": json.dumps(record)},
    }
    if create:
        env.kube("create", "-f", "-", data=json.dumps(obj))
    else:
        if not version:
            raise UserError("Updating ownership requires its resource version.")
        obj["metadata"]["resourceVersion"] = version
        env.kube("replace", "-f", "-", data=json.dumps(obj))


def allocation_record(env, lab):
    record = lab_record(env, lab)
    if not record or record["state"] != "creating" or record["expires_at"] <= now():
        raise UserError(
            "Allocation stopped because the lab expired or cleanup started."
        )
    return record


def validate_request(bundle, provenance, lifetime):
    if type(lifetime) is not int or not 1 <= lifetime <= 240:
        raise UserError("Lab lifetime must be between 1 and 240 minutes.")
    if not all(
        isinstance(provenance.get(key), str) and provenance[key].strip()
        for key in ("repository", "commit", "run", "attempt")
    ):
        raise UserError("Supply repository, commit, run, and attempt identity.")
    image = bundle.topology["topology"]["kinds"]["arista_ceos"]["image"]
    registry = image.split("/")[0]
    if "/" not in image or not (
        "." in registry or ":" in registry or registry == "localhost"
    ):
        registry = "docker.io"
    return image, registry


def lab_manifests(env, bundle, lab):
    namespace = env.name + "-" + lab
    definition = bundle.topology["topology"]
    kind = definition["kinds"]["arista_ceos"]
    files = {node["startup-config"] for node in definition["nodes"].values()}
    for node in (kind, *definition["nodes"].values()):
        files.update(bind.split(":")[0] for bind in node.get("binds", []))
    secrets: list[dict] = []
    locations = {}
    size = 0
    for index, path in enumerate(sorted(files)):
        content = bundle.files[path].encode()
        if not secrets or size + len(content) > PAYLOAD_LIMIT:
            secrets.append(
                {
                    "apiVersion": "v1",
                    "kind": "Secret",
                    "metadata": object_meta(
                        env, f"startup-{len(secrets)}", namespace, lab
                    ),
                    "type": "Opaque",
                    "data": {},
                }
            )
            size = 0
        key = f"file-{index}"
        secrets[-1]["data"][key] = base64.b64encode(content).decode()
        locations[path] = {
            "filePath": "/drydock/" + key,
            "secretName": secrets[-1]["metadata"]["name"],
            "secretPath": key,
        }
        size += len(content)
    topology = deepcopy(bundle.topology)
    runtime = topology["topology"]
    for settings in (runtime["kinds"]["arista_ceos"], *runtime["nodes"].values()):
        if "binds" in settings:
            settings["binds"] = [
                locations[source]["filePath"] + ":" + destination
                for source, destination in (
                    bind.split(":", 1) for bind in settings["binds"]
                )
            ]
    runtime["kinds"]["arista_ceos"]["enforce-startup-config"] = True
    attachments = {}
    for name, original in definition["nodes"].items():
        startup = locations[original["startup-config"]]
        attachments[name] = [startup]
        for bind in original.get("binds") or kind.get("binds", []):
            source = locations[bind.split(":")[0]]
            attachments[name].append(source)
        runtime["nodes"][name]["startup-config"] = startup["filePath"]
        runtime["nodes"][name]["ports"] = ["443/tcp"]
    topology["prefix"] = ""
    topology["mgmt"] = {**topology.get("mgmt", {}), "network": lab}
    manifests = [
        *secrets,
        {
            "apiVersion": "c9s.run/v1alpha1",
            "kind": "Topology",
            "metadata": object_meta(env, "fabric", namespace, lab),
            "spec": {
                "expose": {"exposeType": "ClusterIP", "disableAutoExpose": True},
                "deployment": {
                    "filesFromSecret": attachments,
                    "resources": {
                        "default": {
                            "requests": {"cpu": "1", "memory": "2Gi"},
                            "limits": {"cpu": "2", "memory": "3Gi"},
                        }
                    },
                },
                "definition": {"containerlab": yaml.safe_dump(topology)},
            },
        },
    ]
    if any(len(json.dumps(obj).encode()) > 1024 * 1024 for obj in manifests):
        raise UserError("A lab resource exceeds the 1 MiB manifest limit.")
    return manifests


def create_lab(env, bundle, provenance, lifetime=120, lab=None, *, allocation_id=None):
    image, registry = validate_request(bundle, provenance, lifetime)
    allocation_id = allocation_id or uuid4().hex
    lab = lab or "lab-" + allocation_id[:12]
    check_lab(lab)
    manifests = lab_manifests(env, bundle, lab)
    accepted = now()
    record = {
        "id": lab,
        "allocation_id": allocation_id,
        "environment": env.name,
        "accepted_at": accepted,
        "expires_at": accepted + lifetime * 60,
        "state": "creating",
        "bundle_digest": bundle.digest,
        "provenance": provenance,
        "registry": registry,
        "runtime": {"ceos_image": image},
        "switches": sorted(bundle.topology["topology"]["nodes"]),
        "link_count": len(bundle.topology["topology"].get("links", [])),
    }
    # Commit ownership before allocating Kubernetes workloads.
    write_record(env, record, create=True)
    allocation_record(env, lab)
    namespace = env.name + "-" + lab
    env.kube(
        "create",
        "-f",
        "-",
        data=json.dumps(
            {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {
                    **object_meta(env, namespace, lab=lab),
                    "labels": {
                        ENV_LABEL: env.name,
                        LAB_LABEL: lab,
                        ALLOCATION_LABEL: record["allocation_id"],
                        "pod-security.kubernetes.io/enforce": "privileged",
                    },
                },
            }
        ),
    )
    for manifest in manifests:
        allocation_record(env, lab)
        # Creation avoids a second credential-bearing copy in apply annotations.
        env.kube("create", "-f", "-", data=json.dumps(manifest))
    record = allocation_record(env, lab)
    record["state"] = "running"
    write_record(env, record)
    return record


def delete_lab(env, lab, *, allocation_id=None):
    check_lab(lab)
    record = lab_record(env, lab)
    if allocation_id is not None and (
        not record or record["allocation_id"] != allocation_id
    ):
        raise UserError("Lab creation ownership is unconfirmed. Cleanup refused.")
    namespace = env.name + "-" + lab
    errors = []
    if record:
        record["state"] = "deleting"
        record["overdue"] = now() > record["expires_at"] + 1800
        write_record(env, record)
    namespaces = env.objects("namespaces")
    for item in namespaces:
        if item["metadata"]["name"] == namespace:
            if (
                not record
                or not item["metadata"].get("labels", {}).items()
                >= {
                    ENV_LABEL: env.name,
                    LAB_LABEL: lab,
                    ALLOCATION_LABEL: record["allocation_id"],
                }.items()
            ):
                raise UserError(
                    "Refusing to delete a namespace with different ownership."
                )
            try:
                env.kube(
                    "delete",
                    "--raw=/api/v1/namespaces/" + namespace,
                    "-f",
                    "-",
                    data=json.dumps(
                        {
                            "apiVersion": "v1",
                            "kind": "DeleteOptions",
                            "preconditions": {
                                key: item["metadata"][key]
                                for key in ("uid", "resourceVersion")
                            },
                        }
                    ),
                )
            except (RuntimeError, TimeoutError) as error:
                errors.append(str(error))
    remaining_namespace = any(
        item["metadata"]["name"] == namespace for item in env.objects("namespaces")
    )
    complete = not remaining_namespace and not errors
    result = {
        "lab": lab,
        "deleted": complete,
        "namespace_remaining": remaining_namespace,
        "errors": errors,
    }
    if record:
        record = lab_record(env, lab)
        record["state"] = "deleted" if complete else "deleting"
        record["cleanup"] = result
        record["overdue"] = now() > record["expires_at"] + 1800
        write_record(env, record)
    return result


def reap(env):
    outcomes = []
    records = env.objects(
        "configmaps", env.namespace, f"{ENV_LABEL}={env.name},{LAB_LABEL}"
    )
    for item in records:
        record = json.loads(item["data"]["record"])
        # Revisit deleted records too: an accepted asynchronous allocation can appear late.
        if record["expires_at"] <= now() or record["state"] in {"deleting", "deleted"}:
            try:
                outcomes.append(delete_lab(env, record["id"]))
            except Exception as error:
                outcomes.append(
                    {
                        "lab": record["id"],
                        "deleted": False,
                        "error": str(error),
                        "overdue": now() > record["expires_at"] + 1800,
                    }
                )
    return outcomes
