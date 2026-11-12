"""Authenticated inventory for submitted topologies and changing runtime endpoints."""

import json
import os
from copy import deepcopy
from unittest.mock import patch
from urllib.error import HTTPError

from test_lifecycle import alternate_files, make_bundle
from test_lifecycle_cli import LifecycleCliCase, ready_items

from drydock import lifecycle


class ReadinessTests(LifecycleCliCase):
    def setUp(self):
        super().setUp()
        make_bundle(self.directory, files=alternate_files())
        code, self.record = self.invoke(*self.create_args)
        self.assertEqual(code, 0)
        self.lab = self.record["id"]
        self.names = self.record["switches"]
        self.items = ready_items(self.names, self.record["link_count"])
        for mock in (
            patch.dict(os.environ, {"DRYDOCK_LAB_PASSWORD": "test-password"}),
            patch("drydock.flow.eapi", side_effect=self.eapi),
        ):
            mock.start()
            self.addCleanup(mock.stop)

    def eapi(self, host, password, commands):
        self.assertEqual(password, "test-password")
        return [{"hostname": host["name"]}, {"version": "test-eos"}]

    def test_inventory_authenticates_every_submitted_switch(self):
        with patch("drydock.flow.eapi", side_effect=self.eapi) as api:
            code, result = self.invoke("lab", "inventory", self.lab)
        self.assertEqual(code, 0, result)
        self.assertTrue(result["ready"])
        self.assertEqual(
            [call.args[0]["name"] for call in api.call_args_list], self.names
        )
        self.assertEqual(set(result["eos_versions"]), set(self.names))
        self.assertEqual(
            result["record"]["bundle_digest"], self.record["bundle_digest"]
        )
        for host in result["inventory"]:
            self.assertEqual(host["namespace"], self.backend.name + "-" + self.lab)
            self.assertEqual(host["transport"], "private Pod-IP HTTPS")
            self.assertEqual(host["port"], 443)
            self.assertTrue(host["pod"] and host["pod_uid"])
        self.assertNotIn("test-password", json.dumps(result))

    def test_every_requested_resource_gates_authentication(self):
        original = deepcopy(self.items)
        variants = []
        for kind in ("Node", "Link", "Pod", "Service"):
            items = deepcopy(original)
            items.remove(next(item for item in items if item["kind"] == kind))
            variants.append(("missing " + kind, items))
        items = deepcopy(original)
        link = next(item for item in items if item["kind"] == "Link")
        link["status"]["conditions"][0]["status"] = "False"
        variants.append(("unaccepted link", items))
        items = deepcopy(original)
        node = next(item for item in items if item["kind"] == "Node")
        node["metadata"]["generation"] = 2
        variants.append(("stale node plan", items))
        items = deepcopy(original)
        pods = [item for item in items if item["kind"] == "Pod"]
        items[items.index(pods[-1])] = deepcopy(pods[0])
        variants.append(("duplicate Pod replaces missing switch", items))
        items = deepcopy(original)
        items.append(deepcopy(pods[0]))
        variants.append(("additional duplicate Pod", items))
        for name, items in variants:
            with self.subTest(name=name), patch("drydock.flow.eapi") as api:
                self.items = items
                code, result = self.invoke("lab", "inventory", self.lab)
                self.assertEqual(code, 1)
                self.assertFalse(result["ready"])
                self.assertEqual(result["phase"], "starting")
                self.assertFalse(result["inventory"])
                api.assert_not_called()

    def test_one_failed_switch_prevents_authenticated_inventory_success(self):
        for failure in ("unreachable", "credentials", "hostname"):

            def reject(host, password, commands):
                if host["name"] == self.names[-1]:
                    if failure == "unreachable":
                        raise OSError("private-response-test-password")
                    if failure == "credentials":
                        raise HTTPError(
                            "https://private", 401, "test-password", {}, None
                        )
                    return [{"hostname": "another-switch"}, {"version": "test"}]
                return self.eapi(host, password, commands)

            with (
                self.subTest(failure=failure),
                patch("drydock.flow.eapi", side_effect=reject),
            ):
                code, result = self.invoke("lab", "inventory", self.lab)
            self.assertEqual(code, 1)
            self.assertFalse(result["ready"])
            self.assertEqual(result["phase"], "management_unavailable")
            self.assertFalse(result["eos_versions"])
            self.assertNotIn("test-password", json.dumps(result))
            self.assertNotIn("ready_at", lifecycle.lab_record(self.backend, self.lab))
        code, recovered = self.invoke("lab", "inventory", self.lab)
        self.assertEqual(code, 0, recovered)

    def test_replacement_during_authentication_requires_a_fresh_attempt(self):
        pod = next(item for item in self.items if item["kind"] == "Pod")

        def replace(host, password, commands):
            pod["metadata"].update(name="replacement-pod", uid="replacement-uid")
            pod["status"]["podIP"] = "10.251.2.42"
            return self.eapi(host, password, commands)

        with patch("drydock.flow.eapi", side_effect=replace):
            code, result = self.invoke("lab", "inventory", self.lab)
        self.assertEqual(code, 1)
        self.assertIn(
            "switch endpoints changed during authentication", result["errors"]
        )
        self.assertFalse(result["inventory"])
        self.assertFalse(result["eos_versions"])
        self.assertNotIn("ready_at", lifecycle.lab_record(self.backend, self.lab))
        with patch("drydock.flow.eapi", side_effect=self.eapi) as api:
            code, current = self.invoke("lab", "inventory", self.lab)
        self.assertEqual(code, 0, current)
        self.assertEqual(api.call_args_list[0].args[0]["host"], "10.251.2.42")
        host = current["inventory"][0]
        self.assertEqual(host["pod"], "replacement-pod")
        self.assertEqual(host["pod_uid"], "replacement-uid")
        self.assertEqual(host["host"], "10.251.2.42")

    def test_link_loss_during_authentication_prevents_readiness(self):
        link = next(item for item in self.items if item["kind"] == "Link")

        def lose_link(host, password, commands):
            link["status"]["conditions"][0]["status"] = "False"
            return self.eapi(host, password, commands)

        with patch("drydock.flow.eapi", side_effect=lose_link):
            code, result = self.invoke("lab", "inventory", self.lab)
        self.assertEqual(code, 1)
        self.assertFalse(result["ready"])
        self.assertEqual(result["phase"], "starting")
        self.assertNotIn("ready_at", lifecycle.lab_record(self.backend, self.lab))

    def test_deletion_after_prior_readiness_prevents_inventory_success(self):
        code, result = self.invoke("lab", "status", self.lab)
        self.assertEqual(code, 0, result)

        def deleting(host, password, commands):
            record = lifecycle.lab_record(self.backend, self.lab)
            record["state"] = "deleting"
            lifecycle.write_record(self.backend, record)
            return self.eapi(host, password, commands)

        with patch("drydock.flow.eapi", side_effect=deleting):
            code, result = self.invoke("lab", "inventory", self.lab)
        self.assertEqual(code, 1)
        self.assertFalse(result["ready"])
        self.assertEqual(result["phase"], "deleting")
        self.assertEqual(
            lifecycle.lab_record(self.backend, self.lab)["state"], "deleting"
        )

    def test_inventory_requires_a_password(self):
        with (
            patch.dict(os.environ, {"DRYDOCK_LAB_PASSWORD": ""}),
            patch("drydock.flow.eapi") as api,
        ):
            code, result = self.invoke("lab", "inventory", self.lab)
        self.assertEqual(code, 1)
        self.assertIn("DRYDOCK_LAB_PASSWORD", result["error"])
        api.assert_not_called()
