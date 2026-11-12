"""Exercise CLI results through a Kubernetes-only test boundary."""

import io
import json
import os
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml
from test_lifecycle import (
    ENV,
    IDENTITY,
    NODES,
    FakeEnvironment,
    alternate_files,
    make_bundle,
    switch_pods,
)

from drydock import __main__ as cli
from drydock.core import Environment


def ready_items(names=NODES, link_count=12):
    items = [
        {
            "kind": "Topology",
            "metadata": {"name": "fabric", "generation": 1},
            "status": {
                "observedGeneration": 1,
                "topologyReady": True,
                "topologyState": "running",
            },
        }
    ]
    for name in sorted(names):
        items.append(
            {
                "kind": "Node",
                "metadata": {"name": name, "generation": 1},
                "status": {
                    "readiness": "ready",
                    "planDigest": "digest",
                    "conditions": [
                        {"type": kind, "status": "True", "observedGeneration": 1}
                        for kind in (
                            "PlanApplied",
                            "Prepared",
                            "ConnectivityReady",
                            "ContainersReady",
                        )
                    ],
                },
            }
        )
        items.append(
            {
                "kind": "Service",
                "metadata": {"name": name},
                "spec": {"type": "ClusterIP", "ports": [{"port": 443}]},
            }
        )
    items.extend(
        {
            "kind": "Link",
            "status": {"conditions": [{"type": "Accepted", "status": "True"}]},
        }
        for _ in range(link_count)
    )
    for pod in switch_pods(names):
        pod["status"]["conditions"] = [{"type": "Ready", "status": "True"}]
        items.append(pod)
    return items


class LifecycleCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.backend = FakeEnvironment()
        self.environment = self.directory / "environment.yml"
        self.environment.write_text(yaml.safe_dump(asdict(ENV)))
        make_bundle(self.directory)
        self.create_args = ["lab", "create", str(self.directory / "bundle.tar")]
        for key, value in IDENTITY.items():
            self.create_args.extend(["--" + key, value])
        runner = patch("drydock.core.run", side_effect=self.kubectl)
        runner.start()
        self.addCleanup(runner.stop)
        # The CLI sets a restrictive process umask for files that contain private input.
        previous = os.umask(0o077)
        self.addCleanup(os.umask, previous)

    def kubectl(self, command, *, data=None):
        prefix = ENV.kube_command()
        self.assertEqual(command[: len(prefix)], prefix)
        args = command[len(prefix) :]
        if args[0] == "get":
            namespace = args[args.index("-n") + 1] if "-n" in args else None
            labels = args[args.index("-l") + 1] if "-l" in args else None
            items = self.backend.objects(args[1], namespace, labels)
            if args[1].startswith("topologies."):
                lab = namespace.removeprefix(ENV.name + "-")
                record = self.backend.records[lab]
                record = json.loads(record["data"]["record"])
                items = ready_items(record["switches"], record["link_count"])
            return json.dumps({"items": items})
        if args[0] == "apply":
            self.backend.apply(json.loads(data))
            return "{}"
        return self.backend.kube(*args, data=data)

    def invoke(self, *args):
        output = io.StringIO()
        with redirect_stdout(output):
            code = cli.main(["--environment", str(self.environment), *args])
        return code, json.loads(output.getvalue())

    def test_create_authenticated_status_delete_and_repeat_without_demo_dependencies(
        self,
    ):
        code, record = self.invoke(*self.create_args)
        self.assertEqual(code, 0)
        lab = record["id"]
        self.assertEqual(record["state"], "running")
        self.assertEqual(record["provenance"], IDENTITY)
        with (
            patch.dict(os.environ, {"DRYDOCK_LAB_PASSWORD": "test-only"}),
            patch(
                "drydock.flow.eapi",
                side_effect=lambda host, password, commands: [
                    {"hostname": host["name"]},
                    {"version": "test"},
                ],
            ),
        ):
            code, result = self.invoke("lab", "status", lab)
        self.assertEqual(code, 0)
        self.assertTrue(result["ready"])
        self.assertEqual({host["name"] for host in result["inventory"]}, NODES)
        for _ in range(2):
            code, result = self.invoke("lab", "delete", lab)
            self.assertEqual(code, 0)
            self.assertTrue(result["deleted"])
        self.assertFalse(self.backend.namespaces)

    def test_failed_creation_cleans_up_and_returns_failure(self):
        self.backend.fail_namespace = True
        code, result = self.invoke(*self.create_args)
        self.assertEqual(code, 1)
        self.assertTrue(result["cleanup"]["deleted"])
        self.assertFalse(self.backend.namespaces)

    def test_id_collision_never_cleans_up_the_existing_lab(self):
        code, existing = self.invoke(*self.create_args)
        self.assertEqual(code, 0)
        resources = list(self.backend.applied)
        namespaces = list(self.backend.namespaces)
        records = json.loads(json.dumps(self.backend.records))
        collision = SimpleNamespace(hex=existing["id"].removeprefix("lab-") + "b" * 20)
        self.assertNotEqual(collision.hex, existing["allocation_id"])
        with patch("uuid.uuid4", return_value=collision):
            code, result = self.invoke(*self.create_args)
        self.assertEqual(code, 1)
        self.assertFalse(result["cleanup"]["deleted"])
        self.assertIn("ownership", result["cleanup"]["error"])
        self.assertEqual(self.backend.applied, resources)
        self.assertEqual(self.backend.namespaces, namespaces)
        self.assertEqual(self.backend.records, records)

    def test_lost_ownership_response_still_cleans_up_its_own_record(self):
        original = self.backend.kube

        def lost_response(*args, data=None):
            result = original(*args, data=data)
            if args[0] == "create" and json.loads(data)["kind"] == "ConfigMap":
                raise TimeoutError("private-provider-output")
            return result

        with patch.object(self.backend, "kube", side_effect=lost_response):
            code, result = self.invoke(*self.create_args)
        self.assertEqual(code, 1)
        self.assertEqual(result["error"], "TimeoutError")
        self.assertTrue(result["cleanup"]["deleted"])
        self.assertNotIn("private-provider-output", json.dumps(result))
        self.assertEqual(
            json.loads(self.backend.records[result["lab"]]["data"]["record"])["state"],
            "deleted",
        )
        self.assertFalse(self.backend.namespaces)

    def test_unconfirmed_ownership_returns_failure_without_allocating(self):
        with patch.object(
            self.backend, "kube", side_effect=TimeoutError("private-provider-output")
        ):
            code, result = self.invoke(*self.create_args)
        self.assertEqual(code, 1)
        self.assertFalse(result["cleanup"]["deleted"])
        self.assertIn("ownership", result["cleanup"]["error"])
        self.assertNotIn("private-provider-output", json.dumps(result))
        self.assertFalse(self.backend.records)
        self.assertFalse(self.backend.namespaces)
        self.assertFalse(self.backend.applied)

    def test_alternate_fabrics_through_create_status_and_delete(self):
        for count, mapping in ((1, False), (3, True), (100, False)):
            with self.subTest(count=count, mapping=mapping):
                bundle = make_bundle(
                    self.directory, files=alternate_files(count, mapping=mapping)
                )
                code, record = self.invoke(*self.create_args)
                self.assertEqual(code, 0)
                self.assertEqual(record["bundle_digest"], bundle.digest)
                lab = record["id"]
                with (
                    patch.dict(os.environ, {"DRYDOCK_LAB_PASSWORD": "test-only"}),
                    patch(
                        "drydock.flow.eapi",
                        side_effect=lambda host, password, commands: [
                            {"hostname": host["name"]},
                            {"version": "test"},
                        ],
                    ),
                ):
                    code, result = self.invoke("lab", "status", lab)
                self.assertEqual(code, 0)
                self.assertEqual(
                    {host["name"] for host in result["inventory"]},
                    set(bundle.topology["topology"]["nodes"]),
                )
                for _ in range(2):
                    code, result = self.invoke("lab", "delete", lab)
                    self.assertEqual(code, 0)
                    self.assertTrue(result["deleted"])

    def test_invalid_input_returns_safe_error_before_kubernetes_calls(self):
        files = alternate_files()
        files["configs/switch-2/startup.cfg"] = "hostname switch-2\n! private-marker"
        files.pop("configs/switch-1/startup.cfg")
        with tarfile.open(self.directory / "bundle.tar", "w") as archive:
            for name, text in files.items():
                member = tarfile.TarInfo(name)
                member.size = len(text.encode())
                archive.addfile(member, io.BytesIO(text.encode()))
        code, result = self.invoke(*self.create_args)
        self.assertEqual(code, 1)
        self.assertIn("referenced files", result["error"])
        self.assertNotIn("private-marker", json.dumps(result))
        self.assertFalse(self.backend.calls)
        self.assertFalse(self.backend.applied)

    def test_interrupted_secret_creation_cleans_up_before_topology_allocation(self):
        original = self.backend.kube

        def fail_secret(*args, data=None):
            result = original(*args, data=data)
            if data and json.loads(data)["kind"] == "Secret":
                raise RuntimeError("interrupted after Secret creation")
            return result

        with patch.object(self.backend, "kube", side_effect=fail_secret):
            code, result = self.invoke(*self.create_args)
        self.assertEqual(code, 1)
        self.assertTrue(result["cleanup"]["deleted"])
        self.assertFalse(self.backend.namespaces)
        self.assertFalse(any(obj["kind"] == "Topology" for obj in self.backend.applied))

    def test_expired_lab_is_removed_by_reap(self):
        code, record = self.invoke(*self.create_args)
        self.assertEqual(code, 0)
        with patch("drydock.lifecycle.now", return_value=record["expires_at"] + 1):
            code, result = self.invoke("reap")
        self.assertEqual(code, 0)
        self.assertTrue(result["cleanup"][0]["deleted"])
        self.assertFalse(self.backend.namespaces)

    def test_core_help_excludes_demo_commands(self):
        parser = cli.parser()
        parser.prog = "drydock"
        help_text = parser.format_help()
        self.assertIn("{lab,reap}", help_text)
        self.assertNotIn("infra", help_text)
        self.assertNotIn("test", help_text)

    def test_context_is_explicit_even_inside_kubernetes(self):
        with patch.dict(os.environ, {"KUBERNETES_SERVICE_HOST": "test-cluster"}):
            self.assertEqual(
                Environment.load(self.environment).kube_command("get", "namespaces"),
                [*ENV.kube_command(), "get", "namespaces"],
            )
