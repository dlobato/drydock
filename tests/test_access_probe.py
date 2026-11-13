"""The trusted access probe rejects excess access and removes temporary credentials."""

import importlib.util
import json
import stat
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "access_probe", ROOT / ".github/scripts/probe-gke-access.py"
)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class AccessProbeTests(unittest.TestCase):
    def setUp(self):
        self.paths = []
        self.api = patch.object(
            probe,
            "api",
            side_effect=[
                {
                    "privateClusterConfig": {"privateEndpoint": "10.1.2.3"},
                    "masterAuth": {"clusterCaCertificate": "test-ca"},
                },
                {"permissions": ["container.clusters.get"]},
            ],
        )
        self.api.start()
        self.addCleanup(self.api.stop)
        self.excess = False
        self.username = "workflow-user"

    def kubectl(self, command, **kwargs):
        self.assertNotIn("test-token", " ".join(command))
        self.assertNotIn("--insecure-skip-tls-verify", command)
        path = Path(command[command.index("--kubeconfig") + 1])
        self.paths.append(path)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        connection = json.loads(path.read_text())
        self.assertEqual(connection["users"][0]["user"], {"token": "test-token"})
        self.assertEqual(
            connection["clusters"][0]["cluster"],
            {"server": "https://10.1.2.3", "certificate-authority-data": "test-ca"},
        )
        self.assertTrue(kwargs["capture_output"])
        if "whoami" in command:
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {"status": {"userInfo": {"username": self.username}}}
                ),
            )
        if "can-i" in command:
            return SimpleNamespace(
                returncode=0 if self.excess else 1,
                stdout="yes" if self.excess else "no",
            )
        return SimpleNamespace(returncode=0, stdout="")

    def run_probe(self):
        with patch.object(probe.subprocess, "run", side_effect=self.kubectl):
            return probe.probe(
                "test-token",
                "projects/test-project/locations/europe-west1-b/clusters/test-cluster",
                "drydock-demo-system",
                "workflow-user",
            )

    def test_only_explicit_denials_pass_and_no_credentials_survive(self):
        result = self.run_probe()
        self.assertFalse(result["lab_created"])
        self.assertEqual(result["kubernetes_denials"], 8)
        self.assertTrue(self.paths)
        self.assertTrue(all(not path.parent.exists() for path in self.paths))

    def test_excess_kubernetes_access_and_wrong_identity_fail_without_leaving_files(
        self,
    ):
        self.excess = True
        with self.assertRaisesRegex(ValueError, "explicitly denied"):
            self.run_probe()
        self.assertTrue(all(not path.parent.exists() for path in self.paths))

    def test_wrong_identity_fails(self):
        self.username = "cluster-admin"
        with self.assertRaisesRegex(ValueError, "identity"):
            self.run_probe()
        self.assertTrue(all(not path.parent.exists() for path in self.paths))

    def test_invalid_cluster_resource_never_contacts_provider(self):
        with patch.object(probe, "api") as api:
            with self.assertRaises(ValueError):
                probe.probe(
                    "test-token", "https://example.invalid/collect", "system", "user"
                )
            api.assert_not_called()

    def test_excess_cloud_permission_fails_before_any_kubernetes_command(self):
        with (
            patch.object(
                probe,
                "api",
                side_effect=[
                    {},
                    {
                        "permissions": [
                            "container.clusters.get",
                            "container.nodePools.create",
                        ]
                    },
                ],
            ),
            patch.object(probe.subprocess, "run") as kubectl,
        ):
            with self.assertRaisesRegex(ValueError, "Google permissions"):
                self.run_probe()
            kubectl.assert_not_called()


if __name__ == "__main__":
    unittest.main()
