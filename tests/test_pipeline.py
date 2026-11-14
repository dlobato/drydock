"""Pipeline failure recovery, input boundaries, and credential separation."""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from examples.github import gke_credentials, pipeline

IMAGE = "example.invalid/toolchain@sha256:" + "a" * 64
CLUSTER = "projects/test-project/locations/europe-west1-b/clusters/lab"


class PipelineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.state = self.directory / "state"
        self.state.mkdir()
        for name in ("input", "validated", "lifecycle", "test-output", "reports"):
            (self.state / name).mkdir()
        self.data = {
            "image": IMAGE,
            "allocation_id": "b" * 32,
            "lab": "lab-" + "b" * 12,
            "provenance": {
                "repository": "dlobato/drydock",
                "commit": "c" * 40,
                "run": "42",
                "attempt": "1",
            },
        }
        pipeline.save(self.state / "state.json", self.data)
        (self.state / "lab.env").write_text("DRYDOCK_LAB_PASSWORD=lab-only\n")
        self.credentials = self.directory / "credentials.json"
        self.credentials.write_text(
            json.dumps(
                {
                    "type": "external_account",
                    "service_account_impersonation_url": "https://iamcredentials.googleapis.com/test",
                    "credential_source": {"headers": {"Authorization": "TOP-SECRET"}},
                }
            )
        )

    def test_only_lifecycle_containers_receive_federation_and_no_container_gets_runner_tokens(
        self,
    ):
        calls = []
        with (
            patch.object(
                pipeline, "command", side_effect=lambda args, **kw: calls.append(args)
            ),
            patch.object(pipeline.subprocess, "run"),
            patch.dict(
                os.environ,
                {
                    "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "runner-only",
                    "GITHUB_TOKEN": "also-runner-only",
                },
            ),
        ):
            for stage in ("build", "preflight", "test", "create", "wait", "delete"):
                pipeline.container(
                    self.state,
                    stage,
                    [],
                    credentialed=stage in {"create", "wait", "delete"},
                )
        for stage, args in zip(
            ("build", "preflight", "test", "create", "wait", "delete"),
            calls,
            strict=True,
        ):
            text = " ".join(args)
            self.assertNotIn("runner-only", text)
            self.assertNotIn("ACTIONS_ID_TOKEN", text)
            self.assertNotIn("docker.sock", text)
            self.assertNotIn("--privileged", text)
            self.assertIn("--cap-drop=ALL", args)
            self.assertIn("--read-only", args)
            self.assertEqual(
                "/credentials/google.json" in text,
                stage in {"create", "wait", "delete"},
            )
            self.assertEqual("--network=none" in args, stage in {"build", "preflight"})

    def test_each_allocated_failure_stage_requests_deletion_and_never_claims_success(
        self,
    ):
        for failure in (None, "create", "wait", "test", "report", "cancel", "delete"):
            with self.subTest(failure=failure):
                stages = []

                def run(state, stage, mounts, **kwargs):
                    stages.append(stage)
                    if stage == "create":
                        pipeline.save(
                            state / "lifecycle/allocation.json",
                            {
                                "lab": self.data["lab"],
                                "allocation_id": self.data["allocation_id"],
                            },
                        )
                    if stage == failure or (stage == "test" and failure == "cancel"):
                        raise (
                            KeyboardInterrupt
                            if failure == "cancel"
                            else RuntimeError("test failure")
                        )
                    if stage == "wait":
                        pipeline.save(
                            state / "lifecycle/inventory.json",
                            {
                                "inventory": [],
                                "record": {
                                    "expires_at": time.time() + 1000,
                                    "bundle_digest": "digest",
                                },
                            },
                        )
                    if stage == "test":
                        if failure == "report":
                            raise OSError("report write failed")
                        pipeline.save(
                            state / "test-output/tests.json",
                            {"passed": True, "required": 54},
                        )
                    if stage == "delete":
                        pipeline.save(
                            state / "lifecycle/cleanup.json", {"deleted": True}
                        )

                (self.state / "reports/tests.json").unlink(missing_ok=True)
                (self.state / "test-output/tests.json").unlink(missing_ok=True)
                with patch.object(pipeline, "container", side_effect=run):
                    result = pipeline.execute(
                        self.state, self.credentials, CLUSTER, "drydock-test"
                    )
                self.assertEqual(stages[-1], "delete")
                self.assertEqual(result["passed"], failure is None)
                self.assertEqual(result["cleanup"].get("deleted"), failure != "delete")
                self.assertNotIn(
                    "TOP-SECRET", (self.state / "reports/run.json").read_text()
                )
                self.assertTrue((self.state / "lifecycle/allocation.json").exists())
                credentials = json.loads((self.state / "google.json").read_text())
                self.assertEqual(
                    credentials["service_account_impersonation"][
                        "token_lifetime_seconds"
                    ],
                    900,
                )

    def test_no_allocation_when_build_or_preflight_fails(self):
        environment = {
            "GITHUB_REPOSITORY": "dlobato/drydock",
            "PR_COMMIT": "c" * 40,
            "GITHUB_RUN_ID": "42",
            "GITHUB_RUN_ATTEMPT": "1",
        }
        for failure in ("build", "preflight"):
            with self.subTest(failure=failure), patch.dict(os.environ, environment):

                def run(state, stage, mounts, **kwargs):
                    if stage == failure:
                        raise RuntimeError("failed")

                with patch.object(pipeline, "container", side_effect=run) as launch:
                    with self.assertRaises(RuntimeError):
                        pipeline.prepare(self.directory, IMAGE, IMAGE, self.directory)
                self.assertEqual(launch.call_args.args[1], failure)
                self.assertFalse(list(self.directory.glob("drydock-pipeline-*")))

    def test_malicious_build_cannot_smuggle_links_into_credentialed_containers(self):
        for kind in ("symlink", "directory-link", "hardlink", "fifo"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "raw"
                source.mkdir()
                path = source / "payload"
                if kind == "symlink":
                    path.symlink_to(self.credentials)
                elif kind == "directory-link":
                    path.symlink_to(self.directory, target_is_directory=True)
                elif kind == "hardlink":
                    os.link(self.credentials, path)
                else:
                    os.mkfifo(path)
                with self.assertRaises(ValueError):
                    pipeline.snapshot(source, Path(directory) / "input")

    def test_cleanup_without_an_allocation_needs_no_credentials(self):
        with patch.object(pipeline, "container") as run:
            self.assertTrue(pipeline.cleanup(self.state)["deleted"])
        run.assert_not_called()

    def test_docker_client_failure_still_removes_the_whole_container(self):
        with (
            patch.object(pipeline, "command", side_effect=TimeoutError),
            patch.object(pipeline.subprocess, "run") as remove,
        ):
            with self.assertRaises(TimeoutError):
                pipeline.container(self.state, "build", [])
        self.assertEqual(remove.call_args.args[0][:3], ["docker", "rm", "--force"])


class GkeCredentialTests(unittest.TestCase):
    def test_each_exec_can_renew_a_short_token_with_email_identity(self):
        with patch.object(
            gke_credentials.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0, stdout="temporary-token\n"),
        ) as run:
            for _ in range(2):
                result = gke_credentials.token()
                self.assertEqual(result["status"]["token"], "temporary-token")
                self.assertEqual(result["kind"], "ExecCredential")
        self.assertEqual(run.call_count, 2)
        self.assertIn("userinfo.email", " ".join(run.call_args.args[0]))
        self.assertNotIn("temporary-token", " ".join(run.call_args.args[0]))

    def test_renewal_failure_does_not_return_a_stale_token(self):
        with patch.object(
            gke_credentials.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=1, stdout=""),
        ):
            with self.assertRaises(RuntimeError):
                gke_credentials.token()

    def test_private_endpoint_keeps_ca_verification_and_exec_renewal(self):
        metadata = {
            "privateClusterConfig": {"privateEndpoint": "10.1.2.3"},
            "masterAuth": {"clusterCaCertificate": "cluster-ca"},
        }
        with (
            patch.object(
                gke_credentials.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0, stdout=json.dumps(metadata)),
            ),
            patch.object(gke_credentials, "save") as save,
            patch.object(gke_credentials.Environment, "load"),
        ):
            gke_credentials.configure(CLUSTER, "drydock-test")
        connection = save.call_args_list[0].args[1]
        self.assertEqual(
            connection["clusters"][0]["cluster"],
            {"server": "https://10.1.2.3", "certificate-authority-data": "cluster-ca"},
        )
        self.assertIn("exec", connection["users"][0]["user"])
        self.assertNotIn("token", connection["users"][0]["user"])


if __name__ == "__main__":
    unittest.main()
