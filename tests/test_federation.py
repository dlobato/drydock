"""Operator federation setup never enables access or grants cloud administration."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FederationTests(unittest.TestCase):
    def configure(self, revision):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            command = directory / "gcloud"
            command.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "with open(os.environ['COMMAND_LOG'], 'a') as stream:\n"
                "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "if sys.argv[1:3] == ['projects', 'describe']:\n"
                "    print('123456789')\n"
            )
            command.chmod(0o700)
            log = directory / "commands"
            result = subprocess.run(
                ["bash", str(ROOT / "examples/github/configure-federation.sh")],
                env={
                    **os.environ,
                    "PATH": str(directory) + os.pathsep + os.environ["PATH"],
                    "DRYDOCK_PROJECT": "test-project",
                    "DRYDOCK_WORKFLOW_SHA": revision,
                    "COMMAND_LOG": str(log),
                },
                capture_output=True,
                text=True,
            )
            commands = (
                [json.loads(line) for line in log.read_text().splitlines()]
                if log.exists()
                else []
            )
            return result, commands

    def test_invalid_revision_changes_nothing(self):
        for revision in ("main", "a" * 39, "a" * 41, "A" * 40):
            with self.subTest(revision=revision):
                result, commands = self.configure(revision)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(commands, [])

    def test_provider_stays_disabled_and_pins_all_trust_claims(self):
        revision = "a" * 40
        result, commands = self.configure(revision)
        self.assertEqual(result.returncode, 0, result.stderr)
        services = next(
            command for command in commands if command[:2] == ["services", "enable"]
        )
        self.assertIn("cloudresourcemanager.googleapis.com", services)
        provider = next(command for command in commands if "create-oidc" in command)
        self.assertIn("--disabled", provider)
        condition = next(
            arg for arg in provider if arg.startswith("--attribute-condition=")
        )
        for restriction in (
            "assertion.repository_id == '1452964696'",
            "assertion.repository_owner_id == '1379455'",
            "assertion.sub == 'repo:dlobato@1379455/drydock@1452964696:environment:gke'",
            "assertion.ref == 'refs/heads/main'",
            "assertion.workflow_ref == 'dlobato/drydock/.github/workflows/pre-deployment.yml@refs/heads/main'",
            f"assertion.workflow_sha == '{revision}'",
            "assertion.event_name in ['workflow_dispatch', 'pull_request_target']",
        ):
            self.assertIn(restriction, condition)
        role = next(
            command for command in commands if command[:3] == ["iam", "roles", "create"]
        )
        self.assertIn("--permissions=container.clusters.get", role)
        grants = [
            command for command in commands if "add-iam-policy-binding" in command
        ]
        self.assertEqual(len(grants), 2)
        self.assertIn("--role=roles/iam.workloadIdentityUser", grants[0])
        self.assertIn(
            "--member=principal://iam.googleapis.com/projects/123456789/locations/global/workloadIdentityPools/drydock-github/subject/repo:dlobato@1379455/drydock@1452964696:environment:gke",
            grants[0],
        )
        self.assertIn(
            "--role=projects/test-project/roles/drydockClusterConnection", grants[1]
        )
        self.assertFalse(
            any("enable" in command and "providers" in command for command in commands)
        )


if __name__ == "__main__":
    unittest.main()
