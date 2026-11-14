"""GKE connection and renewable kubectl credentials outside the lifecycle core."""

import json
import os
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from drydock.core import Environment, save

SCOPES = "https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email"


def token():
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token", "--scopes=" + SCOPES, "--quiet"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode or not result.stdout.strip():
        raise RuntimeError("Temporary Google authentication failed.")
    return {
        "apiVersion": "client.authentication.k8s.io/v1beta1",
        "kind": "ExecCredential",
        "status": {
            "token": result.stdout.strip(),
            "expirationTimestamp": (datetime.now(UTC) + timedelta(minutes=1))
            .isoformat()
            .replace("+00:00", "Z"),
        },
    }


def configure(cluster, name):
    if not re.fullmatch(
        r"projects/[a-z][a-z0-9-]+/locations/[a-z0-9-]+/clusters/[a-z][a-z0-9-]+",
        cluster,
    ):
        raise ValueError("Invalid cluster resource.")
    parts = cluster.split("/")
    result = subprocess.run(
        [
            "gcloud",
            "container",
            "clusters",
            "describe",
            parts[5],
            "--project=" + parts[1],
            "--location=" + parts[3],
            "--format=json",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode:
        raise RuntimeError("Cluster connection discovery failed.")
    metadata = json.loads(result.stdout)
    path = Path("/tmp/kubeconfig")
    save(
        path,
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
            "users": [
                {
                    "name": "workflow",
                    "user": {
                        "exec": {
                            "apiVersion": "client.authentication.k8s.io/v1beta1",
                            "command": "/opt/venv/bin/python",
                            "args": ["-m", "examples.github.gke_credentials"],
                            "interactiveMode": "Never",
                        }
                    },
                }
            ],
            "contexts": [
                {"name": "approved", "context": {"cluster": "lab", "user": "workflow"}}
            ],
        },
    )
    save(
        Path("/tmp/environment.json"),
        {"name": name, "kubeconfig": str(path), "context": "approved"},
    )
    Environment.load("/tmp/environment.json")
    return Path("/tmp/environment.json")


if __name__ == "__main__":
    os.umask(0o077)
    try:
        print(json.dumps(token()))
    except Exception:
        raise SystemExit("Temporary Kubernetes authentication failed.") from None
