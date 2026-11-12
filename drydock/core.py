"""Input boundaries and subprocesses shared by the CLI and cluster cleaner."""

import hashlib
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
NODES = {"spine1", "spine2", "leaf1", "leaf2", "leaf3", "leaf4"}


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


@dataclass
class Bundle:
    digest: str
    topology: dict
    files: dict
    interfaces: dict

    @classmethod
    def load(cls, path):
        if Path(path).stat().st_size > 10 * 1024 * 1024:
            raise UserError("Bundle exceeds the 10 MiB limit.")
        content = Path(path).read_bytes()
        files = {}
        with tarfile.open(path, mode="r:") as archive:
            for member in archive:
                if (
                    not member.isfile()
                    or member.name in files
                    or member.size > 1024 * 1024
                    or member.name.startswith("/")
                    or ".." in Path(member.name).parts
                ):
                    raise UserError("Bundle contains an unsafe or duplicate member.")
                stream = archive.extractfile(member)
                assert stream is not None
                files[member.name] = stream.read().decode()
        expected = {"FABRIC-topology.clab.yml", "interface_mapping.json"} | {
            f"intended/configs/{name}.cfg" for name in NODES
        }
        if set(files) != expected:
            raise UserError(
                "Bundle must contain the topology, mapping, and six startup configurations."
            )
        if (
            sum(
                len(text.encode())
                for name, text in files.items()
                if name.endswith((".cfg", ".json"))
            )
            > 512 * 1024
        ):
            raise UserError(
                "Startup files exceed the shared Secret payload limit of 512 KiB."
            )
        topology = yaml.safe_load(files["FABRIC-topology.clab.yml"])
        if (
            set(topology) != {"name", "prefix", "mgmt", "topology"}
            or topology["prefix"] != ""
        ):
            raise UserError("Unsupported topology attributes.")
        if topology["mgmt"] != {
            "network": "custom_mgmt",
            "ipv4-subnet": "192.0.2.0/24",
        }:
            raise UserError("The demo requires the generated management network.")
        definition = topology["topology"]
        if set(definition) != {"nodes", "links", "kinds", "defaults"} or definition[
            "defaults"
        ] != {"kind": "arista_ceos"}:
            raise UserError("Unsupported topology defaults.")
        if set(definition["nodes"]) != NODES:
            raise UserError(
                "The first demo requires spine1, spine2, and leaf1 through leaf4."
            )
        if set(definition.get("kinds", {})) != {"arista_ceos"}:
            raise UserError("Only arista_ceos switches are supported.")
        kind = definition["kinds"]["arista_ceos"]
        if (
            set(kind) != {"image", "binds", "enforce-startup-config"}
            or kind["enforce-startup-config"] is not True
        ):
            raise UserError("The demo requires enforced startup configurations.")
        require_digest(kind["image"])
        if kind.get("binds") != [
            "interface_mapping.json:/mnt/flash/EosIntfMapping.json:ro"
        ]:
            raise UserError("Only the generated interface mapping mount is supported.")
        mapping = json.loads(files["interface_mapping.json"])["EthernetIntf"]
        if mapping != {f"eth{port}": f"Ethernet{port}" for port in (1, 2, 3, 4, 6, 7)}:
            raise UserError("Unsupported switch interface mapping.")
        interfaces: dict[str, list[str]] = {name: [] for name in NODES}
        endpoints = set()
        for link in definition["links"]:
            if set(link) != {"endpoints"} or len(link["endpoints"]) != 2:
                raise UserError("Each link must contain two switch endpoints.")
            for endpoint in link["endpoints"]:
                node, port = endpoint.split(":")
                if node not in NODES or port not in mapping or endpoint in endpoints:
                    raise UserError("Invalid or repeated switch link endpoint.")
                interfaces[node].append(mapping[port])
                endpoints.add(endpoint)
        expected_links = {
            frozenset((f"leaf{leaf}:eth{spine}", f"spine{spine}:eth{leaf}"))
            for leaf in range(1, 5)
            for spine in (1, 2)
        } | {
            frozenset((f"leaf{first}:eth{port}", f"leaf{first + 1}:eth{port}"))
            for first in (1, 3)
            for port in (6, 7)
        }
        if {
            frozenset(link["endpoints"]) for link in definition["links"]
        } != expected_links:
            raise UserError(
                "The demo requires all spine links and both MLAG peer links."
            )
        for name, node in definition["nodes"].items():
            address = f"192.0.2.{20 + int(name[-1]) if name.startswith('leaf') else 10 + int(name[-1])}"
            if node.get("mgmt-ipv4") != address:
                raise UserError("Switch management identity differs from the example.")
            if set(node) - {"kind", "startup-config", "mgmt-ipv4", "labels"}:
                raise UserError("Unsupported switch attributes in the demo bundle.")
            if (
                node.get("kind", definition.get("defaults", {}).get("kind"))
                != "arista_ceos"
            ):
                raise UserError("Only arista_ceos switches are supported.")
            path = f"intended/configs/{name}.cfg"
            if node["startup-config"] != path or not re.search(
                rf"^hostname {name}$", files[path], re.MULTILINE
            ):
                raise UserError(
                    "Switch identity and startup configuration do not match."
                )
        return cls(hashlib.sha256(content).hexdigest(), topology, files, interfaces)


def readiness(items, expected_links=12):
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
    if set(nodes) != NODES:
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
        and item["metadata"].get("labels", {}).get("c9s.run/direct-workload") in NODES
    ]
    if len(pods) != len(NODES):
        errors.append("switch pods are missing")
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
