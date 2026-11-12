"""Ownership and orchestration tests for the manual demo environment."""

import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import yaml
from test_lifecycle import IMAGE

from drydock.core import Environment as LifecycleEnvironment
from drydock.core import save
from examples.demo import gke as cloud
from examples.demo.gke import GKEEnvironment as Environment

ENV = Environment(
    "demo-project",
    "europe-west1-b",
    "drydock-demo",
    "1.36.4-gke.2046003",
    "0.11.0",
    IMAGE,
)


def inventory():
    return {
        key: []
        for key in (
            "clusters",
            "networks",
            "subnets",
            "accounts",
            "roles",
            "instances",
            "disks",
            "firewall-rules",
            "routes",
            "addresses",
            "forwarding-rules",
            "instance-groups",
            "instance-templates",
            "bindings",
            "operations",
        )
    }


class InfrastructureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name)
        self.directory = directory
        self.patch_directory = patch.object(
            Environment, "directory", new=property(lambda _: directory)
        )
        self.patch_directory.start()
        self.addCleanup(self.patch_directory.stop)
        save(
            directory / "ownership.json", {"environment": asdict(ENV), "state": "ready"}
        )

    def test_cleaner_uses_mounted_service_account_without_token_arguments(self):
        cleaner = LifecycleEnvironment(ENV.name, "/environment/kubeconfig", "cleaner")
        command = cleaner.kube_command("get", "configmaps")
        self.assertEqual(
            command[command.index("--kubeconfig") + 1], "/environment/kubeconfig"
        )
        configmap = next(
            o
            for o in cloud.cleaner_objects(ENV)
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
        objects = list(cloud.cleaner_objects(ENV))
        account = next(obj for obj in objects if obj["kind"] == "ServiceAccount")
        self.assertNotIn("annotations", account["metadata"])
        cron = next(obj for obj in objects if obj["kind"] == "CronJob")
        self.assertEqual(cron["spec"]["schedule"], "*/5 * * * *")
        self.assertEqual(cron["spec"]["concurrencyPolicy"], "Forbid")
        self.assertIn(ENV.cleanup_image, str(cron))
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

    def test_configure_emits_explicit_lifecycle_access_without_cloud_fields(self):
        cluster = {
            "resourceLabels": {"drydock-env": ENV.name},
            "status": "RUNNING",
            "currentMasterVersion": ENV.cluster_version,
        }
        with (
            patch.object(Environment, "gcloud", return_value=json.dumps(cluster)),
            patch("examples.demo.gke.run"),
            patch.object(LifecycleEnvironment, "apply") as apply,
        ):
            self.assertEqual(cloud.configure_infrastructure(ENV)["state"], "ready")
        lifecycle = LifecycleEnvironment.load(self.directory / "lifecycle.yml")
        self.assertEqual(lifecycle.kubeconfig, str(self.directory / "kubeconfig"))
        self.assertEqual(lifecycle.context, f"gke_{ENV.project}_{ENV.zone}_{ENV.name}")
        self.assertTrue(apply.called)

    def test_inventory_selects_dependents_without_selecting_other_networks(self):
        data = inventory()
        data["disks"] = [{"name": "gke-drydock-demo-pool-123"}, {"name": "unrelated"}]
        data["instances"] = [
            {
                "name": "worker",
                "networkInterfaces": [
                    {"network": "projects/p/global/networks/drydock-demo"}
                ],
            },
            {
                "name": "other",
                "networkInterfaces": [{"network": "projects/p/global/networks/other"}],
            },
        ]
        data["firewall-rules"] = [
            {"name": "rule", "network": "projects/p/global/networks/drydock-demo"}
        ]
        selected = cloud.selected_resources(ENV, data)
        self.assertEqual([r["name"] for r in selected["instances"]], ["worker"])
        self.assertEqual(
            [r["name"] for r in selected["disks"]], ["gke-drydock-demo-pool-123"]
        )
        self.assertEqual(len(selected["firewall-rules"]), 1)

    def test_destroy_refuses_foreign_resources_before_mutation(self):
        data = inventory()
        data["clusters"] = [
            {
                "name": ENV.name,
                "location": ENV.zone,
                "resourceLabels": {"drydock-env": ENV.name},
            }
        ]
        data["networks"] = [{"name": ENV.name, "description": "someone else"}]
        with (
            patch("examples.demo.gke.infrastructure_inventory", return_value=data),
            patch.object(Environment, "gcloud") as call,
        ):
            with self.assertRaises(ValueError):
                cloud.destroy_infrastructure(ENV)
            call.assert_not_called()

    def test_destroy_waits_for_cluster_and_retains_project(self):
        data = inventory()
        data["clusters"] = [
            {
                "name": ENV.name,
                "location": ENV.zone,
                "status": "RUNNING",
                "resourceLabels": {"drydock-env": ENV.name},
            }
        ]
        data["networks"] = [{"name": ENV.name, "description": "drydock:" + ENV.name}]
        calls = []

        def gcloud(*args):
            calls.append(args)
            return "[]"

        with (
            patch(
                "examples.demo.gke.infrastructure_inventory",
                side_effect=[data, inventory()],
            ),
            patch.object(Environment, "gcloud", side_effect=gcloud),
        ):
            self.assertTrue(cloud.destroy_infrastructure(ENV)["deleted"])
        self.assertEqual(calls[0][:3], ("container", "clusters", "delete"))
        self.assertEqual(calls[1][:3], ("container", "clusters", "list"))
        self.assertEqual(calls[2][:3], ("compute", "networks", "delete"))
        self.assertFalse(any(args[:2] == ("projects", "delete") for args in calls))
        self.assertEqual(
            json.loads((self.directory / "ownership.json").read_text())["state"],
            "deleted",
        )
        with patch(
            "examples.demo.gke.infrastructure_inventory", return_value=inventory()
        ):
            self.assertTrue(cloud.destroy_infrastructure(ENV)["deleted"])

    def test_failed_cluster_deletion_preserves_network_and_reports_remaining(self):
        data = inventory()
        data["clusters"] = [
            {
                "name": ENV.name,
                "location": ENV.zone,
                "status": "RUNNING",
                "resourceLabels": {"drydock-env": ENV.name},
            }
        ]
        with (
            patch("examples.demo.gke.infrastructure_inventory", return_value=data),
            patch.object(Environment, "gcloud", side_effect=RuntimeError) as call,
        ):
            result = cloud.destroy_infrastructure(ENV)
        self.assertFalse(result["deleted"])
        self.assertEqual(result["remaining"]["clusters"], 1)
        self.assertEqual(call.call_count, 1)
        self.assertTrue((self.directory / "cleanup.json").is_file())

    def test_leftover_disk_prevents_teardown_success(self):
        after = inventory()
        after["disks"] = [{"name": "gke-drydock-demo-default-pool-leftover"}]
        with patch(
            "examples.demo.gke.infrastructure_inventory",
            side_effect=[inventory(), after],
        ):
            self.assertFalse(cloud.destroy_infrastructure(ENV)["deleted"])

    def test_pending_cluster_creation_waits_before_shared_teardown(self):
        pending = inventory()
        pending["operations"] = [
            {
                "name": "create-cluster",
                "status": "RUNNING",
                "targetLink": "projects/p/zones/z/clusters/" + ENV.name,
            }
        ]
        with (
            patch(
                "examples.demo.gke.infrastructure_inventory",
                side_effect=[pending, inventory(), inventory(), inventory()],
            ),
            patch.object(Environment, "gcloud") as call,
        ):
            self.assertTrue(cloud.destroy_infrastructure(ENV)["deleted"])
        call.assert_not_called()

    def test_deploy_can_repeat_a_deleted_session_without_granting_cleaner_cloud_access(
        self,
    ):
        save(
            self.directory / "ownership.json",
            {"environment": asdict(ENV), "state": "deleted"},
        )
        data = inventory()
        data["roles"] = [
            {
                "name": "projects/demo-project/roles/drydock_demo",
                "deleted": True,
                "description": "drydock:" + ENV.name,
            }
        ]
        calls = []

        def gcloud(*args):
            self.assertTrue((self.directory / "ownership.json").is_file())
            calls.append(args)
            if args[:3] == ("container", "clusters", "list"):
                return json.dumps([{"name": ENV.name, "status": "RUNNING"}])
            return "{}"

        with (
            patch("examples.demo.gke.infrastructure_inventory", return_value=data),
            patch.object(Environment, "gcloud", side_effect=gcloud),
            patch(
                "examples.demo.gke.configure_infrastructure",
                return_value={"state": "ready"},
            ) as configure,
        ):
            self.assertEqual(cloud.deploy_infrastructure(ENV)["state"], "ready")
        configure.assert_called_once_with(ENV)
        self.assertFalse(any(args[:2] == ("iam", "roles") for args in calls))
        self.assertFalse(any("cleaner@" in str(args) for args in calls))

    def test_deploy_refuses_existing_resource_and_preserves_journal(self):
        (self.directory / "ownership.json").unlink()
        data = inventory()
        data["networks"] = [{"name": ENV.name}]
        with (
            patch("examples.demo.gke.infrastructure_inventory", return_value=data),
            patch.object(Environment, "gcloud") as call,
        ):
            with self.assertRaises(ValueError):
                cloud.deploy_infrastructure(ENV)
            call.assert_not_called()
        self.assertFalse((self.directory / "ownership.json").exists())


if __name__ == "__main__":
    unittest.main()
