"""Operator-installed admission and namespaced reader bindings. No cloud access."""

import argparse
import json
import re
import ssl
import threading
import time
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yaml

from .core import (
    ALLOCATION_LABEL,
    ENV_LABEL,
    LAB_LABEL,
    Environment,
    UserError,
    now,
    require_fields,
    validate_topology,
    wait_for,
)
from .lifecycle import check_lab, lab_record, object_meta


def reader_binding(env, lab, username):
    return {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "RoleBinding",
        "metadata": object_meta(env, "lifecycle-reader", env.name + "-" + lab, lab),
        "roleRef": {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "ClusterRole",
            "name": env.name + "-lab-reader",
        },
        "subjects": [
            {"kind": "User", "apiGroup": "rbac.authorization.k8s.io", "name": username}
        ],
    }


def check_namespace(env, namespace, record):
    lab = record["id"]
    check_lab(lab)
    if (
        namespace["metadata"]["name"] != env.name + "-" + lab
        or not namespace["metadata"].get("labels", {}).items()
        >= {
            ENV_LABEL: env.name,
            LAB_LABEL: lab,
            ALLOCATION_LABEL: record["allocation_id"],
        }.items()
    ):
        raise UserError("Namespace ownership does not match the lab record.")


def validate_runtime_topology(obj, images, lab):
    spec = obj["spec"]
    require_fields(
        spec,
        {"definition", "deployment", "expose"},
        {"definition", "deployment", "expose"},
    )
    if spec["expose"] != {"exposeType": "ClusterIP", "disableAutoExpose": True}:
        raise UserError("Only private HTTPS exposure is allowed.")
    require_fields(spec["definition"], {"containerlab"}, {"containerlab"})
    require_fields(
        spec["deployment"],
        {"resources", "filesFromSecret"},
        {"resources", "filesFromSecret"},
    )
    if spec["deployment"]["resources"] != {
        "default": {
            "requests": {"cpu": "1", "memory": "2Gi"},
            "limits": {"cpu": "2", "memory": "3Gi"},
        }
    }:
        raise UserError("Unsupported switch resource requirements.")
    topology = yaml.safe_load(spec["definition"]["containerlab"])
    original = deepcopy(topology)
    definition = topology["topology"]
    if definition["kinds"]["arista_ceos"]["image"] not in images:
        raise UserError("The cEOS image is not operator-approved.")
    if topology.get("prefix") != "" or topology.get("mgmt", {}).get("network") != lab:
        raise UserError("The topology must use the isolated lab network.")
    if definition["kinds"]["arista_ceos"].get("enforce-startup-config") is not True:
        raise UserError("Complete startup configurations must be enforced.")
    attachments = spec["deployment"]["filesFromSecret"]
    if set(attachments) != set(definition["nodes"]):
        raise UserError("Payload attachments must match the switch identities.")
    files = {"lab.clab.yml": ""}

    def source(path):
        if not isinstance(path, str) or not re.fullmatch(r"/drydock/file-[0-9]+", path):
            raise UserError("Only projected startup payloads are allowed.")
        key = path.removeprefix("/drydock/")
        files[key] = ""
        return key

    kind = definition["kinds"]["arista_ceos"]
    for settings in (kind, *definition["nodes"].values()):
        if "binds" in settings:
            settings["binds"] = [
                source(bind.split(":")[0]) + ":" + bind.split(":", 1)[1]
                for bind in settings["binds"]
            ]
    for name, node in definition["nodes"].items():
        if node.pop("ports", None) != ["443/tcp"]:
            raise UserError("Only private HTTPS ports are allowed.")
        node["startup-config"] = source(node["startup-config"])
        submitted = original["topology"]["nodes"][name]
        paths = [submitted["startup-config"]] + [
            bind.split(":")[0]
            for bind in submitted.get("binds")
            or original["topology"]["kinds"]["arista_ceos"].get("binds", [])
        ]
        entries = attachments[name]
        if len(entries) != len(paths):
            raise UserError("Payload attachments must match the referenced files.")
        for entry, path in zip(entries, paths):
            require_fields(
                entry,
                {"filePath", "secretName", "secretPath", "mode"},
                {"filePath", "secretName", "secretPath"},
            )
            if (
                entry["filePath"] != path
                or entry["secretPath"] != source(path)
                or not re.fullmatch(r"startup-[0-9]+", entry["secretName"])
                or entry.get("mode", "read") != "read"
            ):
                raise UserError("Only read-only startup Secrets are allowed.")
    validate_topology(topology, files, "lab.clab.yml")


class Boundary:
    def __init__(self, env, username, images):
        self.env = env
        self.username = username
        self.images = images

    def validate(self, request):
        env = self.env
        resource = (request["resource"]["group"], request["resource"]["resource"])
        operation = request["operation"]
        obj = request["oldObject"] if operation == "DELETE" else request["object"]
        metadata = obj["metadata"]
        cleaner = "system:serviceaccount:" + env.namespace + ":cleaner"
        username = request["userInfo"]["username"]
        if username not in {self.username, cleaner}:
            raise UserError("The caller is outside the lab boundary.")
        if request.get("subResource"):
            raise UserError("Subresource mutation is not allowed.")
        if resource == ("", "configmaps"):
            if (
                operation not in {"CREATE", "UPDATE"}
                or request["namespace"] != env.namespace
            ):
                raise UserError("Only lab ownership records can be changed.")
            lab = metadata["name"]
            check_lab(lab)
            if any(
                metadata.get(field)
                for field in ("annotations", "finalizers", "ownerReferences")
            ):
                raise UserError(
                    "Ownership record hooks and finalizers are not allowed."
                )
            if set(obj["data"]) != {"record"}:
                raise UserError("Only the ownership record is allowed.")
            record = json.loads(obj["data"]["record"])
            if record["id"] != lab or record["environment"] != env.name:
                raise UserError("The ownership record identity is invalid.")
            if not re.fullmatch(r"[a-f0-9]{32}", record["allocation_id"]):
                raise UserError("The allocation identity is invalid.")
            if operation == "CREATE":
                if username == cleaner or not (
                    now() - 60 <= record["accepted_at"] <= now() + 30
                    and 0 < record["expires_at"] - record["accepted_at"] <= 3600
                    and record["accepted_at"]
                    < record["startup_deadline"]
                    <= record["expires_at"]
                    and record["state"] == "creating"
                    and record["runtime"]["ceos_image"] in self.images
                ):
                    raise UserError("The new ownership record exceeds the lab policy.")
            else:
                old = json.loads(request["oldObject"]["data"]["record"])
                for field in (
                    "id",
                    "environment",
                    "allocation_id",
                    "accepted_at",
                    "expires_at",
                    "startup_deadline",
                    "runtime",
                    "provenance",
                    "bundle_digest",
                    "switches",
                    "link_count",
                    "registry",
                ):
                    if record[field] != old[field]:
                        raise UserError(
                            "Accepted lab identity and expiry are immutable."
                        )
                if old["state"] in {"deleting", "deleted"} and record["state"] not in {
                    "deleting",
                    "deleted",
                }:
                    raise UserError("Cleanup cannot restore an active lab.")
            if record["state"] not in {
                "creating",
                "running",
                "ready",
                "deleting",
                "deleted",
            }:
                raise UserError("The lab state is invalid.")
            if metadata.get("labels") != {ENV_LABEL: env.name, LAB_LABEL: lab}:
                raise UserError("The ownership labels are invalid.")
            return
        if resource == ("", "namespaces"):
            if operation not in {"CREATE", "DELETE"} or (
                username == cleaner and operation != "DELETE"
            ):
                raise UserError("The namespace operation is not allowed.")
            namespace = metadata["name"]
        else:
            if (
                username == cleaner
                or operation != "CREATE"
                or resource not in {("", "secrets"), ("c9s.run", "topologies")}
            ):
                raise UserError("The resource operation is not allowed.")
            namespace = request["namespace"]
        if not namespace.startswith(env.name + "-"):
            raise UserError("The namespace is outside the lab boundary.")
        lab = namespace.removeprefix(env.name + "-")
        check_lab(lab)
        record = lab_record(env, lab)
        if not record:
            raise UserError("The lab ownership record is absent.")
        if resource == ("", "namespaces"):
            check_namespace(env, obj, record)
            if operation == "DELETE":
                if record["state"] not in {"deleting", "deleted"}:
                    raise UserError("Lab cleanup must start before namespace deletion.")
                return
            if (
                metadata.get("annotations")
                or metadata.get("finalizers")
                or metadata.get("ownerReferences")
                or obj.get("spec", {}).get("finalizers", []) not in ([], ["kubernetes"])
            ):
                raise UserError("Namespace hooks and finalizers are not allowed.")
            if metadata["labels"] != {
                ENV_LABEL: env.name,
                LAB_LABEL: lab,
                ALLOCATION_LABEL: record["allocation_id"],
                "pod-security.kubernetes.io/enforce": "privileged",
                "kubernetes.io/metadata.name": namespace,
            }:
                raise UserError("Only operator-approved namespace labels are allowed.")
        else:
            current = json.loads(env.kube("get", "namespace", namespace, "-o", "json"))
            check_namespace(env, current, record)
            wait_for(lambda: self.reader_ready(lab), timeout=5, interval=0.2)
            if (
                metadata.get("labels") != {ENV_LABEL: env.name, LAB_LABEL: lab}
                or metadata.get("annotations")
                or metadata.get("finalizers")
                or metadata.get("ownerReferences")
            ):
                raise UserError("Only lab payload metadata is allowed.")
            if resource == ("", "secrets"):
                if (
                    not re.fullmatch(r"startup-[0-9]+", metadata["name"])
                    or obj.get("type") != "Opaque"
                    or "stringData" in obj
                    or not obj.get("data")
                    or any(not re.fullmatch(r"file-[0-9]+", key) for key in obj["data"])
                ):
                    raise UserError("Only startup payload Secrets can be created.")
            else:
                if metadata["name"] != "fabric":
                    raise UserError("Only the lab fabric Topology can be created.")
                validate_runtime_topology(
                    obj, {record["runtime"]["ceos_image"]} & set(self.images), lab
                )
        if (
            record["state"] != "creating"
            or min(record["expires_at"], record["startup_deadline"]) <= now()
        ):
            raise UserError("The lab is no longer accepting allocations.")

    def reader_ready(self, lab):
        expected = reader_binding(self.env, lab, self.username)
        for binding in self.env.objects("rolebindings", self.env.name + "-" + lab):
            if binding["metadata"]["name"] == "lifecycle-reader":
                if any(
                    binding.get(field) != expected[field]
                    for field in ("roleRef", "subjects")
                ):
                    raise UserError("The lab reader binding has different ownership.")
                return True
        return False

    def bind_readers(self):
        for namespace in self.env.objects(
            "namespaces", labels=f"{ENV_LABEL}={self.env.name}"
        ):
            lab = namespace["metadata"]["name"].removeprefix(self.env.name + "-")
            if not re.fullmatch(r"lab-[a-f0-9]{12}", lab) or namespace["metadata"].get(
                "deletionTimestamp"
            ):
                continue
            try:
                record = lab_record(self.env, lab)
                if not record or record["state"] not in {
                    "creating",
                    "running",
                    "ready",
                }:
                    continue
                check_namespace(self.env, namespace, record)
                binding = reader_binding(self.env, lab, self.username)
                if self.reader_ready(lab):
                    continue
                self.env.kube("create", "-f", "-", data=json.dumps(binding))
            except UserError:
                print("Drydock reader binding ownership conflict.", flush=True)


def serve(boundary, certificate, key):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.connection.settimeout(5)
            review = {}
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if (
                    self.path.partition("?")[0] != "/validate"
                    or not 0 < size <= 2 * 1024 * 1024
                ):
                    self.send_error(400)
                    return
                review = json.loads(self.rfile.read(size))
                request = review["request"]
                if (
                    review["apiVersion"] != "admission.k8s.io/v1"
                    or review["kind"] != "AdmissionReview"
                ):
                    raise ValueError
                boundary.validate(request)
                response = {"uid": request["uid"], "allowed": True}
            except Exception as error:
                # Rejected objects can contain credentials. Never log their contents.
                response = {
                    "uid": review.get("request", {}).get("uid", ""),
                    "allowed": False,
                    "status": {
                        "message": "Drydock lab admission denied."
                        + (" " + str(error) if isinstance(error, UserError) else "")
                    },
                }
            payload = json.dumps(
                {
                    "apiVersion": "admission.k8s.io/v1",
                    "kind": "AdmissionReview",
                    "response": response,
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def reconcile():
        while True:
            try:
                boundary.bind_readers()
            except Exception:
                print("Drydock reader binding reconciliation failed.", flush=True)
            time.sleep(2)

    server = ThreadingHTTPServer(("0.0.0.0", 8443), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certificate, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=reconcile, daemon=True).start()
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--ceos-image", action="append", required=True)
    parser.add_argument("--certificate", required=True)
    parser.add_argument("--key", required=True)
    args = parser.parse_args()
    serve(
        Boundary(Environment.load(args.environment), args.username, args.ceos_image),
        args.certificate,
        args.key,
    )


if __name__ == "__main__":
    main()
