"""Operator-owned GKE demo setup. Lifecycle commands never import this module."""

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from drydock.cleaner import cleaner_objects
from drydock.core import (
    Environment,
    UserError,
    now,
    require_digest,
    run,
    save,
    wait_for,
)


@dataclass(frozen=True)
class GKEEnvironment:
    project: str
    zone: str
    name: str
    cluster_version: str
    clabernetes_version: str
    cleanup_image: str

    def __post_init__(self):
        patterns = {
            "project": r"[a-z][a-z0-9-]{4,28}[a-z0-9]",
            "zone": r"[a-z]+-[a-z]+[0-9]-[a-z]",
            "name": r"drydock-[a-z0-9](?:[a-z0-9-]{0,12}[a-z0-9])?",
            "cluster_version": r"[0-9]+\.[0-9]+\.[0-9]+-gke\.[0-9]+",
            "clabernetes_version": r"[0-9]+\.[0-9]+\.[0-9]+",
        }
        for key, pattern in patterns.items():
            if not re.fullmatch(pattern, getattr(self, key)):
                raise UserError(f"Invalid environment field: {key}")
        require_digest(self.cleanup_image)

    @classmethod
    def load(cls, path):
        return cls(**yaml.safe_load(Path(path).read_text()))

    @property
    def region(self):
        return self.zone.rsplit("-", 1)[0]

    @property
    def directory(self):
        return Path("artifacts/environments") / self.name

    @property
    def namespace(self):
        return self.name + "-system"

    def gcloud(self, *args, data=None):
        return run(
            ["gcloud", *args, f"--project={self.project}", "--quiet", "--format=json"],
            data=data,
        )


def infrastructure_inventory(env):
    commands = {
        "clusters": ("container", "clusters", "list"),
        "networks": ("compute", "networks", "list"),
        "subnets": ("compute", "networks", "subnets", "list"),
        "accounts": ("iam", "service-accounts", "list"),
        "roles": ("iam", "roles", "list", "--show-deleted"),
        "operations": ("container", "operations", "list", f"--zone={env.zone}"),
    }
    for resource in (
        "instances",
        "disks",
        "firewall-rules",
        "routes",
        "addresses",
        "forwarding-rules",
        "instance-groups",
        "instance-templates",
    ):
        commands[resource] = ("compute", resource, "list")
    inventory = {
        name: json.loads(env.gcloud(*command)) for name, command in commands.items()
    }
    inventory["bindings"] = json.loads(
        env.gcloud("projects", "get-iam-policy", env.project)
    ).get("bindings", [])
    return inventory


def selected_resources(env, inventory):
    accounts = {
        f"{env.name}-{kind}@{env.project}.iam.gserviceaccount.com"
        for kind in ("node", "cleaner")
    }
    selected = {
        "clusters": [r for r in inventory["clusters"] if r["name"] == env.name],
        "networks": [r for r in inventory["networks"] if r["name"] == env.name],
        "subnets": [r for r in inventory["subnets"] if r["name"] == env.name],
        "accounts": [r for r in inventory["accounts"] if r["email"] in accounts],
        "roles": [
            r
            for r in inventory["roles"]
            if r["name"].rsplit("/", 1)[-1] == env.name.replace("-", "_")
            and not r.get("deleted")
        ],
        "operations": [
            r
            for r in inventory.get("operations", [])
            if r.get("status") != "DONE"
            and (
                r.get("targetLink", "").endswith("/clusters/" + env.name)
                or "/clusters/" + env.name + "/" in r.get("targetLink", "")
            )
        ],
    }
    for category in set(inventory) - set(selected) - {"bindings"}:
        selected[category] = [
            r
            for r in inventory[category]
            if r.get("name", "").startswith(f"gke-{env.name}-")
            or any(
                isinstance(v, str)
                and (
                    v.endswith("/networks/" + env.name)
                    or v.endswith("/subnetworks/" + env.name)
                )
                for v in r.values()
            )
            or any(
                n.get("network", "").endswith("/networks/" + env.name)
                for n in r.get("networkInterfaces", [])
            )
        ]
    selected["bindings"] = [
        r
        for r in inventory.get("bindings", [])
        if any(
            any(account in member for account in accounts)
            for member in r.get("members", [])
        )
    ]
    return selected


def deploy_infrastructure(env):
    journal = env.directory / "ownership.json"
    if journal.exists() and json.loads(journal.read_text())["state"] != "deleted":
        raise UserError(
            "An ownership record already exists. Inspect or destroy that environment before deployment."
        )
    inventory = infrastructure_inventory(env)
    if any(selected_resources(env, inventory).values()):
        raise UserError(
            "A planned resource already exists. Deployment does not adopt existing resources."
        )
    save(
        journal, {"environment": asdict(env), "state": "creating", "accepted_at": now()}
    )
    marker = "drydock:" + env.name
    env.gcloud(
        "compute",
        "networks",
        "create",
        env.name,
        "--subnet-mode=custom",
        "--mtu=1460",
        f"--description={marker}",
    )
    env.gcloud(
        "compute",
        "networks",
        "subnets",
        "create",
        env.name,
        f"--network={env.name}",
        f"--region={env.region}",
        "--range=10.250.0.0/20",
        "--secondary-range=pods=10.251.0.0/16,services=10.252.0.0/20",
        f"--description={marker}",
    )
    env.gcloud(
        "iam",
        "service-accounts",
        "create",
        env.name + "-node",
        f"--description={marker}",
    )
    node_sa = f"{env.name}-node@{env.project}.iam.gserviceaccount.com"
    for role in (
        "roles/container.defaultNodeServiceAccount",
        "roles/artifactregistry.reader",
    ):
        env.gcloud(
            "projects",
            "add-iam-policy-binding",
            env.project,
            f"--member=serviceAccount:{node_sa}",
            f"--role={role}",
        )
    env.gcloud(
        "container",
        "clusters",
        "create",
        env.name,
        f"--zone={env.zone}",
        f"--node-locations={env.zone}",
        "--num-nodes=1",
        "--machine-type=e2-standard-2",
        "--disk-type=pd-standard",
        "--disk-size=30",
        "--image-type=UBUNTU_CONTAINERD",
        f"--network={env.name}",
        f"--subnetwork={env.name}",
        "--scopes=cloud-platform",
        "--enable-ip-alias",
        "--cluster-secondary-range-name=pods",
        "--services-secondary-range-name=services",
        "--default-max-pods-per-node=32",
        f"--service-account={node_sa}",
        f"--workload-pool={env.project}.svc.id.goog",
        "--node-labels=drydock-role=system",
        f"--labels=drydock-env={env.name}",
        f"--cluster-version={env.cluster_version}",
        "--release-channel=regular",
        "--logging=SYSTEM",
        "--monitoring=SYSTEM",
        "--no-enable-managed-prometheus",
        "--async",
    )
    wait_for(
        lambda: any(
            c["name"] == env.name and c.get("status") == "RUNNING"
            for c in json.loads(env.gcloud("container", "clusters", "list"))
        ),
        1800,
    )
    return configure_infrastructure(env)


def configure_infrastructure(env):
    journal = json.loads((env.directory / "ownership.json").read_text())
    if journal["environment"] != asdict(env):
        raise UserError("Environment differs from the ownership record.")
    cluster = json.loads(
        env.gcloud("container", "clusters", "describe", env.name, f"--zone={env.zone}")
    )
    if (
        cluster.get("resourceLabels", {}).get("drydock-env") != env.name
        or cluster.get("status") != "RUNNING"
    ):
        raise UserError("The owned cluster is not running.")
    env.directory.mkdir(parents=True, exist_ok=True)
    process_env = {**os.environ, "KUBECONFIG": str(env.directory / "kubeconfig")}
    run(
        [
            "gcloud",
            "container",
            "clusters",
            "get-credentials",
            env.name,
            f"--zone={env.zone}",
            f"--project={env.project}",
        ],
        env=process_env,
    )
    values = {
        "manager": {
            "replicaCount": 1,
            "affinity": {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [
                            {
                                "matchExpressions": [
                                    {
                                        "key": "cloud.google.com/gke-nodepool",
                                        "operator": "In",
                                        "values": ["default-pool"],
                                    }
                                ]
                            }
                        ]
                    }
                }
            },
        },
        "plannerPool": {"replicas": 1},
        "globalConfig": {"imagePull": {"policy": "IfNotPresent"}},
    }
    run(
        [
            "helm",
            "upgrade",
            "--install",
            "clabernetes",
            "oci://ghcr.io/clabernetes/clabernetes/clabernetes",
            "--create-namespace",
            "--namespace",
            env.namespace,
            "--version",
            env.clabernetes_version,
            "--kubeconfig",
            str(env.directory / "kubeconfig"),
            "--values",
            "-",
            "--wait",
            "--timeout",
            "5m",
        ],
        data=yaml.safe_dump(values),
        timeout=330,
    )
    lifecycle = Environment(
        env.name,
        str((env.directory / "kubeconfig").resolve()),
        f"gke_{env.project}_{env.zone}_{env.name}",
    )
    for obj in cleaner_objects(lifecycle, env.cleanup_image):
        if obj["kind"] == "CronJob":
            obj["spec"]["jobTemplate"]["spec"]["template"]["spec"]["nodeSelector"] = {
                "drydock-role": "system"
            }
        lifecycle.apply(obj)
    save(env.directory / "lifecycle.yml", asdict(lifecycle))
    save(
        env.directory / "ownership.json",
        {
            **journal,
            "state": "ready",
            "observed_gke_version": cluster["currentMasterVersion"],
        },
    )
    return {"environment": env.name, "state": "ready"}


def destroy_infrastructure(env):
    journal_path = env.directory / "ownership.json"
    journal = json.loads(journal_path.read_text())
    if journal["environment"] != asdict(env):
        raise UserError("Environment differs from the ownership record.")
    resources = selected_resources(env, infrastructure_inventory(env))
    if resources["operations"]:
        # A cluster allocation can be accepted before the cluster appears in list responses.
        wait_for(
            lambda: (
                not selected_resources(env, infrastructure_inventory(env))["operations"]
            ),
            1800,
        )
        resources = selected_resources(env, infrastructure_inventory(env))
    marker = "drydock:" + env.name
    # Refuse mismatches before deleting any infrastructure.
    for cluster in resources["clusters"]:
        if (
            cluster.get("resourceLabels", {}).get("drydock-env") != env.name
            or cluster.get("location") != env.zone
        ):
            raise UserError("Cluster ownership or location does not match.")
    for category in ("subnets", "networks", "accounts", "roles"):
        if any(r.get("description") != marker for r in resources[category]):
            raise UserError(f"{category} ownership does not match.")
    save(journal_path, {**journal, "state": "deleting"})
    errors = []
    if resources["clusters"]:
        try:
            if resources["clusters"][0].get("status") != "STOPPING":
                env.gcloud(
                    "container",
                    "clusters",
                    "delete",
                    env.name,
                    f"--zone={env.zone}",
                    "--async",
                )
            wait_for(
                lambda: (
                    not any(
                        c["name"] == env.name
                        for c in json.loads(env.gcloud("container", "clusters", "list"))
                    )
                ),
                1800,
            )
        except Exception as error:
            errors.append({"resource": "cluster", "error": type(error).__name__})
    # Keep network and identity prerequisites if cluster deletion is incomplete.
    if not errors:
        for category in ("subnets", "networks", "accounts", "roles"):
            for resource in resources[category]:
                try:
                    if category == "subnets":
                        env.gcloud(
                            "compute",
                            "networks",
                            "subnets",
                            "delete",
                            env.name,
                            f"--region={env.region}",
                        )
                    elif category == "networks":
                        env.gcloud("compute", "networks", "delete", env.name)
                    elif category == "accounts":
                        account = resource["email"]
                        roles = (
                            [
                                "roles/container.defaultNodeServiceAccount",
                                "roles/artifactregistry.reader",
                            ]
                            if account.startswith(env.name + "-node@")
                            else [
                                f"projects/{env.project}/roles/{env.name.replace('-', '_')}",
                                "roles/artifactregistry.reader",
                            ]
                        )
                        for role in roles:
                            policy = json.loads(
                                env.gcloud("projects", "get-iam-policy", env.project)
                            )
                            if any(
                                b["role"] == role
                                and f"serviceAccount:{account}" in b.get("members", [])
                                for b in policy.get("bindings", [])
                            ):
                                env.gcloud(
                                    "projects",
                                    "remove-iam-policy-binding",
                                    env.project,
                                    f"--member=serviceAccount:{account}",
                                    f"--role={role}",
                                    "--all",
                                )
                        env.gcloud("iam", "service-accounts", "delete", account)
                    else:
                        env.gcloud("iam", "roles", "delete", env.name.replace("-", "_"))
                except Exception as error:
                    errors.append({"resource": category, "error": type(error).__name__})
    try:
        remaining = selected_resources(env, infrastructure_inventory(env))
        counts = {key: len(value) for key, value in remaining.items()}
    except Exception as error:
        counts = {"unknown": 1}
        errors.append({"resource": "inventory", "error": type(error).__name__})
    result = {
        "environment": env.name,
        "deleted": not any(counts.values()) and not errors,
        "remaining": counts,
        "errors": errors,
        "observed_at": now(),
    }
    save(env.directory / "cleanup.json", result)
    if result["deleted"]:
        save(journal_path, {**journal, "state": "deleted"})
        (env.directory / "kubeconfig").unlink(missing_ok=True)
    return result
