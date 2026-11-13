"""Adversarial requests exercise the same policy used by Kubernetes admission."""

import json
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import Mock, patch

import yaml
from test_lifecycle import (
    ENV,
    IDENTITY,
    IMAGE,
    LAB,
    FakeEnvironment,
    alternate_files,
    make_bundle,
)

from drydock.access import access_objects
from drydock.admission import Boundary, reader_binding, validate_runtime_topology
from drydock.core import ALLOCATION_LABEL, ENV_LABEL, LAB_LABEL, UserError
from drydock.lifecycle import create_lab, lab_manifests, lab_record, object_meta

USER = "workflow-test"


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.backend = FakeEnvironment()
        self.bundle = make_bundle(temporary.name)
        self.record = create_lab(self.backend, self.bundle, IDENTITY, lab=LAB)
        self.record["state"] = "creating"
        self.namespace = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": ENV.name + "-" + LAB,
                "labels": {
                    ENV_LABEL: ENV.name,
                    LAB_LABEL: LAB,
                    ALLOCATION_LABEL: self.record["allocation_id"],
                    "pod-security.kubernetes.io/enforce": "privileged",
                    "kubernetes.io/metadata.name": ENV.name + "-" + LAB,
                },
            },
        }
        self.env = Mock(name=ENV.name, namespace=ENV.namespace)
        self.env.name = ENV.name
        self.env.namespace = ENV.namespace
        self.env.kube.side_effect = lambda *args, **kwargs: json.dumps(self.namespace)
        self.boundary = Boundary(self.env, USER, [IMAGE])
        self.env.objects.side_effect = self.objects
        self.manifests = lab_manifests(ENV, self.bundle, LAB)

    def objects(self, kind, namespace=None, labels=None):
        if kind == "configmaps":
            return [
                {
                    "metadata": {
                        **object_meta(ENV, LAB, ENV.namespace, LAB),
                        "resourceVersion": "1",
                    },
                    "data": {"record": json.dumps(self.record)},
                }
            ]
        if kind == "namespaces":
            return [self.namespace]
        if kind == "rolebindings":
            return [reader_binding(ENV, LAB, USER)]
        raise AssertionError(kind)

    def request(self, obj, operation="CREATE", old=None, user=USER):
        return {
            "uid": "test",
            "userInfo": {"username": user},
            "resource": {
                "group": "c9s.run" if obj["kind"] == "Topology" else "",
                "resource": {
                    "Namespace": "namespaces",
                    "Secret": "secrets",
                    "ConfigMap": "configmaps",
                    "Topology": "topologies",
                }[obj["kind"]],
            },
            "namespace": obj["metadata"].get("namespace", ""),
            "operation": operation,
            "object": deepcopy(obj),
            "oldObject": deepcopy(old),
        }

    def test_generated_payloads_and_namespace_pass(self):
        self.boundary.validate(self.request(self.namespace))
        for obj in self.manifests:
            self.boundary.validate(self.request(obj))

    def test_alternate_names_and_split_payloads_use_existing_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = make_bundle(
                directory, files=alternate_files(12, padding="x" * 100_000)
            )
        topology = lab_manifests(ENV, bundle, LAB)[-1]
        validate_runtime_topology(topology, [IMAGE], LAB)

    def test_unsafe_yaml_and_runtime_overrides_are_denied(self):
        for field, value in (
            ("kind", "linux"),
            ("exec", ["id"]),
            ("binds", ["/etc:/host:rw"]),
            ("image", IMAGE),
            ("startup-config", "/etc/passwd"),
            ("ports", ["22/tcp"]),
            ("network-mode", "host"),
            ("privileged", True),
        ):
            with self.subTest(field=field):
                obj = deepcopy(self.manifests[-1])
                topology = yaml.safe_load(obj["spec"]["definition"]["containerlab"])
                topology["topology"]["nodes"]["leaf1"][field] = value
                obj["spec"]["definition"]["containerlab"] = yaml.safe_dump(topology)
                with self.assertRaises((UserError, ValueError)):
                    self.boundary.validate(self.request(obj))
        for mutate in (
            lambda obj: obj["spec"]["expose"].update(exposeType="LoadBalancer"),
            lambda obj: obj["spec"]["deployment"].update(filesFromURL={"leaf1": []}),
            lambda obj: obj["spec"]["deployment"]["filesFromSecret"]["leaf1"][0].update(
                secretName="registry-credentials"
            ),
            lambda obj: obj["spec"]["deployment"]["filesFromSecret"]["leaf1"][0].update(
                mode="execute"
            ),
            lambda obj: obj["spec"].update(imagePull={"pullSecrets": ["other-secret"]}),
        ):
            obj = deepcopy(self.manifests[-1])
            mutate(obj)
            with self.assertRaises(UserError):
                self.boundary.validate(self.request(obj))

    def test_unapproved_image_and_malformed_yaml_are_denied(self):
        obj = deepcopy(self.manifests[-1])
        for content in (
            "[",
            "null",
            "!!python/object/apply:os.system [id]",
            "topology: {}",
        ):
            obj["spec"]["definition"]["containerlab"] = content
            with self.assertRaises(Exception):
                self.boundary.validate(self.request(obj))
        self.boundary.images = []
        with self.assertRaises(UserError):
            self.boundary.validate(self.request(self.manifests[-1]))

    def test_outside_namespace_forged_labels_and_payload_metadata_are_denied(self):
        for mutate in (
            lambda obj: obj["metadata"].update(namespace="unrelated"),
            lambda obj: obj["metadata"].update(name="registry-credentials"),
            lambda obj: obj["metadata"]["labels"].update({ENV_LABEL: "other"}),
            lambda obj: obj["metadata"].update(annotations={"payload": "untrusted"}),
            lambda obj: obj.update(type="kubernetes.io/dockerconfigjson"),
        ):
            obj = deepcopy(self.manifests[0])
            mutate(obj)
            with self.assertRaises(UserError):
                self.boundary.validate(self.request(obj))
        self.namespace["metadata"]["labels"][ALLOCATION_LABEL] = "different"
        with self.assertRaises(UserError):
            self.boundary.validate(self.request(self.manifests[0]))

    def test_expiry_and_cleanup_prevent_allocation(self):
        for state in ("deleting", "deleted", "running"):
            self.record["state"] = state
            with self.assertRaises(UserError):
                self.boundary.validate(self.request(self.manifests[0]))
        self.record["state"] = "creating"
        with patch("drydock.admission.now", return_value=self.record["expires_at"]):
            with self.assertRaises(UserError):
                self.boundary.validate(self.request(self.manifests[0]))

    def test_cleaner_can_delete_owned_namespace_but_cannot_allocate(self):
        cleaner = "system:serviceaccount:" + ENV.namespace + ":cleaner"
        with self.assertRaises(UserError):
            self.boundary.validate(
                self.request(self.namespace, "DELETE", self.namespace, cleaner)
            )
        self.record["state"] = "deleting"
        self.boundary.validate(
            self.request(self.namespace, "DELETE", self.namespace, cleaner)
        )
        with self.assertRaises(UserError):
            self.boundary.validate(self.request(self.namespace, user=cleaner))
        outside = deepcopy(self.namespace)
        outside["metadata"]["name"] = "unrelated"
        with self.assertRaises(UserError):
            self.boundary.validate(self.request(outside, "DELETE", outside, cleaner))

    def test_ownership_expiry_and_identity_cannot_be_replaced_or_revived(self):
        old = deepcopy(self.backend.records[LAB])
        record = lab_record(self.backend, LAB)
        for field, value in (
            ("expires_at", record["expires_at"] + 60),
            ("allocation_id", "0" * 32),
            ("runtime", {"ceos_image": IMAGE + "x"}),
        ):
            obj = deepcopy(old)
            changed = deepcopy(record)
            changed[field] = value
            obj["data"]["record"] = json.dumps(changed)
            with self.assertRaises(UserError):
                self.boundary.validate(self.request(obj, "UPDATE", old))
        previous = json.loads(old["data"]["record"])
        previous["state"] = "deleted"
        old["data"]["record"] = json.dumps(previous)
        changed = deepcopy(old)
        previous["state"] = "running"
        changed["data"]["record"] = json.dumps(previous)
        with self.assertRaises(UserError):
            self.boundary.validate(self.request(changed, "UPDATE", old))

    def test_reader_reconciler_does_not_adopt_wrong_ownership_or_binding(self):
        self.assertTrue(self.boundary.reader_ready(LAB))
        wrong = reader_binding(ENV, LAB, "someone-else")
        self.env.objects.side_effect = lambda kind, *args, **kwargs: (
            [wrong] if kind == "rolebindings" else self.objects(kind, *args, **kwargs)
        )
        with self.assertRaises(UserError):
            self.boundary.reader_ready(LAB)
        with patch("builtins.print"):
            self.boundary.bind_readers()
        self.env.kube.assert_not_called()

    def test_wrong_namespace_ownership_does_not_block_another_lab(self):
        other_lab = "lab-eeeeeeeeeeee"
        other_namespace = deepcopy(self.namespace)
        other_namespace["metadata"]["name"] = ENV.name + "-" + other_lab
        other_namespace["metadata"]["labels"][LAB_LABEL] = other_lab
        self.namespace["metadata"]["labels"][ALLOCATION_LABEL] = "wrong"

        def objects(kind, namespace=None, labels=None):
            if kind == "namespaces":
                return [self.namespace, other_namespace]
            if kind == "rolebindings":
                return []
            records = self.objects(kind, namespace, labels)
            if other_lab in labels:
                record = json.loads(records[0]["data"]["record"])
                record["id"] = other_lab
                records[0]["data"]["record"] = json.dumps(record)
            return records

        self.env.objects.side_effect = objects
        with patch("builtins.print"):
            self.boundary.bind_readers()
        self.env.kube.assert_called_once()
        created = json.loads(self.env.kube.call_args.kwargs["data"])
        self.assertEqual(created["metadata"]["namespace"], ENV.name + "-" + other_lab)


class AccessManifestTests(unittest.TestCase):
    def test_no_workflow_secret_reads_rbac_changes_or_unrelated_workload_reads(self):
        objects = list(
            access_objects(
                ENV, IMAGE, USER, [IMAGE], b"-----BEGIN CERTIFICATE-----\ntest"
            )
        )
        caller = next(
            obj
            for obj in objects
            if obj["kind"] == "ClusterRole"
            and obj["metadata"]["name"] == ENV.name + "-lifecycle"
        )
        allowed = {
            (resource, verb)
            for rule in caller["rules"]
            for resource in rule["resources"]
            for verb in rule["verbs"]
        }
        for operation in (
            ("secrets", "get"),
            ("secrets", "list"),
            ("pods", "get"),
            ("pods", "create"),
            ("rolebindings", "create"),
            ("clusterroles", "bind"),
            ("serviceaccounts/token", "create"),
        ):
            self.assertNotIn(operation, allowed)
        self.assertIn(("secrets", "create"), allowed)
        self.assertIn(("topologies", "create"), allowed)
        webhook = next(
            obj for obj in objects if obj["kind"] == "ValidatingWebhookConfiguration"
        )["webhooks"][0]
        self.assertEqual(webhook["failurePolicy"], "Fail")
        self.assertEqual(webhook["sideEffects"], "None")
        self.assertNotIn("namespaceSelector", webhook)
        self.assertIn(USER, webhook["matchConditions"][0]["expression"])


if __name__ == "__main__":
    unittest.main()
