"""Operator runner disposal and management credential isolation."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from examples.github.runner_vm import RunnerVM, command


class RunnerDispatcherTests(unittest.TestCase):
    def runner(self, directory):
        configuration = {
            "project": "drydock-513410",
            "zone": "europe-west1-b",
            "subnetwork": "drydock-access",
            "image": "projects/ubuntu-os-cloud/global/images/ubuntu-2404-noble-amd64-v20261105",
        }
        runner = object.__new__(RunnerVM)
        runner.configuration = configuration
        runner.directory = Path(directory)
        runner.name = "drydock-runner-123-1-abcdef012345"
        runner.project = configuration["project"]
        runner.zone = configuration["zone"]
        runner.key = runner.directory / "ssh-key"
        runner.record = runner.directory / "vm.json"
        return runner

    def test_gcloud_does_not_inherit_github_or_kubernetes_credentials(self):
        with (
            patch.dict(
                "os.environ",
                {
                    "GH_TOKEN": "operator-only",
                    "GITHUB_TOKEN": "other",
                    "KUBECONFIG": "admin",
                    "CLOUDSDK_CONFIG": "operator-profile",
                },
            ),
            patch("examples.github.runner_vm.subprocess.run") as run,
        ):
            run.return_value.returncode = 0
            run.return_value.stdout = "{}"
            command(["gcloud", "compute", "instances", "list"])
            environment = run.call_args.kwargs["env"]
            self.assertNotIn("GH_TOKEN", environment)
            self.assertNotIn("GITHUB_TOKEN", environment)
            self.assertNotIn("KUBECONFIG", environment)
            self.assertEqual(environment["CLOUDSDK_CONFIG"], "operator-profile")

    def test_runner_failure_still_deletes_compute_and_ephemeral_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = self.runner(directory)
            runner.key.write_text("synthetic-private-key")
            runner.key.with_suffix(".pub").write_text("synthetic-public-key")
            with (
                patch.object(runner, "instances", return_value=[]),
                patch.object(runner, "create"),
                patch.object(runner, "check_run"),
                patch.object(
                    runner, "ssh", side_effect=["", RuntimeError("job failed")]
                ),
                patch.object(runner, "dispose") as dispose,
            ):
                with self.assertRaisesRegex(RuntimeError, "job failed"):
                    runner.run("synthetic-registration")
            dispose.assert_called_once()
            self.assertFalse(runner.key.exists())
            self.assertFalse(runner.key.with_suffix(".pub").exists())
            record = json.loads(runner.record.read_text())
            self.assertEqual(record["state"], "deleted")
            self.assertNotIn("synthetic-registration", runner.record.read_text())

    def test_cleanup_preserves_an_unrelated_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = self.runner(directory)
            with (
                patch.object(
                    runner,
                    "instances",
                    return_value=[{"labels": {"drydock-dispatcher": "another-owner"}}],
                ),
                patch.object(runner, "gcloud", return_value="[]") as gcloud,
            ):
                with self.assertRaisesRegex(RuntimeError, "ownership differs"):
                    runner.dispose()
            self.assertFalse(
                any("delete" in call.args for call in gcloud.call_args_list)
            )

    def test_vm_has_no_cloud_identity_and_has_a_cloud_deletion_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = self.runner(directory)
            runner.key.with_suffix(".pub").write_text("ssh-ed25519 synthetic")
            with (
                patch("examples.github.runner_vm.command"),
                patch.object(runner, "gcloud") as gcloud,
            ):
                runner.create()
            args = gcloud.call_args.args
            self.assertIn("--no-service-account", args)
            self.assertIn("--no-address", args)
            self.assertIn("--no-scopes", args)
            self.assertIn("--max-run-duration=900s", args)
            self.assertIn("--instance-termination-action=DELETE", args)
            self.assertIn("--boot-disk-auto-delete", args)

    def test_guard_kills_the_runner_group_before_any_further_steps(self):
        startup = Path("examples/github/runner-startup.sh").read_text()
        guard = startup.split("cat > /opt/drydock-guard.py <<'PY'\n")[1].split(
            "\nPY\n"
        )[0]
        with tempfile.TemporaryDirectory() as directory:
            expected = Path(directory) / "expected.json"
            expected.write_text(
                json.dumps({"GITHUB_RUN_ID": "123", "GITHUB_WORKFLOW_SHA": "a" * 40})
            )
            script = Path(directory) / "guard.py"
            script.write_text(
                guard.replace("/opt/drydock-expected.json", str(expected))
            )
            environment = dict(
                os.environ,
                GITHUB_RUN_ID="123",
                GITHUB_WORKFLOW_SHA="a" * 40,
                GITHUB_EVENT_NAME="workflow_dispatch",
            )
            accepted = subprocess.run(
                ["python3", "-I", str(script)],
                env=environment,
                start_new_session=True,
                capture_output=True,
            )
            self.assertEqual(accepted.returncode, 0)
            environment["GITHUB_RUN_ID"] = "124"
            marker = Path(directory) / "unexpected-step"
            denied = subprocess.run(
                [
                    "python3",
                    "-c",
                    "import subprocess,sys; subprocess.run([sys.executable, '-I', sys.argv[1]]); open(sys.argv[2], 'w').write('ran')",
                    str(script),
                    str(marker),
                ],
                env=environment,
                start_new_session=True,
                capture_output=True,
            )
            self.assertEqual(denied.returncode, -9)
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
