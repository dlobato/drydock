"""Portable cleaner deployment and recovery through controlled Kubernetes responses."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import yaml
from test_lifecycle import ENV, IMAGE
from test_lifecycle_cli import LifecycleCliCase

from drydock import lifecycle
from drydock.cleaner import cleaner_objects
from drydock.core import Environment, UserError


class CleanerManifestTests(unittest.TestCase):
    def test_cleaner_uses_mounted_service_account_without_token_arguments(self):
        cleaner = Environment(ENV.name, "/environment/kubeconfig", "cleaner")
        command = cleaner.kube_command("get", "configmaps")
        self.assertEqual(
            command[command.index("--kubeconfig") + 1], "/environment/kubeconfig"
        )
        configmap = next(
            o
            for o in cleaner_objects(ENV, IMAGE)
            if o["kind"] == "ConfigMap" and o["metadata"]["name"] == "environment"
        )
        config = yaml.safe_load(configmap["data"]["kubeconfig"])
        self.assertEqual(
            config["clusters"][0]["cluster"],
            {
                "server": "https://kubernetes.default.svc",
                "certificate-authority": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
            },
        )
        self.assertEqual(
            config["users"][0]["user"],
            {"tokenFile": "/var/run/secrets/kubernetes.io/serviceaccount/token"},
        )
        self.assertNotIn("--token", command)
        self.assertEqual(
            yaml.safe_load(configmap["data"]["environment.yml"]), asdict(cleaner)
        )
        objects = list(cleaner_objects(ENV, IMAGE))
        account = next(obj for obj in objects if obj["kind"] == "ServiceAccount")
        self.assertNotIn("annotations", account["metadata"])
        cron = next(obj for obj in objects if obj["kind"] == "CronJob")
        self.assertEqual(cron["spec"]["schedule"], "*/5 * * * *")
        self.assertEqual(cron["spec"]["concurrencyPolicy"], "Forbid")
        self.assertIn(IMAGE, str(cron))
        rules = next(obj for obj in objects if obj["kind"] == "ClusterRole")["rules"]
        self.assertEqual(
            rules,
            [
                {
                    "apiGroups": [""],
                    "resources": ["namespaces"],
                    "verbs": ["get", "list", "delete"],
                }
            ],
        )

    def test_portable_manifest_cli_and_invalid_image(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = Path(directory) / "environment.yml"
            environment.write_text(yaml.safe_dump(asdict(ENV)))
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "drydock.cleaner",
                    "--environment",
                    str(environment),
                    "--image",
                    IMAGE,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        manifest = json.loads(result.stdout)
        self.assertEqual(manifest["kind"], "List")
        self.assertEqual(manifest["items"], list(cleaner_objects(ENV, IMAGE)))
        cron = next(obj for obj in manifest["items"] if obj["kind"] == "CronJob")
        job = cron["spec"]["jobTemplate"]["spec"]
        self.assertLess(job["activeDeadlineSeconds"], 300)
        self.assertEqual(job["backoffLimit"], 0)
        pod = job["template"]["spec"]
        self.assertNotIn("nodeSelector", pod)
        self.assertEqual(pod["containers"][0]["command"][-1], "reap")
        self.assertNotIn("gcloud", result.stdout)
        with self.assertRaises(UserError):
            list(cleaner_objects(ENV, "cleaner:latest"))


class CleanerRecoveryTests(LifecycleCliCase):
    def test_five_minute_retries_continue_overdue_and_preserve_another_lab(self):
        with patch("drydock.lifecycle.now", return_value=1000):
            code, expired = self.invoke(*self.create_args, "--lifetime", "1")
            self.assertEqual(code, 0)
            code, active = self.invoke(*self.create_args, "--lifetime", "60")
            self.assertEqual(code, 0)
        other_record = json.loads(json.dumps(self.backend.records[active["id"]]))
        namespace = ENV.name + "-" + active["id"]
        other_resources = [
            obj
            for obj in self.backend.applied
            if obj["metadata"]["namespace"] == namespace
        ]
        self.backend.fail_delete = True
        with patch.dict(os.environ, {"DRYDOCK_LAB_PASSWORD": ""}):
            for sweep in range(9):
                observed = expired["expires_at"] + 300 * sweep
                with patch("drydock.lifecycle.now", return_value=observed):
                    code, result = self.invoke("reap")
                self.assertEqual(code, 1)
                self.assertEqual(len(result["cleanup"]), 1)
                outcome = result["cleanup"][0]
                self.assertFalse(outcome["deleted"])
                self.assertEqual(outcome["observed_at"], observed)
                stored = lifecycle.lab_record(self.backend, expired["id"])
                self.assertEqual(stored["state"], "deleting")
                self.assertEqual(stored["expires_at"], expired["expires_at"])
                self.assertEqual(stored["cleanup_started_at"], expired["expires_at"])
                self.assertEqual(stored["overdue"], sweep > 6)
            self.backend.fail_delete = False
            with patch("drydock.lifecycle.now", return_value=observed + 300):
                code, result = self.invoke("reap")
        self.assertEqual(code, 0)
        self.assertTrue(result["cleanup"][0]["deleted"])
        stored = lifecycle.lab_record(self.backend, expired["id"])
        self.assertFalse(stored["overdue"])
        self.assertEqual(stored["cleanup_started_at"], expired["expires_at"])
        self.assertEqual(self.backend.records[active["id"]], other_record)
        self.assertEqual(self.backend.applied, other_resources)

    def test_interrupted_deletion_is_recovered_before_expiry(self):
        for accepted in (False, True):
            with self.subTest(request_accepted=accepted):
                code, record = self.invoke(*self.create_args)
                self.assertEqual(code, 0)
                original = self.backend.kube

                def interrupt(*args, data=None):
                    if args[0] == "delete":
                        if accepted:
                            original(*args, data=data)
                        raise KeyboardInterrupt
                    return original(*args, data=data)

                with patch.object(self.backend, "kube", side_effect=interrupt):
                    code, result = self.invoke("lab", "delete", record["id"])
                self.assertEqual(code, 1)
                self.assertEqual(result["error"], "KeyboardInterrupt")
                self.assertEqual(
                    lifecycle.lab_record(self.backend, record["id"])["state"],
                    "deleting",
                )
                code, result = self.invoke("reap")
                self.assertEqual(code, 0)
                self.assertTrue(result["cleanup"][0]["deleted"])
                self.assertFalse(self.backend.namespaces)
                self.assertFalse(self.backend.applied)

    def test_finalizers_keep_cleanup_incomplete_until_namespace_disappears(self):
        code, record = self.invoke(*self.create_args)
        self.assertEqual(code, 0)
        namespace = self.backend.namespaces[0]
        namespace["spec"] = {"finalizers": ["kubernetes"]}
        original = self.backend.kube

        def terminating(*args, data=None):
            if args[0] == "delete":
                namespace["metadata"]["deletionTimestamp"] = "2026-11-13T10:00:00Z"
                return "{}"
            return original(*args, data=data)

        with (
            patch("drydock.lifecycle.now", return_value=record["expires_at"] + 1801),
            patch.object(self.backend, "kube", side_effect=terminating),
        ):
            code, result = self.invoke("reap")
        self.assertEqual(code, 1)
        self.assertTrue(result["cleanup"][0]["namespace_remaining"])
        self.assertTrue(lifecycle.lab_record(self.backend, record["id"])["overdue"])
        self.assertEqual(namespace["spec"]["finalizers"], ["kubernetes"])
        self.assertTrue(self.backend.applied)
        code, result = self.invoke("reap")
        self.assertEqual(code, 0)
        self.assertTrue(result["cleanup"][0]["deleted"])
        self.assertFalse(self.backend.applied)

    def test_failed_ownership_does_not_block_cleanup_of_another_lab(self):
        code, foreign = self.invoke(*self.create_args)
        self.assertEqual(code, 0)
        self.backend.namespaces[0]["metadata"]["labels"] = {"unrelated": "true"}
        preserved = json.loads(json.dumps(self.backend.namespaces[0]))
        code, owned = self.invoke(*self.create_args)
        self.assertEqual(code, 0)
        with patch("drydock.lifecycle.now", return_value=owned["expires_at"] + 1801):
            code, result = self.invoke("reap")
        self.assertEqual(code, 1)
        outcomes = {item["lab"]: item for item in result["cleanup"]}
        self.assertFalse(outcomes[foreign["id"]]["deleted"])
        self.assertTrue(outcomes[foreign["id"]]["overdue"])
        self.assertTrue(outcomes[owned["id"]]["deleted"])
        self.assertEqual(self.backend.namespaces, [preserved])
