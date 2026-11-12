"""Offline contract tests. No provider calls or device images."""

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
from drydock.core import ENV_LABEL, LAB_LABEL, NODES, Bundle, Environment, readiness

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


def make_bundle(directory, mutate=None):
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
                self.namespaces.append(obj)
                if self.fail_namespace:
                    raise RuntimeError(
                        "namespace creation interrupted after acceptance"
                    )
        elif args[0] == "delete":
            if self.fail_delete:
                raise RuntimeError("namespace deletion failed")
            self.namespaces = [
                n for n in self.namespaces if n["metadata"]["name"] != args[2]
            ]
        return "{}"

    def apply(self, obj):
        self.applied.append(obj)


class BundleTests(unittest.TestCase):
    def test_valid_bundle_preserves_identities(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = make_bundle(directory)
        self.assertEqual(set(bundle.interfaces), NODES)

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
            lambda f: f.update({"intended/configs/leaf1.cfg": "hostname wrong\n"}),
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
                    n["kind"] == "arista_ceos"
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
                        "labels": {ENV_LABEL: ENV.name, LAB_LABEL: LAB},
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
        self.assertTrue(readiness([]))
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
                ]
            ),
        )

    def test_status_probes_api_and_preserves_switch_identities(self):
        with (
            patch("drydock.flow.snapshot", return_value=({}, switch_pods(), [])),
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
            patch("drydock.flow.snapshot", return_value=({}, switch_pods(), [])),
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
                flow.connections(items)

    def test_readiness_discovers_replacement_pod_and_preserves_probe_gate(self):
        first, second = switch_pods(), switch_pods()
        second[0]["metadata"].update(name="replacement", uid="new-uid")
        second[0]["status"]["podIP"] = "10.251.2.42"
        with (
            patch(
                "drydock.flow.snapshot", side_effect=[({}, first, []), ({}, second, [])]
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


def switch_pods():
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
        for index, name in enumerate(sorted(NODES))
    ]
