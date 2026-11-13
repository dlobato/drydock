"""Render operator-installed lab permissions and admission. No cluster changes."""

import argparse
import base64
import json
from pathlib import Path

from .core import Environment, UserError, require_digest
from .lifecycle import object_meta


def access_objects(env, image, username, images, ca):
    require_digest(image)
    for approved in images:
        require_digest(approved)
    if not username or not images or b"-----BEGIN CERTIFICATE-----" not in ca:
        raise UserError(
            "Supply a workflow username, approved images, and the webhook CA certificate."
        )
    reader = env.name + "-lab-reader"
    caller = env.name + "-lifecycle"
    admission = env.name + "-admission"
    workflow_subject = {
        "kind": "User",
        "apiGroup": "rbac.authorization.k8s.io",
        "name": username,
    }
    admission_subject = {
        "kind": "ServiceAccount",
        "namespace": env.namespace,
        "name": "admission",
    }
    roles = [
        (
            "ClusterRole",
            reader,
            None,
            [
                {
                    "apiGroups": [""],
                    "resources": ["pods", "services"],
                    "verbs": ["get", "list"],
                },
                {
                    "apiGroups": ["c9s.run"],
                    "resources": ["topologies", "nodes", "links"],
                    "verbs": ["get", "list"],
                },
            ],
            None,
        ),
        (
            "ClusterRole",
            caller,
            None,
            [
                {
                    "apiGroups": [""],
                    "resources": ["namespaces"],
                    "verbs": ["get", "list", "create", "delete"],
                },
                {"apiGroups": [""], "resources": ["secrets"], "verbs": ["create"]},
                {
                    "apiGroups": ["c9s.run"],
                    "resources": ["topologies"],
                    "verbs": ["create"],
                },
            ],
            workflow_subject,
        ),
        (
            "Role",
            caller,
            env.namespace,
            [
                {
                    "apiGroups": [""],
                    "resources": ["configmaps"],
                    "verbs": ["get", "list", "create", "update"],
                },
            ],
            workflow_subject,
        ),
        (
            "ClusterRole",
            admission,
            None,
            [
                {
                    "apiGroups": [""],
                    "resources": ["namespaces"],
                    "verbs": ["get", "list"],
                },
                {
                    "apiGroups": ["rbac.authorization.k8s.io"],
                    "resources": ["rolebindings"],
                    "verbs": ["get", "list", "create"],
                },
                {
                    "apiGroups": ["rbac.authorization.k8s.io"],
                    "resources": ["clusterroles"],
                    "resourceNames": [reader],
                    "verbs": ["bind"],
                },
            ],
            admission_subject,
        ),
        (
            "Role",
            admission,
            env.namespace,
            [
                {
                    "apiGroups": [""],
                    "resources": ["configmaps"],
                    "verbs": ["get", "list"],
                },
            ],
            admission_subject,
        ),
    ]
    yield {
        "apiVersion": "admissionregistration.k8s.io/v1",
        "kind": "ValidatingWebhookConfiguration",
        "metadata": object_meta(env, admission),
        "webhooks": [
            {
                "name": admission + ".drydock.io",
                "admissionReviewVersions": ["v1"],
                "sideEffects": "None",
                "failurePolicy": "Fail",
                "matchPolicy": "Equivalent",
                "timeoutSeconds": 10,
                "matchConditions": [
                    {
                        "name": "lab-identities",
                        "expression": "request.userInfo.username in "
                        + json.dumps(
                            [
                                username,
                                "system:serviceaccount:" + env.namespace + ":cleaner",
                            ]
                        ),
                    }
                ],
                "clientConfig": {
                    "service": {
                        "namespace": env.namespace,
                        "name": "admission",
                        "path": "/validate",
                        "port": 443,
                    },
                    "caBundle": base64.b64encode(ca).decode(),
                },
                "rules": [
                    {
                        "apiGroups": [""],
                        "apiVersions": ["v1"],
                        "resources": ["namespaces", "secrets", "configmaps"],
                        "operations": ["CREATE", "UPDATE", "DELETE"],
                        "scope": "*",
                    },
                    {
                        "apiGroups": ["c9s.run"],
                        "apiVersions": ["v1alpha1"],
                        "resources": ["topologies"],
                        "operations": ["CREATE", "UPDATE", "DELETE"],
                        "scope": "Namespaced",
                    },
                ],
            }
        ],
    }
    yield {
        "apiVersion": "v1",
        "kind": "ServiceAccount",
        "metadata": object_meta(env, "admission", env.namespace),
    }
    for kind, name, namespace, rules, subject in roles:
        yield {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": kind,
            "metadata": object_meta(env, name, namespace),
            "rules": rules,
        }
        if subject:
            yield {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": kind + "Binding",
                "metadata": object_meta(env, name, namespace),
                "roleRef": {
                    "apiGroup": "rbac.authorization.k8s.io",
                    "kind": kind,
                    "name": name,
                },
                "subjects": [subject],
            }
    yield {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": object_meta(env, "admission", env.namespace),
        "spec": {
            "selector": {"app": admission},
            "ports": [{"port": 443, "targetPort": 8443}],
        },
    }
    yield {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": object_meta(env, "admission", env.namespace),
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": admission}},
            "template": {
                "metadata": {"labels": {"app": admission}},
                "spec": {
                    "serviceAccountName": "admission",
                    "securityContext": {
                        "runAsNonRoot": True,
                        "runAsUser": 65532,
                        "runAsGroup": 65532,
                        "seccompProfile": {"type": "RuntimeDefault"},
                    },
                    "containers": [
                        {
                            "name": "admission",
                            "image": image,
                            "command": [
                                "/opt/drydock/bin/python",
                                "-m",
                                "drydock.admission",
                                "--environment",
                                "/environment/environment.yml",
                                "--username",
                                username,
                                "--certificate",
                                "/tls/tls.crt",
                                "--key",
                                "/tls/tls.key",
                                *[
                                    arg
                                    for approved in images
                                    for arg in ("--ceos-image", approved)
                                ],
                            ],
                            "env": [
                                {"name": "HOME", "value": "/tmp"},
                                {"name": "PYTHONDONTWRITEBYTECODE", "value": "1"},
                            ],
                            "ports": [{"containerPort": 8443}],
                            "readinessProbe": {"tcpSocket": {"port": 8443}},
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                                "limits": {"cpu": "1", "memory": "512Mi"},
                            },
                            "securityContext": {
                                "allowPrivilegeEscalation": False,
                                "readOnlyRootFilesystem": True,
                                "capabilities": {"drop": ["ALL"]},
                            },
                            "volumeMounts": [
                                {
                                    "name": "environment",
                                    "mountPath": "/environment",
                                    "readOnly": True,
                                },
                                {"name": "tls", "mountPath": "/tls", "readOnly": True},
                                {"name": "temporary", "mountPath": "/tmp"},
                            ],
                        }
                    ],
                    "volumes": [
                        {"name": "environment", "configMap": {"name": "environment"}},
                        {"name": "tls", "secret": {"secretName": "admission-tls"}},
                        {"name": "temporary", "emptyDir": {}},
                    ],
                },
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--ceos-image", action="append", required=True)
    parser.add_argument("--ca-certificate", required=True)
    args = parser.parse_args()
    items = access_objects(
        Environment.load(args.environment),
        args.image,
        args.username,
        args.ceos_image,
        Path(args.ca_certificate).read_bytes(),
    )
    print(json.dumps({"apiVersion": "v1", "kind": "List", "items": list(items)}))


if __name__ == "__main__":
    main()
