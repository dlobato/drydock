"""Kubernetes ownership records, switch workloads, and independent lab expiry."""

import json
import re
from uuid import uuid4

import yaml

from .core import UserError, ENV_LABEL, LAB_LABEL, now


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
    records = env.objects("configmaps", env.namespace, f"{ENV_LABEL}={env.name},{LAB_LABEL}={lab}")
    if not records:
        return None
    record = json.loads(records[0]["data"]["record"])
    if record["id"] != lab or record["environment"] != env.name:
        raise UserError("Lab ownership record does not match its labels.")
    record["resource_version"] = records[0]["metadata"]["resourceVersion"]
    return record


def write_record(env, record, create=False):
    version = record.pop("resource_version", None)
    obj = {"apiVersion": "v1", "kind": "ConfigMap",
           "metadata": object_meta(env, record["id"], env.namespace, record["id"]),
           "data": {"record": json.dumps(record)}}
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
        raise UserError("Allocation stopped because the lab expired or cleanup started.")
    return record


def validate_request(bundle, provenance, lifetime):
    if type(lifetime) is not int or not 1 <= lifetime <= 240:
        raise UserError("Lab lifetime must be between 1 and 240 minutes.")
    if not all(isinstance(provenance.get(key), str) and provenance[key].strip()
               for key in ("repository", "commit", "run", "attempt")):
        raise UserError("Supply repository, commit, run, and attempt identity.")
    image = bundle.topology["topology"]["kinds"]["arista_ceos"]["image"]
    registry = image.split("/")[0]
    if not re.fullmatch(r"[a-z]+-[a-z]+[0-9]-docker.pkg.dev", registry):
        raise UserError("The demo requires a cEOS digest in regional Google Artifact Registry.")
    return image, registry


def create_lab(env, bundle, provenance, lifetime=120, lab=None):
    image, registry = validate_request(bundle, provenance, lifetime)
    lab = lab or "lab-" + uuid4().hex[:12]
    check_lab(lab)
    accepted = now()
    record = {"id": lab, "environment": env.name, "accepted_at": accepted,
              "expires_at": accepted + lifetime * 60, "state": "creating",
              "bundle_digest": bundle.digest, "provenance": provenance, "registry": registry,
              "runtime": {"ceos_image": image}}
    # Commit ownership before allocating Kubernetes workloads.
    write_record(env, record, create=True)
    allocation_record(env, lab)
    namespace = env.name + "-" + lab
    env.kube("create", "-f", "-", data=json.dumps({"apiVersion": "v1", "kind": "Namespace",
             "metadata": {**object_meta(env, namespace, lab=lab), "labels": {
                 ENV_LABEL: env.name, LAB_LABEL: lab, "pod-security.kubernetes.io/enforce": "privileged"}}}))
    allocation_record(env, lab)
    files = {f"{name}.cfg": text for name, text in
             ((name, bundle.files[f"intended/configs/{name}.cfg"]) for name in bundle.interfaces)}
    files["interface_mapping.json"] = bundle.files["interface_mapping.json"]
    env.apply({"apiVersion": "v1", "kind": "Secret", "metadata": object_meta(env, "startup", namespace, lab),
               "type": "Opaque", "stringData": files})
    nodes = {}
    attachments = {}
    for name, original in bundle.topology["topology"]["nodes"].items():
        nodes[name] = {"kind": "arista_ceos", "image": image, "mgmt-ipv4": original["mgmt-ipv4"],
                       "enforce-startup-config": True,
                       "startup-config": f"/drydock/{name}.cfg", "ports": ["443/tcp"],
                       "binds": ["/drydock/interface_mapping.json:/mnt/flash/EosIntfMapping.json:ro"]}
        attachments[name] = [{"filePath": f"/drydock/{name}.cfg", "secretName": "startup", "secretPath": f"{name}.cfg"},
                             {"filePath": "/drydock/interface_mapping.json", "secretName": "startup", "secretPath": "interface_mapping.json"}]
    allocation_record(env, lab)
    topology = {"name": "fabric", "prefix": "", "mgmt": {**bundle.topology["mgmt"], "network": lab},
                "topology": {"nodes": nodes, "links": bundle.topology["topology"]["links"]}}
    env.apply({"apiVersion": "c9s.run/v1alpha1", "kind": "Topology",
               "metadata": object_meta(env, "fabric", namespace, lab), "spec": {
                   "expose": {"exposeType": "ClusterIP", "disableAutoExpose": True},
                   "deployment": {"filesFromSecret": attachments,
                       "resources": {"default": {"requests": {"cpu": "1", "memory": "2Gi"}, "limits": {"cpu": "2", "memory": "3Gi"}}}},
                   "definition": {"containerlab": yaml.safe_dump(topology)}}})
    record = allocation_record(env, lab)
    record["state"] = "running"
    write_record(env, record)
    return record


def delete_lab(env, lab):
    check_lab(lab)
    record = lab_record(env, lab)
    namespace = env.name + "-" + lab
    errors = []
    if record:
        record["state"] = "deleting"
        record["overdue"] = now() > record["expires_at"] + 1800
        write_record(env, record)
    namespaces = env.objects("namespaces")
    for item in namespaces:
        if item["metadata"]["name"] == namespace:
            if not item["metadata"].get("labels", {}).items() >= {ENV_LABEL: env.name, LAB_LABEL: lab}.items():
                raise UserError("Refusing to delete a namespace with different ownership.")
            try:
                env.kube("delete", "namespace", namespace, "--wait=false", "--ignore-not-found")
            except (RuntimeError, TimeoutError) as error:
                errors.append(str(error))
    remaining_namespace = any(item["metadata"]["name"] == namespace for item in env.objects("namespaces"))
    complete = not remaining_namespace and not errors
    result = {"lab": lab, "deleted": complete, "namespace_remaining": remaining_namespace, "errors": errors}
    if record:
        record = lab_record(env, lab)
        record["state"] = "deleted" if complete else "deleting"
        record["cleanup"] = result
        record["overdue"] = now() > record["expires_at"] + 1800
        write_record(env, record)
    return result


def reap(env):
    outcomes = []
    records = env.objects("configmaps", env.namespace, f"{ENV_LABEL}={env.name},{LAB_LABEL}")
    for item in records:
        record = json.loads(item["data"]["record"])
        # Revisit deleted records too: an accepted asynchronous allocation can appear late.
        if record["expires_at"] <= now() or record["state"] in {"deleting", "deleted"}:
            try:
                outcomes.append(delete_lab(env, record["id"]))
            except Exception as error:
                outcomes.append({"lab": record["id"], "deleted": False, "error": str(error),
                                 "overdue": now() > record["expires_at"] + 1800})
    return outcomes
