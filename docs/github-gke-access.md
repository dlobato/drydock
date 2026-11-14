# GitHub access to GKE

Task 8.2 adds temporary authentication and an enforced lab boundary.
This setup belongs to the cluster operator. Lifecycle commands do not administer Google IAM or Kubernetes permissions.
OIDC lets GitHub prove a workflow identity without a stored key.
Google Workload Identity Federation exchanges that identity for temporary access.

The federation setup script creates a disabled provider and a dedicated Google service account.
A service account represents an automated caller.
It grants only `container.clusters.get` for cluster discovery.
The script does not grant worker allocation, IAM administration, or Kubernetes access.
It enables the Cloud Resource Manager API for the permission probe without granting additional permissions.
Keep the provider disabled until the Kubernetes boundary and trusted workflow pass their denial tests.

## Create the disabled provider

Use the operator's existing authenticated Google Cloud CLI profile.
Never copy that profile or its credentials into GitHub.
The script targets `dlobato/drydock`, repository ID `1452964696`, and owner ID `1379455`.
Use a separate reviewed configuration for another repository.

Set the existing project and the reviewed workflow commit on protected `main`:

```sh
export DRYDOCK_PROJECT=drydock-513410
export DRYDOCK_WORKFLOW_SHA=<40-character-reviewed-commit-on-main>
bash examples/github/configure-federation.sh
```

This is an initial setup script. It stops if a named resource already exists.
It does not adopt existing resources or replace their permissions.
After a partial failure, inspect the created resources before continuing the remaining commands.

For an existing setup, enable the permission probe's API with the isolated operator profile:

```sh
gcloud services enable cloudresourcemanager.googleapis.com --project="$DRYDOCK_PROJECT"
```

The provider requires all these GitHub claims:

- The numeric repository and owner IDs match this repository.
- The subject is `repo:dlobato@1379455/drydock@1452964696:environment:gke`.
- The branch is `refs/heads/main`.
- The workflow is `.github/workflows/pre-deployment.yml` on `main`.
- The workflow commit matches the operator-approved SHA.
- The event is `workflow_dispatch`. The PR metadata event can only dispatch that workflow.

The subject requires the protected environment. Omitting that environment changes the subject and prevents federation.
This repository uses GitHub's [immutable subject format](https://docs.github.com/en/actions/reference/security/oidc#immutable-subject-claims), which includes numeric owner and repository IDs.
Inspect `gh api repos/dlobato/drydock/actions/oidc/customization/sub` before setup.
Its `sub_claim_prefix` must match `repo:dlobato@1379455/drydock@1452964696` and `use_immutable_subject` must be true.
A PR workflow, fork, other branch, or changed workflow commit fails the same condition.
Keep owner review and disabled administrator bypass on the `gke` environment.
Restrict environment deployments to `main`, as described in [the workflow instructions](workflows.md#protect-the-environment).

The service account accepts impersonation only from that pool's exact environment subject.
The pool must contain only this reviewed provider.
Do not grant project-wide token creation or add another provider with weaker trust.

## Establish the Kubernetes boundary

Kubernetes RBAC is its API permission system.
RBAC must allow lifecycle operations without granting Secret reads, permission changes, or direct workload creation.
Admission must restrict namespace mutations, startup Secret creation, and Topology creation to the selected lab environment.
The cleaner needs its own restricted namespace deletion policy and ownership-record permissions.

Clabernetes stores its Containerlab definition as a YAML string.
Native Kubernetes admission expressions cannot parse that string to enforce Drydock's switch-only rules.
Namespace prefixes and labels alone cannot prevent an unsafe Topology from creating privileged workloads.
An admission webhook accepts or rejects Kubernetes API requests.
The operator installs a TLS admission webhook that reuses Drydock's topology validation.
The webhook accepts only approved cEOS digests, complete projected startup files, and private HTTPS exposure.
It rejects execution hooks, host containers, host mounts, external payloads, arbitrary Secret references, and deployment overrides.
It also protects namespace ownership, accepted expiry, and cleanup state.

The admission service gives the workflow read access through a binding in each owned lab namespace.
A RoleBinding grants API permissions within a namespace.
A background loop creates those bindings from durable ownership records.
The validating request itself changes no resources, including during an API dry run.
The first payload request waits up to five seconds for its reader binding.
A missing or conflicting binding prevents allocation.
The workflow receives no permission to create or change bindings.

The service uses Python's standard HTTP and TLS libraries with the existing PyYAML dependency.
It reads ownership records and namespace metadata without reading startup Secrets.
Its operator identity can bind only the generated reader role.
This identity and the clabernetes controller remain trusted cluster components.
This design does not establish isolation against hostile privileged cEOS tenants.

### Install admission

Install the independent cleaner first, using [the lifecycle procedure](lifecycle.md#install-the-independent-cleaner).
Its connection template must exist in the system namespace.
The admission Pod uses that template with its own mounted service-account token.
It receives no cloud credentials.

Set these operator values:

- `DRYDOCK_KUBECONFIG` and `DRYDOCK_CONTEXT` select the target cluster.
- `DRYDOCK_SYSTEM_NAMESPACE` is the lifecycle environment name plus `-system`.
- `DRYDOCK_GKE_USERNAME` is the exact username that GKE authenticates for the dedicated account.
- `DRYDOCK_CLEANUP_IMAGE` identifies the reviewed lifecycle image by digest.
- `DRYDOCK_CEOS_IMAGE` identifies an operator-approved cEOS image by digest.

Use an image built from this revision with the existing `Dockerfile.cleaner`.
The same minimal image supplies the admission command.
Do not assume that a service account email and numeric ID are interchangeable Kubernetes usernames.
Compare `kubectl auth whoami -o json` with the installed subject before enabling execution.

An OAuth scope selects the identity information or APIs available to a token.
Request both `cloud-platform` and `userinfo.email` scopes for the temporary workflow token.
GKE needs `userinfo.email` to identify the account by its email address.
The default Google action scope supplied a numeric account ID during the live probe.
That identity did not match the configured email or its Kubernetes permissions.
See [Google's GKE authentication requirements](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/api-server-authentication#authenticate_users).

The following certificate is private to this webhook.
A certificate authority (CA) signs certificates that identify services.
Kubernetes trusts its public certificate through the webhook's `caBundle` field.
This does not change switch TLS behavior or Kubernetes client verification.
Create its files in an ignored, restricted directory:

```sh
umask 077
mkdir -p artifacts/admission
openssl req -x509 -newkey rsa:2048 -nodes -days 90 \
  -keyout artifacts/admission/tls.key -out artifacts/admission/tls.crt \
  -subj "/CN=admission.${DRYDOCK_SYSTEM_NAMESPACE}.svc" \
  -addext "subjectAltName=DNS:admission.${DRYDOCK_SYSTEM_NAMESPACE}.svc" \
  -addext "extendedKeyUsage=serverAuth" \
  -addext "basicConstraints=critical,CA:TRUE"
kubectl --kubeconfig "$DRYDOCK_KUBECONFIG" --context "$DRYDOCK_CONTEXT" \
  create secret tls admission-tls -n "$DRYDOCK_SYSTEM_NAMESPACE" \
  --cert=artifacts/admission/tls.crt --key=artifacts/admission/tls.key
.venv/bin/python -m drydock.access --environment artifacts/lifecycle.yml \
  --image "$DRYDOCK_CLEANUP_IMAGE" --username "$DRYDOCK_GKE_USERNAME" \
  --ceos-image "$DRYDOCK_CEOS_IMAGE" --ca-certificate artifacts/admission/tls.crt \
  > artifacts/admission/access.json
kubectl --kubeconfig "$DRYDOCK_KUBECONFIG" --context "$DRYDOCK_CONTEXT" \
  apply -f artifacts/admission/access.json
kubectl --kubeconfig "$DRYDOCK_KUBECONFIG" --context "$DRYDOCK_CONTEXT" \
  rollout status deployment/admission -n "$DRYDOCK_SYSTEM_NAMESPACE" --timeout=120s
```

Repeat `--ceos-image` for each additional approved digest.
The renderer installs the webhook before granting permissions.
Until its service becomes ready, API mutations from the restricted identities fail.
The service uses one replica and a ten-second admission timeout.
The operator retains responsibility for availability and certificate rotation.

Renew the certificate before its 90-day expiry.
First install a `caBundle` that contains both old and new public certificates.
Then replace the TLS Secret and restart the admission Deployment.
After the new Pod becomes ready, remove the old certificate from `caBundle`.
Keep the private keys out of manifests, reports, logs, and GitHub.
If admission is unavailable or its certificate expires, restricted mutations stop, including cleaner deletion requests.
Restore admission before resuming lab work. Never bypass it to make a workflow pass.

## Rotate or revoke trust

Before changing the trusted workflow revision, disable the provider:

```sh
gcloud iam workload-identity-pools providers update-oidc pre-deployment \
  --project="$DRYDOCK_PROJECT" --location=global \
  --workload-identity-pool=drydock-github --disabled
```

Inspect the new workflow on protected `main`.
Replace only the SHA restriction in the existing attribute condition.
Retain every repository, environment, branch, workflow, and event restriction.
For task 8.3, also narrow the allowed event to `workflow_dispatch` when installing the reviewed workflow revision.
Repeat the denial tests before enabling the provider.

Disabling federation prevents new exchanges. Existing access tokens remain usable until they expire.
Restrict issued Google access tokens to 900 seconds and request fresh approval for each credentialed job.
Keep token issuance inside environment-approved jobs and outside Ansible execution.
The independent cleaner must retain its separate Kubernetes identity if workflow access expires.

## Scoped access acceptance

The approved trusted workflow passed [the complete no-lab access probe](live-github-gke-access.md#email-scope-acceptance-request) on November 13, 2026.
The result includes email identity, ownership reads, Kubernetes denials, and the Google permission boundary.
Federation is disabled again, and independent inspection confirmed disposable runner removal.
Repeat the following procedure for a new target or trusted workflow revision.

The task 8.2 workflow used a temporary-access probe without PR code or lab allocation.
That record remains the evidence for scoped access and denials.
Task 8.3 replaces the probe with [isolated lab orchestration](workflows.md#isolated-pipeline-execution).
The coordinator uses the reviewed workflow commit and treats the selected PR as uncredentialed container input.
After `gke` approval and successful preflight, the official Google action prepares temporary federation.
The lifecycle containers renew 900-second access through Google Cloud CLI and preserve the cluster CA certificate.
The PR build and ANTA containers receive no federation file or GitHub token endpoint.
Complete live workflow acceptance remains task 8.5.
The initial implementation required a new GKE access target and controlled private execution.
Use [the operator dispatcher](runner-dispatcher.md) to supply one approved disposable runner with Python 3 and kubectl.
Its labels must include `self-hosted`, `linux`, `x64`, and `drydock-gke`.
Labels only route jobs. They do not authorize private execution.
The platform operator must enforce trusted-workflow assignment outside PR-controlled YAML before registering private capacity.
Do not register an unrestricted persistent repository runner.
The absence of a private runner leaves an approved probe queued without granting credentials.

Set these nonsecret variables on the protected `gke` environment:

| Variable | Value |
|---|---|
| `GKE_WORKLOAD_IDENTITY_PROVIDER` | The provider resource printed by the setup script |
| `GKE_SERVICE_ACCOUNT` | `drydock-github@drydock-513410.iam.gserviceaccount.com` |
| `GKE_CLUSTER_RESOURCE` | `projects/<project>/locations/<location>/clusters/<cluster>` |
| `GKE_PIPELINE_IMAGE` | The reviewed pipeline toolchain image, pinned by digest |
| `DRYDOCK_CEOS_IMAGE` | The approved cEOS image, pinned by digest |
| `DRYDOCK_ENVIRONMENT` | The existing lifecycle environment name, such as `drydock-demo` |

The coordinator generates its lab password. The operator supplies switch image access through the existing cluster.
The trusted credentialed workflow must reach protected `main` before a live federation test.

Before enabling lab execution, retain evidence for these cases:

- An absent or rejected environment approval prevents runner assignment and token issuance.
- A valid approved identity receives temporary credentials without a personal key.
- Invalid repository, environment, branch, and workflow claims fail federation.
- The workflow identity cannot read an unrelated Secret or change Kubernetes permissions.
- Google IAM denies worker allocation and IAM administration.
- Kubernetes rejects unsafe topology inputs and direct workload creation.
- The allowed lifecycle path succeeds and the independent cleaner retains separate access.

After the trusted workflow reaches `main`, update the disabled provider's SHA condition to that exact reviewed revision.
Enable it only after the target cluster's permissions, admission, and private runner controls pass their tests.
Then request the probe through the marker or manual path and approve it through GitHub.
Never merge or relax trust merely to satisfy a live test.

Local API tests establish the recorded Kubernetes boundary, not GKE identity mapping or GitHub token exchange.
Keep task 8.2 unchecked until the approved GitHub-to-GKE probe and denial scenarios pass.
