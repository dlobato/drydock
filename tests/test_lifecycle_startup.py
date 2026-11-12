"""Bounded startup through the CLI with controlled Kubernetes capacity and time."""

import json
import os
from unittest.mock import patch

from test_lifecycle import IDENTITY, alternate_files, make_bundle
from test_lifecycle_cli import LifecycleCliCase, ready_items

from drydock import flow, lifecycle


def pending_items():
    items = ready_items()
    pod = next(item for item in items if item["kind"] == "Pod")
    pod["status"] = {
        "phase": "Pending",
        "conditions": [
            {
                "type": "PodScheduled",
                "status": "False",
                "reason": "Unschedulable",
                "message": "private-provider-output",
            }
        ],
    }
    return items


class StartupTests(LifecycleCliCase):
    def setUp(self):
        super().setUp()
        self.instant = 1000
        for target in ("drydock.lifecycle.now", "drydock.flow.now"):
            timer = patch(target, side_effect=lambda: self.instant)
            timer.start()
            self.addCleanup(timer.stop)
        for mock in (
            patch.dict(os.environ, {"DRYDOCK_LAB_PASSWORD": "test-only"}),
            patch("drydock.flow.eapi", side_effect=self.eapi),
            patch("drydock.flow.time.sleep", side_effect=self.sleep),
        ):
            mock.start()
            self.addCleanup(mock.stop)

    def sleep(self, seconds):
        self.instant += seconds

    def eapi(self, host, password, commands):
        return [{"hostname": host["name"]}, {"version": "test"}]

    def create(self, *args):
        code, record = self.invoke(*self.create_args, *args)
        self.assertEqual(code, 0, record)
        return record

    def test_lifetime_default_and_boundaries_through_cli(self):
        for args, minutes in (
            ((), 30),
            (("--lifetime", "1"), 1),
            (("--lifetime", "60"), 60),
        ):
            with self.subTest(minutes=minutes):
                record = self.create(*args)
                self.assertEqual(record["accepted_at"], 1000)
                self.assertEqual(record["expires_at"], 1000 + minutes * 60)

    def test_invalid_lifetime_fails_before_ownership(self):
        for lifetime in ("0", "-1", "61", "240"):
            with self.subTest(lifetime=lifetime):
                code, result = self.invoke(*self.create_args, "--lifetime", lifetime)
                self.assertEqual(code, 1)
                self.assertIn("between 1 and 60 minutes", result["error"])
        self.assertFalse(self.backend.calls)
        self.assertFalse(self.backend.records)

    def test_deadline_is_accepted_once_and_clipped_to_expiry(self):
        for timeout, expected in ((20, 1020), (1200, 1060)):
            with self.subTest(timeout=timeout):
                record = self.create(
                    "--lifetime", "1", "--startup-timeout", str(timeout)
                )
                self.assertEqual(record["accepted_at"], 1000)
                self.assertEqual(record["startup_deadline"], expected)
                self.assertEqual(record["expires_at"], 1060)

    def test_invalid_startup_timeout_fails_before_ownership(self):
        for timeout in ("0", "-1"):
            code, result = self.invoke(*self.create_args, "--startup-timeout", timeout)
            self.assertEqual(code, 1)
            self.assertIn("positive", result["error"])
        with self.assertRaisesRegex(ValueError, "Startup timeout"):
            lifecycle.validate_request(make_bundle(self.directory), IDENTITY, 30, True)
        self.assertFalse(self.backend.calls)
        self.assertFalse(self.backend.records)

    def test_capacity_arrives_without_extending_deadlines(self):
        record = self.create("--startup-timeout", "20")
        self.assertEqual(record["expires_at"], 2800)
        lab = record["id"]
        self.items = pending_items()
        code, waiting = self.invoke("lab", "status", lab)
        self.assertEqual(code, 1)
        self.assertEqual(waiting["phase"], "waiting_for_capacity")
        self.assertEqual(waiting["scheduling"][0]["reason"], "Unschedulable")
        self.assertNotIn("private-provider-output", json.dumps(waiting))

        def capacity(seconds):
            self.sleep(seconds)
            self.items = None

        with patch("drydock.flow.time.sleep", side_effect=capacity):
            code, ready = self.invoke("lab", "wait", lab)
        self.assertEqual(code, 0, ready)
        self.assertEqual(ready["phase"], "ready")
        self.assertEqual(ready["record"]["ready_at"], 1010)
        self.instant = 1021
        code, repeated = self.invoke("lab", "wait", lab)
        self.assertEqual(code, 0, repeated)
        for key in ("accepted_at", "startup_deadline", "expires_at"):
            self.assertEqual(repeated["record"][key], record[key])
        self.assertEqual(repeated["record"]["ready_at"], 1010)
        self.assertNotIn("cleanup", repeated)

        self.instant = record["expires_at"]
        code, expired = self.invoke("lab", "wait", lab)
        self.assertEqual(code, 1)
        self.assertEqual(expired["phase"], "expired")
        self.assertTrue(expired["cleanup"]["deleted"])
        stored = lifecycle.lab_record(self.backend, lab)
        for key in ("accepted_at", "startup_deadline", "expires_at"):
            self.assertEqual(stored[key], record[key])

    def test_capacity_exhaustion_cleans_partial_lab_and_preserves_another(self):
        survivor = self.create()
        resources = list(self.backend.applied)
        record = self.create("--startup-timeout", "15")
        self.items = pending_items()
        code, result = self.invoke("lab", "wait", record["id"])
        self.assertEqual(code, 1)
        self.assertEqual(result["phase"], "startup_timeout")
        self.assertTrue(result["cleanup"]["deleted"])
        self.assertEqual(self.instant, 1015)
        self.assertEqual(self.backend.applied, resources)
        self.assertEqual(len(self.backend.namespaces), 1)
        self.assertEqual(
            lifecycle.lab_record(self.backend, survivor["id"])["state"], "running"
        )
        stored = lifecycle.lab_record(self.backend, record["id"])
        self.assertEqual(stored["state"], "deleted")
        self.assertEqual(stored["expires_at"], record["expires_at"])
        self.assertEqual(stored["startup_deadline"], 1015)
        self.assertNotIn("ready_at", stored)

    def test_cleanup_failure_remains_visible_and_cleaner_retries(self):
        record = self.create("--startup-timeout", "1")
        self.items = pending_items()
        self.backend.fail_delete = True

        def one_cleanup_attempt(action, *args):
            result = action()
            if result:
                return result
            raise TimeoutError

        with patch("drydock.flow.wait_for", side_effect=one_cleanup_attempt):
            code, result = self.invoke("lab", "wait", record["id"])
        self.assertEqual(code, 1)
        self.assertEqual(result["phase"], "startup_timeout")
        self.assertFalse(result["cleanup"]["deleted"])
        self.assertTrue(self.backend.namespaces)
        self.assertEqual(
            lifecycle.lab_record(self.backend, record["id"])["state"], "deleting"
        )
        self.backend.fail_delete = False
        self.assertTrue(lifecycle.reap(self.backend)[0]["deleted"])
        self.assertFalse(self.backend.namespaces)

    def test_late_authentication_cannot_report_ready(self):
        make_bundle(self.directory, files=alternate_files(1, mapping=False))
        for late in (1020, 1021):
            self.instant = 1000
            record = self.create("--startup-timeout", "20")

            def delayed(host, password, commands):
                self.instant = late
                return self.eapi(host, password, commands)

            with patch("drydock.flow.eapi", side_effect=delayed):
                code, result = self.invoke("lab", "wait", record["id"])
            self.assertEqual(code, 1)
            self.assertEqual(result["phase"], "startup_timeout")
            self.assertFalse(result["ready"])
            self.assertTrue(result["cleanup"]["deleted"])
            self.assertNotIn(
                "ready_at", lifecycle.lab_record(self.backend, record["id"])
            )

    def test_expiry_ends_wait_even_with_a_longer_requested_timeout(self):
        record = self.create("--lifetime", "1", "--startup-timeout", "300")
        self.items = pending_items()
        code, result = self.invoke("lab", "wait", record["id"])
        self.assertEqual(code, 1)
        self.assertEqual(result["phase"], "expired")
        self.assertEqual(self.instant, 1060)
        self.assertTrue(result["cleanup"]["deleted"])

    def test_late_allocation_stops_before_workload_creation(self):
        original = self.backend.kube

        def late_namespace(*args, data=None):
            result = original(*args, data=data)
            if data and json.loads(data)["kind"] == "Namespace":
                self.instant = 1020
            return result

        with patch.object(self.backend, "kube", side_effect=late_namespace):
            code, result = self.invoke(*self.create_args, "--startup-timeout", "20")
        self.assertEqual(code, 1)
        self.assertTrue(result["cleanup"]["deleted"])
        self.assertFalse(self.backend.applied)
        self.assertFalse(self.backend.namespaces)

    def test_deletion_during_authentication_cannot_be_overwritten(self):
        record = self.create()
        lab = record["id"]

        def deleting(host, password, commands):
            lifecycle.delete_lab(self.backend, lab)
            return self.eapi(host, password, commands)

        with patch("drydock.flow.eapi", side_effect=deleting):
            code, result = self.invoke("lab", "wait", lab)
        self.assertEqual(code, 1)
        self.assertFalse(result["ready"])
        self.assertTrue(result["cleanup"]["deleted"])
        stored = lifecycle.lab_record(self.backend, lab)
        self.assertEqual(stored["state"], "deleted")
        self.assertNotIn("ready_at", stored)

    def test_startup_and_management_failures_have_distinct_phases(self):
        record = self.create()
        self.items = []
        code, starting = self.invoke("lab", "status", record["id"])
        self.assertEqual(code, 1)
        self.assertEqual(starting["phase"], "starting")
        self.items = None
        with patch("drydock.flow.eapi", side_effect=OSError("private-provider-output")):
            code, failed = self.invoke("lab", "status", record["id"])
        self.assertEqual(code, 1)
        self.assertEqual(failed["phase"], "management_unavailable")
        self.assertNotIn("private-provider-output", json.dumps(failed))

    def test_cancellation_requests_cleanup(self):
        record = self.create()
        self.items = pending_items()
        with patch("drydock.flow.time.sleep", side_effect=flow.Canceled):
            code, result = self.invoke("lab", "wait", record["id"])
        self.assertEqual(code, 1)
        self.assertEqual(result["error"], "Canceled")
        self.assertTrue(result["cleanup"]["deleted"])
        self.assertFalse(self.backend.namespaces)
