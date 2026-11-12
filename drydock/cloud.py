"""GKE resources, Kubernetes ownership records, and independent lab expiry."""

from dataclasses import asdict
import base64
import json
import os
import re
from uuid import uuid4

import yaml

from .core import UserError, ENV_LABEL, LAB_LABEL, now, run, save, wait_for


def object_meta(env, name, namespace=None, lab=None):
    metadata = {"name": name, "labels": {ENV_LABEL: env.name}}
    if namespace:
        metadata["namespace"] = namespace
    if lab:
        metadata["labels"][LAB_LABEL] = lab
    return metadata


def pool_labels(env, lab):
    return {"drydock-env": env.name, "drydock-lab": lab}


def pools(env):
    return json.loads(env.gcloud("container", "node-pools", "list", f"--cluster={env.name}", f"--zone={env.zone}"))


def owned_pool(pool, env, lab):
    return pool.get("config", {}).get("labels", {}).items() >= pool_labels(env, lab).items()


def check_lab(lab):
    if not re.fullmatch(r"lab-[a-f0-9]{12}", lab):
        raise UserError("Invalid lab identifier.")


def lab_record(env, lab):
    check_lab(lab)
    records = env.objects("configmaps", env.namespace, f"{ENV_LABEL}={env.name},{LAB_LABEL}={lab}")
    if not records:
        return None
    record = json.loads(records[0]["data"]["record"])
    if record["id"] != lab or record["environment"] != env.name:
        raise UserError("Lab ownership record does not match its labels.")
    record["resource_version"] = records[0]["metadata"]["resourceVersion"]
    return record


def write_record(env, record, create=False):
    version = record.pop("resource_version", None)
    obj = {"apiVersion": "v1", "kind": "ConfigMap",
           "metadata": object_meta(env, record["id"], env.namespace, record["id"]),
           "data": {"record": json.dumps(record)}}
    if create:
        env.kube("create", "-f", "-", data=json.dumps(obj))
    else:
        if not version:
            raise UserError("Updating ownership requires its resource version.")
        obj["metadata"]["resourceVersion"] = version
        env.kube("replace", "-f", "-", data=json.dumps(obj))


def allocation_record(env, lab):
    record = lab_record(env, lab)
    if not record or record["state"] != "creating" or record["expires_at"] <= now():
        raise UserError("Allocation stopped because the lab expired or cleanup started.")
    return record


def registry_secret(env, lab, registry):
    namespace = env.name + "-" + lab
    token = json.loads(env.gcloud("auth", "print-access-token"))["token"]
    auth = base64.b64encode(("oauth2accesstoken:" + token).encode()).decode()
    env.apply({"apiVersion": "v1", "kind": "Secret", "metadata": object_meta(env, "registry", namespace, lab),
               "type": "kubernetes.io/dockerconfigjson", "stringData": {".dockerconfigjson": json.dumps({
                   "auths": {registry: {"auth": auth}}})}})


def validate_request(bundle, provenance, lifetime):
    if type(lifetime) is not int or not 1 <= lifetime <= 240:
        raise UserError("Lab lifetime must be between 1 and 240 minutes.")
    if not all(isinstance(provenance.get(key), str) and provenance[key].strip()
               for key in ("repository", "commit", "run", "attempt")):
        raise UserError("Supply repository, commit, run, and attempt identity.")
    image = bundle.topology["topology"]["kinds"]["arista_ceos"]["image"]
    registry = image.split("/")[0]
    if not re.fullmatch(r"[a-z]+-[a-z]+[0-9]-docker.pkg.dev", registry):
        raise UserError("The demo requires a cEOS digest in regional Google Artifact Registry.")
    return image, registry


def create_lab(env, bundle, provenance, lifetime=120, lab=None):
    image, registry = validate_request(bundle, provenance, lifetime)
    lab = lab or "lab-" + uuid4().hex[:12]
    check_lab(lab)
    accepted = now()
    record = {"id": lab, "environment": env.name, "accepted_at": accepted,
              "expires_at": accepted + lifetime * 60, "state": "creating",
              "bundle_digest": bundle.digest, "provenance": provenance, "registry": registry,
              "runtime": {"ceos_image": image, "gke_requested": env.cluster_version,
                          "clabernetes": env.clabernetes_version}}
    # Commit ownership before the first allocation, including the planned pool name.
    write_record(env, record, create=True)
    allocation_record(env, lab)
    labels = pool_labels(env, lab)
    env.gcloud("container", "node-pools", "create", lab, f"--cluster={env.name}", f"--zone={env.zone}",
               f"--node-locations={env.zone}", "--num-nodes=2", "--machine-type=e2-standard-4",
               "--disk-type=pd-standard", "--disk-size=30", "--image-type=UBUNTU_CONTAINERD",
               "--scopes=cloud-platform",
               "--node-labels=" + ",".join(f"{k}={v}" for k, v in labels.items()),
               f"--node-taints=drydock-lab={lab}:NoSchedule", f"--service-account={env.name}-node@{env.project}.iam.gserviceaccount.com",
               "--workload-metadata=GKE_METADATA", "--async")
    allocation_record(env, lab)
    namespace = env.name + "-" + lab
    env.kube("create", "-f", "-", data=json.dumps({"apiVersion": "v1", "kind": "Namespace",
             "metadata": {**object_meta(env, namespace, lab=lab), "labels": {
                 ENV_LABEL: env.name, LAB_LABEL: lab, "pod-security.kubernetes.io/enforce": "privileged"}}}))
    allocation_record(env, lab)
    registry_secret(env, lab, registry)
    files = {f"{name}.cfg": text for name, text in
             ((name, bundle.files[f"intended/configs/{name}.cfg"]) for name in bundle.interfaces)}
    files["interface_mapping.json"] = bundle.files["interface_mapping.json"]
    env.apply({"apiVersion": "v1", "kind": "Secret", "metadata": object_meta(env, "startup", namespace, lab),
               "type": "Opaque", "stringData": files})
    nodes = {}
    attachments = {}
    for name, original in bundle.topology["topology"]["nodes"].items():
        nodes[name] = {"kind": "arista_ceos", "image": image, "mgmt-ipv4": original["mgmt-ipv4"],
                       "enforce-startup-config": True,
                       "startup-config": f"/drydock/{name}.cfg", "ports": ["443/tcp"],
                       "binds": ["/drydock/interface_mapping.json:/mnt/flash/EosIntfMapping.json:ro"]}
        attachments[name] = [{"filePath": f"/drydock/{name}.cfg", "secretName": "startup", "secretPath": f"{name}.cfg"},
                             {"filePath": "/drydock/interface_mapping.json", "secretName": "startup", "secretPath": "interface_mapping.json"}]
    allocation_record(env, lab)
    topology = {"name": "fabric", "prefix": "", "mgmt": {**bundle.topology["mgmt"], "network": lab},
                "topology": {"nodes": nodes, "links": bundle.topology["topology"]["links"]}}
    env.apply({"apiVersion": "c9s.run/v1alpha1", "kind": "Topology",
               "metadata": object_meta(env, "fabric", namespace, lab), "spec": {
                   "imagePull": {"pullSecrets": ["registry"]},
                   "expose": {"exposeType": "ClusterIP", "disableAutoExpose": True},
                   "deployment": {"filesFromSecret": attachments,
                       "resources": {"default": {"requests": {"cpu": "1", "memory": "2Gi"}, "limits": {"cpu": "2", "memory": "3Gi"}}},
                       "scheduling": {"nodeSelector": labels, "tolerations": [
                           {"key": "drydock-lab", "operator": "Equal", "value": lab, "effect": "NoSchedule"}]}},
                   "definition": {"containerlab": yaml.safe_dump(topology)}}})
    record = allocation_record(env, lab)
    record["state"] = "running"
    write_record(env, record)
    return record


def delete_lab(env, lab):
    check_lab(lab)
    record = lab_record(env, lab)
    namespace = env.name + "-" + lab
    errors = []
    if record:
        record["state"] = "deleting"
        record["overdue"] = now() > record["expires_at"] + 1800
        write_record(env, record)
    namespaces = env.objects("namespaces")
    for item in namespaces:
        if item["metadata"]["name"] == namespace:
            if not item["metadata"].get("labels", {}).items() >= {ENV_LABEL: env.name, LAB_LABEL: lab}.items():
                raise UserError("Refusing to delete a namespace with different ownership.")
            try:
                env.kube("delete", "namespace", namespace, "--wait=false", "--ignore-not-found")
            except (RuntimeError, TimeoutError) as error:
                errors.append(str(error))
    for pool in pools(env):
        if pool["name"] == lab:
            if not owned_pool(pool, env, lab):
                raise UserError("Refusing to delete a worker pool with different ownership.")
            try:
                if pool.get("status") != "STOPPING":
                    env.gcloud("container", "node-pools", "delete", lab, f"--cluster={env.name}", f"--zone={env.zone}", "--async")
            except (RuntimeError, TimeoutError) as error:
                errors.append(str(error))
    remaining_namespace = any(item["metadata"]["name"] == namespace for item in env.objects("namespaces"))
    remaining_pool = any(pool["name"] == lab for pool in pools(env))
    operations = json.loads(env.gcloud("container", "operations", "list", f"--zone={env.zone}"))
    pending = [op["name"] for op in operations if op.get("status") != "DONE" and
               (op.get("targetLink", "").endswith(f"/clusters/{env.name}/nodePools/{lab}") or
                op.get("targetLink", "").endswith(f"/clusters/{env.name}"))]
    complete = not remaining_namespace and not remaining_pool and not pending and not errors
    result = {"lab": lab, "deleted": complete, "namespace_remaining": remaining_namespace,
              "pool_remaining": remaining_pool, "pending_operations": pending, "errors": errors}
    if record:
        record = lab_record(env, lab)
        record["state"] = "deleted" if complete else "deleting"
        record["cleanup"] = result
        record["overdue"] = now() > record["expires_at"] + 1800
        write_record(env, record)
    return result


def reap(env):
    outcomes = []
    records = env.objects("configmaps", env.namespace, f"{ENV_LABEL}={env.name},{LAB_LABEL}")
    for item in records:
        record = json.loads(item["data"]["record"])
        # Revisit deleted records too: an accepted asynchronous allocation can appear late.
        if record["expires_at"] <= now() or record["state"] in {"deleting", "deleted"}:
            try:
                outcomes.append(delete_lab(env, record["id"]))
            except Exception as error:
                outcomes.append({"lab": record["id"], "deleted": False, "error": str(error),
                                 "overdue": now() > record["expires_at"] + 1800})
        elif record["state"] == "running":
            try:
                namespaces = env.objects("namespaces")
                namespace = next((n for n in namespaces if n["metadata"]["name"] == env.name + "-" + record["id"]), None)
                if namespace and namespace["metadata"].get("labels", {}).items() >= {
                        ENV_LABEL: env.name, LAB_LABEL: record["id"]}.items():
                    registry_secret(env, record["id"], record["registry"])
            except Exception:
                outcomes.append({"lab": record["id"], "error": "Registry token refresh failed."})
    return outcomes


def infrastructure_inventory(env):
    commands = {"clusters": ("container", "clusters", "list"), "networks": ("compute", "networks", "list"),
                "subnets": ("compute", "networks", "subnets", "list"),
                "accounts": ("iam", "service-accounts", "list"), "roles": ("iam", "roles", "list", "--show-deleted"),
                "operations": ("container", "operations", "list", f"--zone={env.zone}")}
    for resource in ("instances", "disks", "firewall-rules", "routes", "addresses", "forwarding-rules",
                     "instance-groups", "instance-templates"):
        commands[resource] = ("compute", resource, "list")
    inventory = {name: json.loads(env.gcloud(*command)) for name, command in commands.items()}
    inventory["bindings"] = json.loads(env.gcloud("projects", "get-iam-policy", env.project)).get("bindings", [])
    return inventory


def selected_resources(env, inventory):
    accounts = {f"{env.name}-{kind}@{env.project}.iam.gserviceaccount.com" for kind in ("node", "cleaner")}
    selected = {"clusters": [r for r in inventory["clusters"] if r["name"] == env.name],
            "networks": [r for r in inventory["networks"] if r["name"] == env.name],
            "subnets": [r for r in inventory["subnets"] if r["name"] == env.name],
            "accounts": [r for r in inventory["accounts"] if r["email"] in accounts],
            "roles": [r for r in inventory["roles"] if r["name"].rsplit("/", 1)[-1] == env.name.replace("-", "_") and not r.get("deleted")],
            "operations": [r for r in inventory.get("operations", []) if r.get("status") != "DONE" and
                           (r.get("targetLink", "").endswith("/clusters/" + env.name) or
                            "/clusters/" + env.name + "/" in r.get("targetLink", ""))]}
    for category in set(inventory) - set(selected) - {"bindings"}:
        selected[category] = [r for r in inventory[category] if
            r.get("name", "").startswith(f"gke-{env.name}-") or
            any(isinstance(v, str) and (v.endswith("/networks/" + env.name) or
                v.endswith("/subnetworks/" + env.name)) for v in r.values()) or
            any(n.get("network", "").endswith("/networks/" + env.name) for n in r.get("networkInterfaces", []))]
    selected["bindings"] = [r for r in inventory.get("bindings", []) if
        any(any(account in member for account in accounts) for member in r.get("members", []))]
    return selected


def deploy_infrastructure(env):
    journal = env.directory / "ownership.json"
    if journal.exists() and json.loads(journal.read_text())["state"] != "deleted":
        raise UserError("An ownership record already exists. Inspect or destroy that environment before deployment.")
    inventory = infrastructure_inventory(env)
    if any(selected_resources(env, inventory).values()):
        raise UserError("A planned resource already exists. Deployment does not adopt existing resources.")
    role_id = env.name.replace("-", "_")
    deleted_role = next((r for r in inventory["roles"] if r["name"].rsplit("/", 1)[-1] == role_id), None)
    if deleted_role and deleted_role.get("description") != "drydock:" + env.name:
        raise UserError("A deleted role has different ownership.")
    save(journal, {"environment": asdict(env), "state": "creating", "accepted_at": now()})
    marker = "drydock:" + env.name
    env.gcloud("compute", "networks", "create", env.name, "--subnet-mode=custom", "--mtu=1460", f"--description={marker}")
    env.gcloud("compute", "networks", "subnets", "create", env.name, f"--network={env.name}",
               f"--region={env.region}", "--range=10.250.0.0/20",
               "--secondary-range=pods=10.251.0.0/16,services=10.252.0.0/20", f"--description={marker}")
    for kind in ("node", "cleaner"):
        env.gcloud("iam", "service-accounts", "create", env.name + "-" + kind, f"--description={marker}")
    node_sa = f"{env.name}-node@{env.project}.iam.gserviceaccount.com"
    cleaner_sa = f"{env.name}-cleaner@{env.project}.iam.gserviceaccount.com"
    for role in ("roles/container.defaultNodeServiceAccount", "roles/artifactregistry.reader"):
        env.gcloud("projects", "add-iam-policy-binding", env.project, f"--member=serviceAccount:{node_sa}", f"--role={role}")
    if deleted_role:
        env.gcloud("iam", "roles", "undelete", role_id)
    env.gcloud("iam", "roles", "update" if deleted_role else "create", role_id, f"--title={env.name}", f"--description={marker}",
               "--permissions=container.clusters.get,container.clusters.list,container.clusters.update,container.operations.get,container.operations.list")
    # GKE authorizes node-pool deletion through container.clusters.update.
    env.gcloud("projects", "add-iam-policy-binding", env.project, f"--member=serviceAccount:{cleaner_sa}",
               f"--role=projects/{env.project}/roles/{role_id}")
    env.gcloud("projects", "add-iam-policy-binding", env.project, f"--member=serviceAccount:{cleaner_sa}",
               "--role=roles/artifactregistry.reader")
    env.gcloud("iam", "service-accounts", "add-iam-policy-binding", cleaner_sa,
               "--role=roles/iam.workloadIdentityUser",
               f"--member=serviceAccount:{env.project}.svc.id.goog[{env.namespace}/cleaner]")
    env.gcloud("container", "clusters", "create", env.name, f"--zone={env.zone}", f"--node-locations={env.zone}",
               "--num-nodes=1", "--machine-type=e2-standard-2", "--disk-type=pd-standard", "--disk-size=30",
               "--image-type=UBUNTU_CONTAINERD", f"--network={env.name}", f"--subnetwork={env.name}",
               "--scopes=cloud-platform",
               "--enable-ip-alias", "--cluster-secondary-range-name=pods", "--services-secondary-range-name=services",
               "--default-max-pods-per-node=32", f"--service-account={node_sa}",
               f"--workload-pool={env.project}.svc.id.goog", "--node-labels=drydock-role=system",
               f"--labels=drydock-env={env.name}", f"--cluster-version={env.cluster_version}",
               "--release-channel=regular", "--logging=SYSTEM", "--monitoring=SYSTEM", "--no-enable-managed-prometheus", "--async")
    wait_for(lambda: any(c["name"] == env.name and c.get("status") == "RUNNING" for c in
                        json.loads(env.gcloud("container", "clusters", "list"))), 1800)
    return configure_infrastructure(env)


def configure_infrastructure(env):
    journal = json.loads((env.directory / "ownership.json").read_text())
    if journal["environment"] != asdict(env):
        raise UserError("Environment differs from the ownership record.")
    cluster = json.loads(env.gcloud("container", "clusters", "describe", env.name, f"--zone={env.zone}"))
    if cluster.get("resourceLabels", {}).get("drydock-env") != env.name or cluster.get("status") != "RUNNING":
        raise UserError("The owned cluster is not running.")
    env.directory.mkdir(parents=True, exist_ok=True)
    process_env = {**os.environ, "KUBECONFIG": str(env.directory / "kubeconfig")}
    run(["gcloud", "container", "clusters", "get-credentials", env.name, f"--zone={env.zone}", f"--project={env.project}"], env=process_env)
    values = {"manager": {"replicaCount": 1, "affinity": {"nodeAffinity": {
        "requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [{"matchExpressions": [
            {"key": "cloud.google.com/gke-nodepool", "operator": "In", "values": ["default-pool"]}]}]}}}},
        "plannerPool": {"replicas": 1}, "globalConfig": {"imagePull": {"policy": "IfNotPresent"}}}
    run(["helm", "upgrade", "--install", "clabernetes", "oci://ghcr.io/clabernetes/clabernetes/clabernetes",
         "--create-namespace", "--namespace", env.namespace, "--version", env.clabernetes_version,
         "--kubeconfig", str(env.directory / "kubeconfig"), "--values", "-", "--wait", "--timeout", "5m"],
        data=yaml.safe_dump(values), timeout=330)
    for obj in cleaner_objects(env):
        env.apply(obj)
    save(env.directory / "ownership.json", {**journal, "state": "ready", "observed_gke_version": cluster["currentMasterVersion"]})
    return {"environment": env.name, "state": "ready"}


def cleaner_objects(env):
    role = env.name + "-cleaner"
    yield {"apiVersion": "v1", "kind": "ServiceAccount", "metadata": {
        **object_meta(env, "cleaner", env.namespace), "annotations": {
            "iam.gke.io/gcp-service-account": f"{env.name}-cleaner@{env.project}.iam.gserviceaccount.com"}}}
    yield {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRole", "metadata": object_meta(env, role),
           "rules": [{"apiGroups": [""], "resources": ["namespaces"], "verbs": ["get", "list", "delete"]},
                     {"apiGroups": [""], "resources": ["secrets"], "verbs": ["get", "create", "patch", "update"]}]}
    yield {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRoleBinding", "metadata": object_meta(env, role),
           "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "ClusterRole", "name": role},
           "subjects": [{"kind": "ServiceAccount", "name": "cleaner", "namespace": env.namespace}]}
    yield {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "Role", "metadata": object_meta(env, role, env.namespace),
           "rules": [{"apiGroups": [""], "resources": ["configmaps"], "verbs": ["get", "list", "create", "patch", "update"]}]}
    yield {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding", "metadata": object_meta(env, role, env.namespace),
           "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": role},
           "subjects": [{"kind": "ServiceAccount", "name": "cleaner", "namespace": env.namespace}]}
    yield {"apiVersion": "v1", "kind": "ConfigMap", "metadata": object_meta(env, "environment", env.namespace),
           "data": {"environment.yml": yaml.safe_dump(asdict(env)), "kubeconfig": yaml.safe_dump({
               "apiVersion": "v1", "kind": "Config", "current-context": "cleaner",
               "clusters": [{"name": "cluster", "cluster": {"server": "https://kubernetes.default.svc",
                   "certificate-authority": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"}}],
               "users": [{"name": "cleaner", "user": {
                   "tokenFile": "/var/run/secrets/kubernetes.io/serviceaccount/token"}}],
               "contexts": [{"name": "cleaner", "context": {"cluster": "cluster", "user": "cleaner"}}]})}}
    yield {"apiVersion": "batch/v1", "kind": "CronJob", "metadata": object_meta(env, "cleanup", env.namespace),
           "spec": {"schedule": "*/5 * * * *", "concurrencyPolicy": "Forbid", "startingDeadlineSeconds": 240,
                    "successfulJobsHistoryLimit": 1, "failedJobsHistoryLimit": 3, "jobTemplate": {"spec": {
                        "activeDeadlineSeconds": 240, "backoffLimit": 0, "template": {"spec": {
                            "serviceAccountName": "cleaner", "restartPolicy": "Never", "nodeSelector": {"drydock-role": "system"},
                            "containers": [{"name": "cleanup", "image": env.cleanup_image,
                                            "command": ["/opt/drydock/bin/python", "-m", "drydock", "--environment", "/environment/environment.yml", "reap"],
                                            "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "1", "memory": "512Mi"}},
                                            "volumeMounts": [{"name": "environment", "mountPath": "/environment", "readOnly": True}]}],
                            "volumes": [{"name": "environment", "configMap": {"name": "environment"}}]}}}}}}


def destroy_infrastructure(env):
    journal_path = env.directory / "ownership.json"
    journal = json.loads(journal_path.read_text())
    if journal["environment"] != asdict(env):
        raise UserError("Environment differs from the ownership record.")
    resources = selected_resources(env, infrastructure_inventory(env))
    if resources["operations"]:
        # A cluster allocation can be accepted before the cluster appears in list responses.
        wait_for(lambda: not selected_resources(env, infrastructure_inventory(env))["operations"], 1800)
        resources = selected_resources(env, infrastructure_inventory(env))
    marker = "drydock:" + env.name
    # Refuse mismatches before deleting any infrastructure.
    for cluster in resources["clusters"]:
        if (cluster.get("resourceLabels", {}).get("drydock-env") != env.name
                or cluster.get("location") != env.zone):
            raise UserError("Cluster ownership or location does not match.")
    for category in ("subnets", "networks", "accounts", "roles"):
        if any(r.get("description") != marker for r in resources[category]):
            raise UserError(f"{category} ownership does not match.")
    save(journal_path, {**journal, "state": "deleting"})
    errors = []
    if resources["clusters"]:
        try:
            if resources["clusters"][0].get("status") != "STOPPING":
                env.gcloud("container", "clusters", "delete", env.name, f"--zone={env.zone}", "--async")
            wait_for(lambda: not any(c["name"] == env.name for c in
                                    json.loads(env.gcloud("container", "clusters", "list"))), 1800)
        except Exception as error:
            errors.append({"resource": "cluster", "error": type(error).__name__})
    # Keep network and identity prerequisites if cluster deletion is incomplete.
    if not errors:
        for category in ("subnets", "networks", "accounts", "roles"):
            for resource in resources[category]:
                try:
                    if category == "subnets":
                        env.gcloud("compute", "networks", "subnets", "delete", env.name, f"--region={env.region}")
                    elif category == "networks":
                        env.gcloud("compute", "networks", "delete", env.name)
                    elif category == "accounts":
                        account = resource["email"]
                        roles = (["roles/container.defaultNodeServiceAccount", "roles/artifactregistry.reader"]
                                 if account.startswith(env.name + "-node@") else
                                 [f"projects/{env.project}/roles/{env.name.replace('-', '_')}", "roles/artifactregistry.reader"])
                        for role in roles:
                            policy = json.loads(env.gcloud("projects", "get-iam-policy", env.project))
                            if any(b["role"] == role and f"serviceAccount:{account}" in b.get("members", [])
                                   for b in policy.get("bindings", [])):
                                env.gcloud("projects", "remove-iam-policy-binding", env.project,
                                           f"--member=serviceAccount:{account}", f"--role={role}", "--all")
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
    result = {"environment": env.name, "deleted": not any(counts.values()) and not errors,
              "remaining": counts, "errors": errors, "observed_at": now()}
    save(env.directory / "cleanup.json", result)
    if result["deleted"]:
        save(journal_path, {**journal, "state": "deleted"})
        (env.directory / "kubeconfig").unlink(missing_ok=True)
    return result
