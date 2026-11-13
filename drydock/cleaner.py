"""Render an independent cleaner for an operator-supplied Kubernetes cluster."""

import argparse
import json
from dataclasses import asdict

import yaml

from .core import Environment, require_digest
from .lifecycle import object_meta


def cleaner_objects(env, image):
    require_digest(image)
    role = env.name + "-cleaner"
    yield {
        "apiVersion": "v1",
        "kind": "ServiceAccount",
        "metadata": object_meta(env, "cleaner", env.namespace),
    }
    yield {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "ClusterRole",
        "metadata": object_meta(env, role),
        "rules": [
            {
                "apiGroups": [""],
                "resources": ["namespaces"],
                "verbs": ["get", "list", "delete"],
            }
        ],
    }
    yield {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "ClusterRoleBinding",
        "metadata": object_meta(env, role),
        "roleRef": {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "ClusterRole",
            "name": role,
        },
        "subjects": [
            {"kind": "ServiceAccount", "name": "cleaner", "namespace": env.namespace}
        ],
    }
    yield {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "Role",
        "metadata": object_meta(env, role, env.namespace),
        "rules": [
            {
                "apiGroups": [""],
                "resources": ["configmaps"],
                "verbs": ["get", "list", "create", "update"],
            }
        ],
    }
    yield {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "RoleBinding",
        "metadata": object_meta(env, role, env.namespace),
        "roleRef": {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "Role",
            "name": role,
        },
        "subjects": [
            {"kind": "ServiceAccount", "name": "cleaner", "namespace": env.namespace}
        ],
    }
    yield {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": object_meta(env, "environment", env.namespace),
        "data": {
            "environment.yml": yaml.safe_dump(
                asdict(Environment(env.name, "/environment/kubeconfig", "cleaner"))
            ),
            "kubeconfig": yaml.safe_dump(
                {
                    "apiVersion": "v1",
                    "kind": "Config",
                    "current-context": "cleaner",
                    "clusters": [
                        {
                            "name": "cluster",
                            "cluster": {
                                "server": "https://kubernetes.default.svc",
                                "certificate-authority": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
                            },
                        }
                    ],
                    "users": [
                        {
                            "name": "cleaner",
                            "user": {
                                "tokenFile": "/var/run/secrets/kubernetes.io/serviceaccount/token"
                            },
                        }
                    ],
                    "contexts": [
                        {
                            "name": "cleaner",
                            "context": {"cluster": "cluster", "user": "cleaner"},
                        }
                    ],
                }
            ),
        },
    }
    yield {
        "apiVersion": "batch/v1",
        "kind": "CronJob",
        "metadata": object_meta(env, "cleanup", env.namespace),
        "spec": {
            "schedule": "*/5 * * * *",
            "concurrencyPolicy": "Forbid",
            "startingDeadlineSeconds": 240,
            "successfulJobsHistoryLimit": 1,
            "failedJobsHistoryLimit": 3,
            "jobTemplate": {
                "spec": {
                    "activeDeadlineSeconds": 240,
                    "backoffLimit": 0,
                    "template": {
                        "spec": {
                            "serviceAccountName": "cleaner",
                            "restartPolicy": "Never",
                            "containers": [
                                {
                                    "name": "cleanup",
                                    "image": image,
                                    "command": [
                                        "/opt/drydock/bin/python",
                                        "-m",
                                        "drydock",
                                        "--environment",
                                        "/environment/environment.yml",
                                        "reap",
                                    ],
                                    "resources": {
                                        "requests": {"cpu": "100m", "memory": "128Mi"},
                                        "limits": {"cpu": "1", "memory": "512Mi"},
                                    },
                                    "volumeMounts": [
                                        {
                                            "name": "environment",
                                            "mountPath": "/environment",
                                            "readOnly": True,
                                        }
                                    ],
                                }
                            ],
                            "volumes": [
                                {
                                    "name": "environment",
                                    "configMap": {"name": "environment"},
                                }
                            ],
                        }
                    },
                }
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    objects = cleaner_objects(Environment.load(args.environment), args.image)
    print(json.dumps({"apiVersion": "v1", "kind": "List", "items": list(objects)}))


if __name__ == "__main__":
    main()
