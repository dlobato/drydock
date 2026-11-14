"""Inspect the final upload directory and exercise failed upload cleanup."""

import hashlib
import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from test_workflows import workflow

from examples.github import pipeline, reports


class ReportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.state = Path(temporary.name) / "state"
        self.state.mkdir()
        self.secret = "synthetic-private-canary"
        self.row = {
            "name": "leaf1",
            "test": "VerifyMlagStatus",
            "description": self.secret,
            "result": "success",
            "messages": [self.secret],
            "custom_field": self.secret,
        }
        self.save(
            "state.json",
            {
                "provenance": {
                    "repository": "dlobato/drydock",
                    "commit": "c" * 40,
                    "run": "42",
                    "attempt": "2",
                },
                "trusted_commit": "d" * 40,
                "image": "toolchain@sha256:" + "a" * 64,
                "ceos_image": "ceos@sha256:" + "b" * 64,
                "bundle_digest": "e" * 64,
                "stage": "prepared",
            },
        )
        (self.state / "lab.env").write_text(
            f"DRYDOCK_LAB_PASSWORD={self.secret}\nDRYDOCK_LAB_PASSWORD_HASH=$6$private-hash\n"
        )
        self.save(
            "reports/run.json",
            {"passed": True, "stage": "test", "cleanup": {"deleted": False}},
        )
        self.save("reports/tests.json", {"passed": True})
        self.save("reports/anta.json", [self.row])
        self.save("validated/expected.json", [{**self.row, "count": 1}])
        self.save(
            "validated/runtime.json",
            {
                "python": "3.13.9",
                "pyavd": "6.5.0",
                "anta": "1.10.0",
                "credential_source": self.secret,
            },
        )
        self.save(
            "lifecycle/allocation.json",
            {"lab": "lab-123456789abc", "allocation_id": self.secret},
        )
        self.save(
            "lifecycle/inventory.json",
            {
                "ready": True,
                "eos_versions": {"leaf1": "4.36.1F"},
                "record": {"accepted_at": 1, "expires_at": 1801, "secret": self.secret},
            },
        )
        self.save("cleanup-result.json", {"deleted": True, "extra": self.secret})
        self.save(
            "validated/anta/avd_catalogs/leaf1.json",
            {
                "anta.tests.mlag": [
                    {
                        "VerifyMlagStatus": {
                            "result_overwrite": {"description": self.secret},
                            "password": self.secret,
                        }
                    }
                ],
                "anta.tests.routing.bgp": [
                    {
                        "VerifyBGPPeerSession": {
                            "bgp_peers": [
                                {"peer_address": "10.0.0.1", "vrf": "default"}
                            ]
                        }
                    }
                ],
                "credential_source": self.secret,
            },
        )
        for name in (
            "reports/startup.cfg",
            "reports/intended/structured_configs/leaf1.yml",
            "reports/anta.log",
            "google.json",
        ):
            path = self.state / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.secret)

    def save(self, name, value):
        pipeline.save(self.state / name, value)

    def test_final_artifacts_exclude_private_files_and_free_text_but_retain_provenance(
        self,
    ):
        output = reports.collect(self.state)
        files = {
            str(p.relative_to(output)): p.read_bytes()
            for p in output.rglob("*")
            if p.is_file()
        }
        self.assertEqual(
            set(files),
            {
                "run.json",
                "diagnostics.json",
                "anta.json",
                "anta.xml",
                "catalogs/leaf1.json",
                "manifest.json",
            },
        )
        for content in files.values():
            for forbidden in (
                self.secret,
                "$6$",
                "credential_source",
                "startup",
                "allocation_id",
            ):
                self.assertNotIn(forbidden.encode(), content)
        run = json.loads(files["run.json"])
        self.assertTrue(run["passed"])
        self.assertEqual(run["provenance"]["commit"], "c" * 40)
        self.assertEqual(run["provenance"]["attempt"], "2")
        self.assertEqual(run["trusted_commit"], "d" * 40)
        self.assertEqual(run["bundle_digest"], "e" * 64)
        self.assertEqual(run["lab"], "lab-123456789abc")
        self.assertEqual(run["runtime"]["anta"], "1.10.0")
        self.assertEqual(run["runtime"]["eos"], {"leaf1": "4.36.1F"})
        self.assertTrue(run["cleanup"]["deleted"])
        self.assertFalse(
            json.loads(files["diagnostics.json"])["initial_cleanup_deleted"]
        )
        self.assertIn(b"10.0.0.1", files["catalogs/leaf1.json"])
        manifest = json.loads(files["manifest.json"])
        self.assertEqual(
            manifest,
            {
                name: hashlib.sha256(content).hexdigest()
                for name, content in files.items()
                if name != "manifest.json"
            },
        )

    def test_missing_duplicate_skipped_and_errored_results_still_fail_safe_reports(
        self,
    ):
        for rows in (
            [],
            [self.row, self.row],
            [{**self.row, "result": "skipped"}],
            [{**self.row, "result": "error"}],
            [{**self.row, "description": "different"}],
        ):
            with self.subTest(rows=rows):
                self.save("reports/anta.json", rows)
                output = reports.collect(self.state)
                self.assertFalse(
                    json.loads((output / "run.json").read_text())["passed"]
                )
                self.assertGreater(
                    int(ET.parse(output / "anta.xml").getroot().get("failures")), 0
                )

    def test_build_failure_retains_only_safe_available_diagnostics_without_network_success(
        self,
    ):
        shutil.rmtree(self.state / "reports")
        shutil.rmtree(self.state / "validated")
        shutil.rmtree(self.state / "lifecycle")
        self.save(
            "cleanup-result.json", {"deleted": True, "allocation_attempted": False}
        )
        self.save(
            "state.json",
            {
                **json.loads((self.state / "state.json").read_text()),
                "stage": "build",
                "prepare_error": "RuntimeError",
            },
        )
        output = reports.collect(self.state)
        run = json.loads((output / "run.json").read_text())
        self.assertFalse(run["passed"])
        self.assertEqual(run["stage"], "build")
        self.assertEqual(run["prepare_error"], "RuntimeError")
        self.assertIsNone(run["lab"])
        self.assertFalse(run["cleanup"]["allocation_attempted"])

    def test_sensitive_or_linked_input_removes_previous_upload_directory(self):
        reports.collect(self.state)
        self.save(
            "state.json",
            {
                **json.loads((self.state / "state.json").read_text()),
                "trusted_commit": self.secret,
            },
        )
        with self.assertRaisesRegex(ValueError, "Sensitive"):
            reports.collect(self.state)
        self.assertFalse((self.state / "public").exists())
        (self.state / "reports/anta.json").unlink()
        (self.state / "reports/anta.json").symlink_to(self.state / "google.json")
        with self.assertRaisesRegex(ValueError, "regular"):
            reports.collect(self.state)

    def test_upload_failure_follows_real_deletion_and_private_files_are_still_removed(
        self,
    ):
        steps = workflow("pre-deployment.yml")["jobs"]["gke-lab"]["steps"]
        outcomes = []
        self.save("lifecycle/cleanup.json", {"deleted": True})
        with patch.object(pipeline, "container") as container:
            for step in steps:
                try:
                    if "pipeline cleanup" in step.get("run", ""):
                        self.assertIn("always()", step["if"])
                        self.assertTrue(pipeline.cleanup(self.state)["deleted"])
                        outcomes.append("deleted")
                    elif "pipeline collect" in step.get("run", ""):
                        reports.collect(self.state)
                    elif step.get("uses", "").startswith("actions/upload-artifact@"):
                        self.assertEqual(outcomes, ["deleted"])
                        raise OSError("controlled upload failure")
                    elif step.get("run", "").startswith("rm -rf"):
                        self.assertIn("always()", step["if"])
                        shutil.rmtree(self.state)
                except OSError:
                    outcomes.append("upload_failed")
            container.assert_called_once()
        self.assertEqual(outcomes, ["deleted", "upload_failed"])
        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()
