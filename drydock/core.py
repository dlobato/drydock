"""Input boundaries and subprocesses shared by the CLI and cluster cleaner."""

import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

ENV_LABEL = "drydock.io/environment"
LAB_LABEL = "drydock.io/lab"
ALLOCATION_LABEL = "drydock.io/allocation"
PAYLOAD_LIMIT = 512 * 1024


class UserError(ValueError):
    """A safe operator-facing message with no provider output or input contents."""


def now():
    return datetime.now(UTC).timestamp()


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(json.dumps(data, indent=2) + "\n")
        Path(temporary).replace(path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def run(command, *, data=None, timeout=120, env=None):
    try:
        result = subprocess.run(
            command,
            input=data,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"{command[0]} {command[1]} timed out") from None
    if result.returncode:
        # Manifests and tool output can contain credentials. Do not echo them.
        raise RuntimeError(
            f"{command[0]} {command[1]} failed with exit code {result.returncode}"
        )
    return result.stdout


def wait_for(action, timeout, interval=10):
    deadline = time.monotonic() + timeout
    while True:
        result = action()
        if result:
            return result
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                "Operation timed out. Ownership remains recorded for cleanup."
            )
        time.sleep(min(interval, remaining))


@dataclass(frozen=True)
class Environment:
    name: str
    kubeconfig: str
    context: str

    def __post_init__(self):
        if not re.fullmatch(r"drydock-[a-z0-9](?:[a-z0-9-]{0,12}[a-z0-9])?", self.name):
            raise UserError("Invalid environment name.")
        if not self.kubeconfig or not self.context:
            raise UserError("Supply a kubeconfig path and Kubernetes context.")

    @classmethod
    def load(cls, path):
        return cls(**yaml.safe_load(Path(path).read_text()))

    @property
    def namespace(self):
        return self.name + "-system"

    def kube_command(self, *args):
        return [
            "kubectl",
            "--request-timeout=30s",
            "--kubeconfig",
            self.kubeconfig,
            "--context",
            self.context,
            *args,
        ]

    def kube(self, *args, data=None):
        return run(self.kube_command(*args), data=data)

    def apply(self, obj):
        return self.kube("apply", "-f", "-", data=json.dumps(obj))

    def objects(self, resource, namespace=None, labels=None):
        args = ["get", resource, "-o", "json"]
        if namespace:
            args += ["-n", namespace]
        if labels:
            args += ["-l", labels]
        return json.loads(self.kube(*args))["items"]


def require_digest(image):
    if not isinstance(image, str) or not re.fullmatch(
        r"[a-zA-Z0-9][a-zA-Z0-9._:/-]*@sha256:[a-f0-9]{64}", image
    ):
        raise UserError("Supply an image reference pinned by SHA-256 digest.")


def require_fields(value, allowed, required=()):
    if (
        not isinstance(value, dict)
        or value.keys() - set(allowed)
        or set(required) - value.keys()
    ):
        raise UserError("Unsupported or missing topology attributes.")


def safe_path(value):
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", value)
        or any(part in {".", ".."} for part in value.split("/"))
    ):
        raise UserError("File references must be safe relative archive paths.")
    return value


def mapping_source(binds):
    if not isinstance(binds, list) or len(binds) > 1:
        raise UserError(
            "Only one read-only interface mapping mount is supported per switch."
        )
    source = None
    for bind in binds:
        if (
            not isinstance(bind, str)
            or len(bind.split(":")) != 3
            or not bind.endswith(":/mnt/flash/EosIntfMapping.json:ro")
        ):
            raise UserError("Only a read-only interface mapping mount is supported.")
        source = safe_path(bind.split(":")[0])
    return source


@dataclass
class Bundle:
    digest: str
    topology: dict
    files: dict

    @classmethod
    def load(cls, path):
        with Path(path).open("rb") as stream:
            content = stream.read(10 * 1024 * 1024 + 1)
        if len(content) > 10 * 1024 * 1024:
            raise UserError("Bundle exceeds the 10 MiB limit.")
        files = {}
        try:
            with tarfile.open(fileobj=io.BytesIO(content), mode="r:") as archive:
                for member in archive:
                    safe_path(member.name)
                    if (
                        not member.isfile()
                        or member.sparse is not None
                        or member.name in files
                        or not 0 <= member.size <= 1024 * 1024
                    ):
                        raise UserError(
                            "Bundle contains an unsafe or duplicate member."
                        )
                    member_stream = archive.extractfile(member)
                    assert member_stream is not None
                    files[member.name] = member_stream.read().decode()
        except (tarfile.TarError, UnicodeError):
            raise UserError(
                "Supply an uncompressed tar archive of UTF-8 files."
            ) from None
        candidates = [
            name for name in files if re.fullmatch(r"[^/]+\.clab\.ya?ml", name)
        ]
        if len(candidates) != 1:
            raise UserError(
                "Supply exactly one root-level .clab.yml or .clab.yaml file."
            )
        topology_path = candidates[0]
        try:
            topology = yaml.safe_load(files[topology_path])
        except yaml.YAMLError:
            raise UserError("The topology must contain valid YAML.") from None
        require_fields(
            topology,
            {"name", "prefix", "mgmt", "topology"},
            {"name", "topology"},
        )
        if not isinstance(topology["name"], str) or topology.get("prefix", "") != "":
            raise UserError("Unsupported topology attributes.")
        require_fields(topology.get("mgmt", {}), {"network", "ipv4-subnet"})
        definition = topology["topology"]
        require_fields(
            definition, {"nodes", "links", "kinds", "defaults"}, {"nodes", "kinds"}
        )
        defaults = definition.get("defaults", {})
        require_fields(defaults, {"kind"})
        if defaults.get("kind", "arista_ceos") != "arista_ceos":
            raise UserError("Unsupported topology defaults.")
        require_fields(definition["kinds"], {"arista_ceos"}, {"arista_ceos"})
        kind = definition["kinds"]["arista_ceos"]
        require_fields(kind, {"image", "binds", "enforce-startup-config"}, {"image"})
        if kind.get("enforce-startup-config", True) is not True:
            raise UserError("Complete startup configurations must be enforced.")
        require_digest(kind["image"])
        nodes = definition["nodes"]
        if not isinstance(nodes, dict) or not nodes:
            raise UserError("Supply at least one cEOS switch.")
        expected = {topology_path}
        source = mapping_source(kind.get("binds", []))
        if source:
            expected.add(source)
        for name, node in nodes.items():
            if not isinstance(name, str) or not re.fullmatch(
                r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", name
            ):
                raise UserError(
                    "Switch names must be DNS labels of at most 63 characters."
                )
            require_fields(
                node,
                {"kind", "startup-config", "mgmt-ipv4", "binds", "labels"},
                {"startup-config"},
            )
            if node.get("kind", defaults.get("kind")) != "arista_ceos":
                raise UserError("Only arista_ceos switches are supported.")
            startup = safe_path(node["startup-config"])
            expected.add(startup)
            source = mapping_source(node.get("binds", []))
            if source:
                expected.add(source)
        if set(files) != expected:
            raise UserError(
                "Bundle files must match the topology and its referenced files exactly."
            )
        if any(
            len(files[name].encode()) > PAYLOAD_LIMIT
            for name in expected - {topology_path}
        ):
            raise UserError("Each startup or mapping file must fit within 512 KiB.")
        links = definition.get("links", [])
        if not isinstance(links, list):
            raise UserError("Topology links must be a list.")
        for link in links:
            require_fields(link, {"endpoints", "mtu"}, {"endpoints"})
            if not isinstance(link["endpoints"], list) or len(link["endpoints"]) != 2:
                raise UserError("Each link must contain two switch endpoints.")
            for endpoint in link["endpoints"]:
                if (
                    not isinstance(endpoint, str)
                    or len(endpoint.split(":")) != 2
                    or endpoint.split(":")[0] not in nodes
                ):
                    raise UserError("Link endpoints must reference admitted switches.")
        return cls(hashlib.sha256(content).hexdigest(), topology, files)


def readiness(items, expected_nodes, expected_links):
    errors = []
    topology = [item for item in items if item["kind"] == "Topology"]
    if len(topology) != 1:
        errors.append("topology is missing")
    else:
        status = topology[0].get("status", {})
        if (
            status.get("observedGeneration") != topology[0]["metadata"]["generation"]
            or not status.get("topologyReady")
            or status.get("topologyState") != "running"
        ):
            errors.append("topology is not current and ready")
    nodes = {item["metadata"]["name"]: item for item in items if item["kind"] == "Node"}
    if set(nodes) != set(expected_nodes):
        errors.append("switch identities differ from the bundle")
    for name, node in nodes.items():
        status = node.get("status", {})
        conditions = {c["type"]: c for c in status.get("conditions", [])}
        if status.get("readiness") != "ready" or not status.get("planDigest"):
            errors.append(f"{name}: no ready plan")
        for kind in ("PlanApplied", "Prepared", "ConnectivityReady", "ContainersReady"):
            if conditions.get(kind, {}).get("status") != "True":
                errors.append(f"{name}: {kind} is not ready")
        if (
            conditions.get("PlanApplied", {}).get("observedGeneration")
            != node["metadata"]["generation"]
        ):
            errors.append(f"{name}: plan generation is stale")
    links = [item for item in items if item["kind"] == "Link"]
    if len(links) != expected_links or any(
        not any(
            c["type"] == "Accepted" and c["status"] == "True"
            for c in item.get("status", {}).get("conditions", [])
        )
        for item in links
    ):
        errors.append("switch links are missing or not accepted")
    pods = [
        item
        for item in items
        if item["kind"] == "Pod"
        and item["metadata"].get("labels", {}).get("c9s.run/direct-workload")
        in expected_nodes
    ]
    if len(pods) != len(expected_nodes) or {
        pod["metadata"]["labels"]["c9s.run/direct-workload"] for pod in pods
    } != set(expected_nodes):
        errors.append("exactly one switch pod is required for each device")
    for pod in pods:
        status = pod.get("status", {})
        if pod["metadata"].get("deletionTimestamp") or not any(
            c["type"] == "Ready" and c["status"] == "True"
            for c in status.get("conditions", [])
        ):
            errors.append("a switch pod is not ready")
        if any(
            c.get("restartCount", 0)
            for c in status.get("containerStatuses", [])
            + status.get("initContainerStatuses", [])
        ):
            errors.append("a switch container restarted")
    return errors
