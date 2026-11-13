"""Test temporary access without allocating a lab or printing credentials."""

import json
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path


def api(url, token, data=None):
    request = urllib.request.Request(
        url,
        data=None if data is None else json.dumps(data).encode(),
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def probe(token, cluster, namespace, username):
    # The workflow supplies operator configuration, never a PR-controlled URL.
    if not re.fullmatch(
        r"projects/[a-z][a-z0-9-]+/locations/[a-z0-9-]+/clusters/[a-z][a-z0-9-]+",
        cluster,
    ):
        raise ValueError("Invalid cluster resource.")
    metadata = api("https://container.googleapis.com/v1/" + cluster, token)
    permissions = [
        "container.clusters.get",
        "container.clusters.create",
        "container.clusters.delete",
        "container.clusters.update",
        "compute.instances.create",
        "iam.serviceAccounts.create",
        "resourcemanager.projects.setIamPolicy",
    ]
    result = api(
        "https://cloudresourcemanager.googleapis.com/v1/"
        + "/".join(cluster.split("/")[:2])
        + ":testIamPermissions",
        token,
        {"permissions": permissions},
    )
    if set(result.get("permissions", [])) != {"container.clusters.get"}:
        raise ValueError("Google permissions exceed the connection boundary.")
    with tempfile.TemporaryDirectory(prefix="drydock-access-") as directory:
        kubeconfig = Path(directory) / "kubeconfig"
        kubeconfig.write_text(
            json.dumps(
                {
                    "apiVersion": "v1",
                    "kind": "Config",
                    "current-context": "approved",
                    "clusters": [
                        {
                            "name": "lab",
                            "cluster": {
                                "server": "https://"
                                + metadata["privateClusterConfig"]["privateEndpoint"],
                                "certificate-authority-data": metadata["masterAuth"][
                                    "clusterCaCertificate"
                                ],
                            },
                        }
                    ],
                    "users": [{"name": "workflow", "user": {"token": token}}],
                    "contexts": [
                        {
                            "name": "approved",
                            "context": {"cluster": "lab", "user": "workflow"},
                        }
                    ],
                }
            )
        )
        kubeconfig.chmod(0o600)

        def kubectl(*args):
            return subprocess.run(
                [
                    "kubectl",
                    "--request-timeout=15s",
                    "--kubeconfig",
                    str(kubeconfig),
                    "--context",
                    "approved",
                    *args,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

        identity = kubectl("auth", "whoami", "-o", "json")
        if (
            identity.returncode
            or json.loads(identity.stdout)["status"]["userInfo"]["username"] != username
        ):
            raise ValueError("The authenticated Kubernetes identity does not match.")
        if kubectl("get", "configmaps", "-n", namespace, "-o", "name").returncode:
            raise ValueError("Ownership record access was denied.")
        denied = [
            ("get", "secrets", "-n", "default"),
            ("list", "secrets", "--all-namespaces"),
            ("create", "rolebindings", "-n", namespace),
            ("create", "clusterrolebindings"),
            ("create", "pods", "-n", namespace),
            ("create", "deployments.apps", "-n", namespace),
            ("get", "pods", "-n", "default"),
            ("create", "serviceaccounts/token", "-n", namespace),
        ]
        for operation in denied:
            response = kubectl("auth", "can-i", *operation)
            if (
                response.returncode != 1
                or response.stdout.strip().partition(" - ")[0] != "no"
            ):
                raise ValueError("An unrelated operation was not explicitly denied.")
    return {
        "temporary_access": "passed",
        "kubernetes_denials": len(denied),
        "cloud_administration": "denied",
        "lab_created": False,
        "network_tests": "not_run",
    }


if __name__ == "__main__":
    try:
        outcome = probe(
            os.environ["DRYDOCK_ACCESS_TOKEN"],
            os.environ["GKE_CLUSTER_RESOURCE"],
            os.environ["DRYDOCK_SYSTEM_NAMESPACE"],
            os.environ["GKE_WORKFLOW_USERNAME"],
        )
    except Exception:
        raise SystemExit(
            "GKE access probe failed. No provider response or credential output was retained."
        ) from None
    print(json.dumps(outcome))
