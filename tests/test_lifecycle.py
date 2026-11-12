"""Offline contract tests. No provider calls or device images."""

import base64
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from drydock import flow
from drydock import lifecycle as cloud
from drydock.core import (
    ALLOCATION_LABEL,
    ENV_LABEL,
    LAB_LABEL,
    PAYLOAD_LIMIT,
    Bundle,
    Environment,
    UserError,
    readiness,
)

NODES = {"spine1", "spine2", "leaf1", "leaf2", "leaf3", "leaf4"}

IMAGE = "europe-west1-docker.pkg.dev/demo-project/images/ceos@sha256:" + "a" * 64
ENV = Environment("drydock-demo", "/tmp/test-kubeconfig", "test-context")
IDENTITY = {
    "repository": "example/repo",
    "commit": "abc123",
    "run": "local-demo",
    "attempt": "1",
}
LAB = "lab-123456789abc"


def bundle_files():
    nodes = {
        name: {
            "mgmt-ipv4": f"192.0.2.{20 + int(name[-1]) if name.startswith('leaf') else 10 + int(name[-1])}",
            "startup-config": f"intended/configs/{name}.cfg",
        }
        for name in sorted(NODES)
    }
    links = [
        {"endpoints": [f"leaf{leaf}:eth{spine}", f"spine{spine}:eth{leaf}"]}
        for leaf in range(1, 5)
        for spine in (1, 2)
    ]
    links += [
        {"endpoints": [f"leaf{leaf}:eth{port}", f"leaf{leaf + 1}:eth{port}"]}
        for leaf in (1, 3)
        for port in (6, 7)
    ]
    topology = {
        "name": "FABRIC",
        "prefix": "",
        "mgmt": {"network": "custom_mgmt", "ipv4-subnet": "192.0.2.0/24"},
        "topology": {
            "defaults": {"kind": "arista_ceos"},
            "kinds": {
                "arista_ceos": {
                    "image": IMAGE,
                    "enforce-startup-config": True,
                    "binds": [
                        "interface_mapping.json:/mnt/flash/EosIntfMapping.json:ro"
                    ],
                }
            },
            "nodes": nodes,
            "links": links,
        },
    }
    return {
        "FABRIC-topology.clab.yml": yaml.safe_dump(topology),
        "interface_mapping.json": json.dumps(
            {
                "ManagementIntf": {"eth0": "Management1"},
                "EthernetIntf": {f"eth{p}": f"Ethernet{p}" for p in (1, 2, 3, 4, 6, 7)},
            }
        ),
        **{
            f"intended/configs/{name}.cfg": f"hostname {name}\nmanagement api http-commands\n   no shutdown\n   protocol https\n"
            for name in NODES
        },
    }


def make_bundle(directory, mutate=None, *, files=None):
    if files is None:
        files = bundle_files()
    if mutate:
        mutate(files)
    path = Path(directory) / "bundle.tar"
    with tarfile.open(path, "w") as archive:
        for name, text in files.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(text.encode())
            archive.addfile(entry, io.BytesIO(text.encode()))
    return Bundle.load(path)


def alternate_files(count=3, *, mapping=True, padding=""):
    names = [f"switch-{index}" for index in range(1, count + 1)]
    files = {}
    nodes = {}
    for index, name in enumerate(names):
        startup = f"configs/{name}/startup.cfg"
        nodes[name] = {
            "kind": "arista_ceos",
            "mgmt-ipv4": f"10.70.0.{index + 10}",
            "startup-config": startup,
        }
        files[startup] = f"hostname {name}\n! {padding}\n"
        if mapping:
            path = f"mappings/{name}.json"
            nodes[name]["binds"] = [f"{path}:/mnt/flash/EosIntfMapping.json:ro"]
            files[path] = json.dumps(
                {
                    "EthernetIntf": {
                        "eth9": f"Ethernet{index + 1}/1",
                        "eth10": f"Ethernet{index + 1}/2",
                    }
                }
            )
    topology = {
        "name": "alternate",
        "mgmt": {"ipv4-subnet": "10.70.0.0/24"},
        "topology": {
            "kinds": {"arista_ceos": {"image": IMAGE}},
            "nodes": nodes,
            "links": [
                {"endpoints": [f"{left}:eth10", f"{right}:eth9"]}
                for left, right in zip(names, names[1:])
            ],
        },
    }
    files["lab.clab.yaml"] = yaml.safe_dump(topology)
    return files


class FakeEnvironment:
    """Persist ownership like Kubernetes, including optimistic update conflicts."""

    def __init__(self):
        self.name, self.namespace = ENV.name, ENV.namespace
        self.records, self.namespaces, self.applied, self.calls = {}, [], [], []
        self.fail_namespace, self.fail_delete = False, False

    def objects(self, kind, namespace=None, labels=None):
        if kind == "configmaps":
            return [
                json.loads(json.dumps(obj))
                for lab, obj in self.records.items()
                if not labels or LAB_LABEL + "=" not in labels or lab in labels
            ]
        if kind == "namespaces":
            return json.loads(json.dumps(self.namespaces))
        return []

    def kube(self, *args, data=None):
        self.calls.append(("kube", args))
        if args[0] in ("create", "replace"):
            obj = json.loads(data)
            if obj["kind"] == "ConfigMap":
                name = obj["metadata"]["name"]
                old = self.records.get(name)
                if args[0] == "create" and old:
                    raise RuntimeError("Conflict")
                if args[0] == "replace" and (
                    not old
                    or obj["metadata"]["resourceVersion"]
                    != old["metadata"]["resourceVersion"]
                ):
                    raise RuntimeError("Conflict")
                obj["metadata"]["resourceVersion"] = str(
                    int(old["metadata"]["resourceVersion"]) + 1 if old else 1
                )
                self.records[name] = obj
            elif obj["kind"] == "Namespace":
                if any(
                    n["metadata"]["name"] == obj["metadata"]["name"]
                    for n in self.namespaces
                ):
                    raise RuntimeError("Conflict")
                obj["metadata"].update(
                    uid="namespace-" + str(len(self.calls)), resourceVersion="1"
                )
                self.namespaces.append(obj)
                if self.fail_namespace:
                    raise RuntimeError(
                        "namespace creation interrupted after acceptance"
                    )
            else:
                self.applied.append(obj)
        elif args[0] == "delete":
            if self.fail_delete:
                raise RuntimeError("namespace deletion failed")
            name = args[1].removeprefix("--raw=/api/v1/namespaces/")
            preconditions = json.loads(data)["preconditions"]
            for item in self.namespaces:
                if item["metadata"]["name"] == name and any(
                    item["metadata"][key] != value
                    for key, value in preconditions.items()
                ):
                    raise RuntimeError("Conflict")
            self.namespaces = [
                n for n in self.namespaces if n["metadata"]["name"] != name
            ]
            self.applied = [
                obj for obj in self.applied if obj["metadata"]["namespace"] != name
            ]
        return "{}"

    def apply(self, obj):
        self.applied.append(obj)


class BundleTests(unittest.TestCase):
    def test_valid_bundle_preserves_identities(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = make_bundle(directory)
        self.assertEqual(set(bundle.topology["topology"]["nodes"]), NODES)

    def test_reject_unsafe_missing_and_unsupported_inputs(self):
        changes = [
            lambda f: f.pop("intended/configs/leaf4.cfg"),
            lambda f: f.update({"../outside": "x"}),
            lambda f: f.update(
                {
                    "FABRIC-topology.clab.yml": f["FABRIC-topology.clab.yml"].replace(
                        "arista_ceos", "linux"
                    )
                }
            ),
            lambda f: f.update(
                {
                    "FABRIC-topology.clab.yml": f["FABRIC-topology.clab.yml"].replace(
                        IMAGE, "ceos:latest"
                    )
                }
            ),
        ]
        for change in changes:
            with (
                self.subTest(change=change),
                tempfile.TemporaryDirectory() as directory,
                self.assertRaises(ValueError),
            ):
                make_bundle(directory, change)

    def test_duplicate_and_symlink_rejected(self):
        for kind in ("duplicate", "symlink"):
            with tempfile.TemporaryDirectory() as directory:
                make_bundle(directory)
                path = Path(directory) / "bundle.tar"
                with tarfile.open(path, "a") as archive:
                    member = tarfile.TarInfo(
                        "interface_mapping.json" if kind == "duplicate" else "link"
                    )
                    if kind == "symlink":
                        member.type = tarfile.SYMTYPE
                        member.linkname = "/etc/passwd"
                    archive.addfile(member)
                with self.assertRaises(ValueError):
                    Bundle.load(path)


class TopologyAdmissionTests(unittest.TestCase):
    def test_preserves_topology_fields_and_treats_payloads_as_opaque(self):
        files = alternate_files(3, mapping=False)
        original = yaml.safe_load(files["lab.clab.yaml"])
        kind = original["topology"]["kinds"]["arista_ceos"]
        kind["binds"] = ["shared.json:/mnt/flash/EosIntfMapping.json:ro"]
        nodes = original["topology"]["nodes"]
        nodes["switch-1"]["binds"] = ["custom.json:/mnt/flash/EosIntfMapping.json:ro"]
        nodes["switch-2"]["binds"] = []
        nodes["switch-1"]["labels"] = {"role": "edge"}
        # Address and interface semantics belong to clabernetes.
        original["mgmt"]["ipv4-subnet"] = "10.70.0.10/31"
        nodes["switch-1"]["mgmt-ipv4"] = "10.70.0.10"
        nodes["switch-2"].pop("mgmt-ipv4")
        original["topology"]["links"][0] = {
            "endpoints": ["switch-1:e1-1", "switch-2:e1-2"],
            "mtu": 9000,
        }
        files["shared.json"] = "opaque shared mapping\n"
        files["custom.json"] = "opaque custom mapping\n"
        files["configs/switch-1/startup.cfg"] = "! opaque startup configuration\n"
        files["lab.clab.yaml"] = yaml.safe_dump(original)
        with tempfile.TemporaryDirectory() as directory:
            bundle = make_bundle(directory, files=files)
        env = FakeEnvironment()
        cloud.create_lab(env, bundle, IDENTITY, lab=LAB)
        self.assertEqual(bundle.topology, original)
        manifest = next(obj for obj in env.applied if obj["kind"] == "Topology")
        submitted = yaml.safe_load(manifest["spec"]["definition"]["containerlab"])
        self.assertEqual(submitted["name"], original["name"])
        self.assertEqual(submitted["mgmt"]["ipv4-subnet"], "10.70.0.10/31")
        self.assertEqual(submitted["mgmt"]["network"], LAB)
        self.assertEqual(submitted["topology"]["links"], original["topology"]["links"])
        secrets = {
            obj["metadata"]["name"]: obj
            for obj in env.applied
            if obj["kind"] == "Secret"
        }
        for name, node in submitted["topology"]["nodes"].items():
            self.assertEqual(node.get("mgmt-ipv4"), nodes[name].get("mgmt-ipv4"))
            self.assertEqual(node.get("labels"), nodes[name].get("labels"))
            references = manifest["spec"]["deployment"]["filesFromSecret"][name]
            delivered = {
                ref["filePath"]: base64.b64decode(
                    secrets[ref["secretName"]]["data"][ref["secretPath"]]
                ).decode()
                for ref in references
            }
            self.assertEqual(
                delivered[node["startup-config"]], files[nodes[name]["startup-config"]]
            )
            binds = (
                node.get("binds")
                or submitted["topology"]["kinds"]["arista_ceos"]["binds"]
            )
            if name == "switch-2":
                self.assertEqual(node["binds"], [])
            self.assertEqual(len(references), 2)
            source = binds[0].split(":")[0]
            self.assertEqual(
                delivered[source],
                files["custom.json" if name == "switch-1" else "shared.json"],
            )

    def test_backend_defaults_do_not_require_management_or_link_fields(self):
        files = alternate_files(1, mapping=False)
        original = yaml.safe_load(files["lab.clab.yaml"])
        original.pop("mgmt")
        original["topology"].pop("links")
        original["topology"]["nodes"]["switch-1"].pop("mgmt-ipv4")
        files["lab.clab.yaml"] = yaml.safe_dump(original)
        with tempfile.TemporaryDirectory() as directory:
            bundle = make_bundle(directory, files=files)
        env = FakeEnvironment()
        record = cloud.create_lab(env, bundle, IDENTITY)
        self.assertEqual(record["switches"], ["switch-1"])
        self.assertEqual(record["link_count"], 0)
        self.assertEqual(bundle.topology, original)

    def test_different_fabrics_preserve_topology_and_mapping(self):
        for count, mapping in ((1, False), (3, True), (5, False), (100, True)):
            with (
                self.subTest(count=count, mapping=mapping),
                tempfile.TemporaryDirectory() as directory,
            ):
                files = alternate_files(count, mapping=mapping)
                bundle = make_bundle(directory, files=files)
                self.assertEqual(
                    set(bundle.topology["topology"]["nodes"]),
                    {f"switch-{index}" for index in range(1, count + 1)},
                )
                self.assertEqual(
                    bundle.topology["topology"]["links"],
                    yaml.safe_load(files["lab.clab.yaml"])["topology"]["links"],
                )

    def test_reject_invalid_topology_shapes_and_execution_features(self):
        changes = [
            (("exec",), ["touch /outside"]),
            (("prefix",), "other"),
            (("mgmt", "bridge"), "host"),
            (("topology", "defaults"), {"exec": ["bad"]}),
            (("topology", "nodes"), []),
            (("topology", "nodes"), {}),
            (
                ("topology", "kinds", "arista_ceos", "binds"),
                ["/outside:/mnt/flash/EosIntfMapping.json:ro"],
            ),
            (("topology", "nodes", "switch-1", "exec"), ["bad"]),
            (("topology", "nodes", "switch-1", "kind"), "linux"),
            (("topology", "nodes", "switch-1", "startup-config"), "../outside"),
            (("topology", "nodes", "switch-1", "startup-config"), "/etc/passwd"),
            (
                ("topology", "nodes", "switch-1", "startup-config"),
                "https://example.test/file",
            ),
            (
                ("topology", "nodes", "switch-1", "startup-config"),
                "configs//switch-1/startup.cfg",
            ),
            (
                ("topology", "nodes", "switch-1", "binds"),
                ["/etc/passwd:/mnt/flash/EosIntfMapping.json:ro"],
            ),
            (
                ("topology", "nodes", "switch-1", "binds"),
                ["mappings/switch-1.json:/tmp/other:ro"],
            ),
            (
                ("topology", "nodes", "switch-1", "binds"),
                ["mappings/switch-1.json:/mnt/flash/EosIntfMapping.json:rw"],
            ),
            (("topology", "nodes", "switch-1", "binds"), "mappings/switch-1.json"),
            (("topology", "links"), [{"endpoints": ["switch-1:eth10", "absent:eth9"]}]),
            (("topology", "links"), [{"endpoints": ["switch-1:eth10", "host:eth9"]}]),
            (("topology", "links"), [{"type": "host", "endpoint": "switch-1:eth10"}]),
            (("topology", "links"), [{"endpoints": "switch-1:eth10"}]),
        ]
        for path, value in changes:
            with (
                self.subTest(path=path, value=value),
                tempfile.TemporaryDirectory() as directory,
            ):
                files = alternate_files()
                topology = yaml.safe_load(files["lab.clab.yaml"])
                target = topology
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                files["lab.clab.yaml"] = yaml.safe_dump(topology)
                with self.assertRaises(UserError):
                    make_bundle(directory, files=files)

    def test_reject_missing_extra_malformed_and_oversized_files(self):
        changes = [
            lambda f: f.pop("configs/switch-1/startup.cfg"),
            lambda f: f.pop("mappings/switch-1.json"),
            lambda f: f.update({"unreferenced.txt": "x"}),
            lambda f: f.update({"second.clab.yml": f["lab.clab.yaml"]}),
            lambda f: f.update({"configs/./other": "x"}),
            lambda f: f.update({"lab.clab.yaml": "[not a mapping]"}),
            lambda f: f.update({"lab.clab.yaml": "[invalid YAML"}),
            lambda f: f.update(
                {
                    "configs/switch-1/startup.cfg": "hostname switch-1\n"
                    + "!" * PAYLOAD_LIMIT
                }
            ),
        ]
        for change in changes:
            with (
                self.subTest(change=change),
                tempfile.TemporaryDirectory() as directory,
            ):
                with self.assertRaises(UserError):
                    make_bundle(directory, change, files=alternate_files())

    def test_oversized_manifest_fails_before_ownership_or_allocation(self):
        with tempfile.TemporaryDirectory() as directory:
            files = alternate_files(100, mapping=False)
            topology = yaml.safe_load(files["lab.clab.yaml"])
            topology["topology"]["nodes"]["switch-1"]["labels"] = {
                "padding": '"' * 600000
            }
            files["lab.clab.yaml"] = yaml.safe_dump(topology)
            bundle = make_bundle(directory, files=files)
        env = FakeEnvironment()
        with self.assertRaisesRegex(UserError, "manifest limit"):
            cloud.create_lab(env, bundle, IDENTITY)
        self.assertFalse(env.calls)
        self.assertFalse(env.applied)

    def test_manifest_payloads_preserve_all_files_within_kubernetes_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            files = alternate_files(100, padding="\u00e9" * 4096)
            bundle = make_bundle(directory, files=files)
        env = FakeEnvironment()
        record = cloud.create_lab(env, bundle, IDENTITY)
        secrets = {
            obj["metadata"]["name"]: obj
            for obj in env.applied
            if obj["kind"] == "Secret"
        }
        self.assertGreater(len(secrets), 1)
        for secret in secrets.values():
            self.assertLessEqual(
                sum(len(base64.b64decode(value)) for value in secret["data"].values()),
                PAYLOAD_LIMIT,
            )
            self.assertLessEqual(len(json.dumps(secret).encode()), 1024 * 1024)
        topology = next(obj for obj in env.applied if obj["kind"] == "Topology")
        definition = yaml.safe_load(topology["spec"]["definition"]["containerlab"])
        self.assertEqual(
            definition["topology"]["links"], bundle.topology["topology"]["links"]
        )
        references = topology["spec"]["deployment"]["filesFromSecret"]
        for name, node in definition["topology"]["nodes"].items():
            self.assertEqual(
                node["mgmt-ipv4"],
                bundle.topology["topology"]["nodes"][name]["mgmt-ipv4"],
            )
            delivered = {
                ref["filePath"]: base64.b64decode(
                    secrets[ref["secretName"]]["data"][ref["secretPath"]]
                ).decode()
                for ref in references[name]
            }
            self.assertEqual(
                delivered[node["startup-config"]], files[f"configs/{name}/startup.cfg"]
            )
            self.assertEqual(
                delivered[node["binds"][0].split(":")[0]],
                files[f"mappings/{name}.json"],
            )
        self.assertEqual(len(record["switches"]), 100)
        self.assertEqual(record["link_count"], 99)
        self.assertNotIn("hostname", json.dumps(record))


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bundle = make_bundle(self.temp.name)
        self.env = FakeEnvironment()

    def test_validation_precedes_allocation(self):
        for lifetime in (0, 241, True):
            with self.assertRaises(ValueError):
                cloud.create_lab(self.env, self.bundle, IDENTITY, lifetime)
        with self.assertRaises(ValueError):
            cloud.create_lab(self.env, self.bundle, {**IDENTITY, "attempt": ""})
        self.assertFalse(self.env.calls)

    def test_distinct_attempts_and_private_switches(self):
        first = cloud.create_lab(self.env, self.bundle, IDENTITY)
        second = cloud.create_lab(self.env, self.bundle, {**IDENTITY, "attempt": "2"})
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["provenance"]["commit"], second["provenance"]["commit"])
        topologies = [o for o in self.env.applied if o["kind"] == "Topology"]
        for obj in topologies:
            self.assertEqual(
                obj["spec"]["expose"],
                {"exposeType": "ClusterIP", "disableAutoExpose": True},
            )
            definition = yaml.safe_load(obj["spec"]["definition"]["containerlab"])
            self.assertEqual(set(definition["topology"]["nodes"]), NODES)
            self.assertTrue(
                all(
                    n.get("kind", definition["topology"]["defaults"]["kind"])
                    == "arista_ceos"
                    for n in definition["topology"]["nodes"].values()
                )
            )
        self.assertNotEqual(
            topologies[0]["metadata"]["namespace"],
            topologies[1]["metadata"]["namespace"],
        )
        deleted = cloud.delete_lab(self.env, first["id"])
        self.assertTrue(deleted["deleted"])
        self.assertEqual(
            [n["metadata"]["name"] for n in self.env.namespaces],
            [ENV.name + "-" + second["id"]],
        )
        self.assertTrue(cloud.delete_lab(self.env, first["id"])["deleted"])

    def test_partial_allocation_discovered_and_retried(self):
        self.env.fail_namespace = True
        with self.assertRaises(RuntimeError):
            cloud.create_lab(self.env, self.bundle, IDENTITY, lab=LAB)
        self.assertEqual(cloud.lab_record(self.env, LAB)["state"], "creating")
        self.env.fail_delete = True
        with patch("drydock.lifecycle.now", return_value=10**12):
            failed = cloud.reap(self.env)
            self.assertFalse(failed[0]["deleted"])
            self.assertTrue(cloud.lab_record(self.env, LAB)["overdue"])
            self.env.fail_delete = False
            self.assertTrue(cloud.reap(self.env)[0]["deleted"])
            # A late provider allocation is still removed after the record says deleted.
            self.env.namespaces.append(
                {
                    "metadata": {
                        "name": ENV.name + "-" + LAB,
                        "labels": {
                            ENV_LABEL: ENV.name,
                            LAB_LABEL: LAB,
                            ALLOCATION_LABEL: cloud.lab_record(self.env, LAB)[
                                "allocation_id"
                            ],
                        },
                        "uid": "late-namespace",
                        "resourceVersion": "1",
                    }
                }
            )
            self.assertTrue(cloud.reap(self.env)[0]["deleted"])
        self.assertFalse(self.env.namespaces)

    def test_refuse_foreign_namespace(self):
        cloud.create_lab(self.env, self.bundle, IDENTITY, lab=LAB)
        self.env.namespaces[0]["metadata"]["labels"] = {
            ENV_LABEL: "another",
            "unrelated": "label",
        }
        with self.assertRaises(ValueError):
            cloud.delete_lab(self.env, LAB)
        self.assertTrue(self.env.namespaces)

    def test_stale_update_cannot_undo_cleanup(self):
        cloud.create_lab(self.env, self.bundle, IDENTITY, lab=LAB)
        stale = cloud.lab_record(self.env, LAB)
        cloud.delete_lab(self.env, LAB)
        with self.assertRaises(RuntimeError):
            cloud.write_record(self.env, {**stale, "state": "running"})
        self.assertEqual(cloud.lab_record(self.env, LAB)["state"], "deleted")

    def test_repeated_input_creates_separate_owned_resources(self):
        first = cloud.create_lab(self.env, self.bundle, IDENTITY)
        second = cloud.create_lab(self.env, self.bundle, IDENTITY)
        self.assertNotEqual(first["id"], second["id"])
        self.assertNotEqual(first["allocation_id"], second["allocation_id"])
        self.assertEqual(first["bundle_digest"], second["bundle_digest"])
        namespace = ENV.name + "-" + second["id"]
        resources = [
            obj for obj in self.env.applied if obj["metadata"]["namespace"] == namespace
        ]
        record = cloud.lab_record(self.env, second["id"])
        cloud.delete_lab(self.env, first["id"])
        self.assertEqual(self.env.applied, resources)
        self.assertEqual(cloud.lab_record(self.env, second["id"]), record)

    def test_namespace_allocation_identity_is_required_for_status_and_deletion(self):
        cloud.create_lab(self.env, self.bundle, IDENTITY, lab=LAB)
        self.env.namespaces[0]["metadata"]["labels"][ALLOCATION_LABEL] = (
            "another-allocation"
        )
        with self.assertRaisesRegex(UserError, "ownership"):
            flow.snapshot(self.env, LAB)
        with self.assertRaisesRegex(UserError, "ownership"):
            cloud.delete_lab(self.env, LAB)
        self.assertTrue(self.env.namespaces)
        self.assertTrue(self.env.applied)

    def test_deletion_requires_a_record_for_an_existing_namespace(self):
        cloud.create_lab(self.env, self.bundle, IDENTITY, lab=LAB)
        self.env.records.clear()
        with self.assertRaisesRegex(UserError, "ownership"):
            cloud.delete_lab(self.env, LAB)
        self.assertTrue(self.env.namespaces)
        self.assertTrue(self.env.applied)

    def test_creation_stops_after_late_namespace_and_cleanup_revisits_it(self):
        original = self.env.kube

        def delayed_namespace(*args, data=None):
            if data and json.loads(data)["kind"] == "Namespace":
                self.assertTrue(cloud.delete_lab(self.env, LAB)["deleted"])
            return original(*args, data=data)

        with patch.object(self.env, "kube", side_effect=delayed_namespace):
            with self.assertRaisesRegex(UserError, "cleanup started"):
                cloud.create_lab(self.env, self.bundle, IDENTITY, lab=LAB)
        record = cloud.lab_record(self.env, LAB)
        self.assertEqual(record["state"], "deleted")
        self.assertTrue(self.env.namespaces)
        self.assertFalse(self.env.applied)
        self.assertTrue(cloud.reap(self.env)[0]["deleted"])
        self.assertFalse(self.env.namespaces)
        self.assertEqual(
            cloud.lab_record(self.env, LAB)["expires_at"], record["expires_at"]
        )

    def test_competing_final_update_cannot_restore_a_deleted_lab(self):
        original = self.env.kube
        deleted = None

        def competing_update(*args, data=None):
            nonlocal deleted
            obj = json.loads(data) if data else {}
            if (
                obj.get("kind") == "ConfigMap"
                and json.loads(obj["data"]["record"])["state"] == "running"
            ):
                cloud.delete_lab(self.env, LAB)
                deleted = cloud.lab_record(self.env, LAB)
            return original(*args, data=data)

        with patch.object(self.env, "kube", side_effect=competing_update):
            with self.assertRaisesRegex(RuntimeError, "Conflict"):
                cloud.create_lab(self.env, self.bundle, IDENTITY, lab=LAB)
        self.assertEqual(cloud.lab_record(self.env, LAB), deleted)
        self.assertFalse(self.env.namespaces)
        self.assertFalse(self.env.applied)

    def test_delete_preconditions_preserve_a_replaced_namespace(self):
        cloud.create_lab(self.env, self.bundle, IDENTITY, lab=LAB)
        original = self.env.kube

        def replace_namespace(*args, data=None):
            if args[0] == "delete":
                self.env.namespaces[0]["metadata"]["uid"] = "unrelated-replacement"
                self.env.namespaces[0]["metadata"]["labels"] = {"unrelated": "true"}
            return original(*args, data=data)

        with patch.object(self.env, "kube", side_effect=replace_namespace):
            self.assertFalse(cloud.delete_lab(self.env, LAB)["deleted"])
        self.assertEqual(
            self.env.namespaces[0]["metadata"]["uid"], "unrelated-replacement"
        )
        self.assertEqual(cloud.lab_record(self.env, LAB)["state"], "deleting")

    def test_changed_namespace_labels_prevent_a_pending_delete(self):
        cloud.create_lab(self.env, self.bundle, IDENTITY, lab=LAB)
        original = self.env.kube

        def change_labels(*args, data=None):
            if args[0] == "delete":
                self.env.namespaces[0]["metadata"]["resourceVersion"] = "2"
                self.env.namespaces[0]["metadata"]["labels"] = {"unrelated": "true"}
            return original(*args, data=data)

        with patch.object(self.env, "kube", side_effect=change_labels):
            self.assertFalse(cloud.delete_lab(self.env, LAB)["deleted"])
        self.assertTrue(self.env.namespaces)

    def test_allocation_stops_at_expiry_without_renewing_it(self):
        original = self.env.kube
        accepted = 1000

        def expired_namespace(*args, data=None):
            result = original(*args, data=data)
            if data and json.loads(data)["kind"] == "Namespace":
                clock.return_value = accepted + 60
            return result

        with patch("drydock.lifecycle.now", return_value=accepted) as clock:
            with patch.object(self.env, "kube", side_effect=expired_namespace):
                with self.assertRaisesRegex(UserError, "expired"):
                    cloud.create_lab(
                        self.env, self.bundle, IDENTITY, lifetime=1, lab=LAB
                    )
        self.assertEqual(cloud.lab_record(self.env, LAB)["expires_at"], accepted + 60)
        self.assertFalse(self.env.applied)


class ReadinessTests(unittest.TestCase):
    def test_probe_rejects_wrong_identity(self):
        with (
            patch(
                "drydock.flow.eapi",
                return_value=[{"hostname": "other"}, {"version": "test"}],
            ),
            self.assertRaises(ValueError),
        ):
            flow.probe([{"name": "leaf1", "port": 12345}], "secret")
        with patch("drydock.flow.snapshot", side_effect=OSError):
            self.assertIsNone(flow.available_probe(ENV, LAB, "secret"))

    def test_empty_and_stale_readiness_fail(self):
        self.assertTrue(readiness([], NODES, 12))
        self.assertIn(
            "topology is not current and ready",
            readiness(
                [
                    {
                        "kind": "Topology",
                        "metadata": {"generation": 2},
                        "status": {
                            "observedGeneration": 1,
                            "topologyReady": True,
                            "topologyState": "running",
                        },
                    }
                ],
                NODES,
                12,
            ),
        )

    def test_status_probes_api_and_preserves_switch_identities(self):
        with (
            patch(
                "drydock.flow.snapshot",
                return_value=({"switches": sorted(NODES)}, switch_pods(), []),
            ),
            patch("drydock.flow.probe", side_effect=OSError),
        ):
            result = flow.status(ENV, LAB, "secret")
        self.assertFalse(result["ready"])
        self.assertEqual({host["name"] for host in result["inventory"]}, NODES)
        self.assertTrue(
            all(
                host["host"].startswith("10.251.") and host["pod_uid"]
                for host in result["inventory"]
            )
        )
        with (
            patch(
                "drydock.flow.snapshot",
                return_value=({"switches": sorted(NODES)}, switch_pods(), []),
            ),
            patch(
                "drydock.flow.eapi",
                side_effect=lambda host, password, commands: [
                    {"hostname": host["name"]},
                    {"version": "test"},
                ],
            ),
        ):
            self.assertTrue(flow.status(ENV, LAB, "secret")["ready"])

    def test_connections_reject_missing_duplicate_and_invalid_pods(self):
        pods = switch_pods()
        variants = [pods[:-1], pods + [pods[0]], [pods[0]] * len(NODES)]
        for address in (
            "",
            "not-an-ip",
            "8.8.8.8",
            "127.0.0.1",
            "169.254.1.1",
            "0.0.0.0",
            "::1",
        ):
            changed = switch_pods()
            changed[0]["status"]["podIP"] = address
            variants.append(changed)
        for field in ("uid", "deletionTimestamp"):
            changed = switch_pods()
            changed[0]["metadata"][field] = (
                "" if field == "uid" else "2026-11-11T00:00:00Z"
            )
            variants.append(changed)
        duplicate_ip = switch_pods()
        duplicate_ip[0]["status"]["podIP"] = duplicate_ip[1]["status"]["podIP"]
        variants.append(duplicate_ip)
        for items in variants:
            with self.subTest(items=items), self.assertRaises(ValueError):
                flow.connections(items, NODES)

    def test_readiness_discovers_replacement_pod_and_preserves_probe_gate(self):
        first, second = switch_pods(), switch_pods()
        second[0]["metadata"].update(name="replacement", uid="new-uid")
        second[0]["status"]["podIP"] = "10.251.2.42"
        with (
            patch(
                "drydock.flow.snapshot",
                side_effect=[
                    ({"switches": sorted(NODES)}, first, []),
                    ({"switches": sorted(NODES)}, second, []),
                ],
            ),
            patch(
                "drydock.flow.probe", side_effect=[OSError, {n: "test" for n in NODES}]
            ) as probe,
        ):
            self.assertIsNone(flow.available_probe(ENV, LAB, "secret"))
            hosts, versions = flow.available_probe(ENV, LAB, "secret")
        self.assertEqual(hosts[0]["host"], "10.251.2.42")
        self.assertEqual(hosts[0]["pod_uid"], "new-uid")
        self.assertEqual(probe.call_args.args[0], hosts)
        self.assertEqual(set(versions), NODES)
        with (
            patch("drydock.flow.snapshot", return_value=({}, first, ["not ready"])),
            patch("drydock.flow.probe") as probe,
        ):
            self.assertIsNone(flow.available_probe(ENV, LAB, "secret"))
            probe.assert_not_called()

    def test_eapi_uses_discovered_address_with_demo_tls_policy(self):
        response = io.BytesIO(b'{"result": [{"hostname": "leaf1"}]}')
        with patch("drydock.flow.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value = response
            flow.eapi({"host": "10.251.2.42", "port": 443}, "secret", ["show hostname"])
        args, kwargs = urlopen.call_args
        self.assertEqual(args[0].full_url, "https://10.251.2.42:443/command-api")
        import ssl

        self.assertEqual(kwargs["context"].verify_mode, ssl.CERT_NONE)


def switch_pods(names=NODES):
    return [
        {
            "kind": "Pod",
            "metadata": {
                "name": name + "-pod",
                "uid": name + "-uid",
                "labels": {"c9s.run/direct-workload": name},
            },
            "status": {"podIP": f"10.251.1.{index + 10}"},
        }
        for index, name in enumerate(sorted(names))
    ]
