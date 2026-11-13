# GitHub-to-GKE access acceptance

This record covers task 8.2 access acceptance. It does not establish network acceptance.

## Trusted revision

PR #20 merged into protected `main` as `44e6caa176108eb5be62252bf1363678086680e0` on November 13, 2026.
The Google federation provider trusts that exact workflow revision and retains every other identity restriction.
The provider remains disabled.

The `gke` environment requires owner review, disables administrator bypass, and restricts deployments to `main`.
The initial inspection found no GKE cluster, compute instance, or registered private runner.
These observations describe the inspected state, not a deployment guarantee.

## Approval boundary

The marked head of PR #21 requested the merged trusted workflow for exact input `9af7cffc0e218e130da0bb377824ef5985b6f88d`.
[Run 43429024041](https://github.com/dlobato/drydock/actions/runs/43429024041) reached the native `gke` approval gate.
The hosted selector completed before the access job waited for approval.

API inspection recorded the access job with no runner, no runner name, and no executed steps while approval was absent.
The operator then rejected the deployment through GitHub's native review endpoint.
The run and access job ended with the expected failure result.
Final API inspection recorded no assigned runner and no executed steps after rejection.
The authentication action never started. These observations required no private capacity or enabled federation.

The run identifies the PR input separately from the trusted workflow revision on `main`.
No PR code executed in the credentialed job.

## Remaining acceptance

The repository belongs to a personal GitHub account.
An organization runner group with workflow restrictions is not available inside this repository.
Runner labels do not restrict which workflow can request private execution.
The operator must supply an enforced execution boundary before registering private capacity.

## Accepted runner boundary

The user approved the operator-controlled dispatcher on November 13.
The implementation uses the official GitHub scale-set SDK at `v0.5.0`.
It checks authoritative queue identity and native environment review before runner registration or VM creation.
GitHub can route a job to an empty scale set before a runner exists.
Routing remains separate from authorization and private execution.

A root-owned start guard stops unexpected run attempts or workflow revisions before workflow steps.
The guard kills the whole runner process group, including unconditional steps.
This covers cancellation or reassignment while the VM starts.
The operator supplies one disposable VM without a service account or administrative kubeconfig.
GCE enforces a 900-second deletion deadline independently of the operator process.

See [the operator procedure](runner-dispatcher.md) for installation, execution, and recovery.
Live runner authorization and disposal evidence remains required before federation can be enabled.

## Remaining target tests

The remaining tests require a private GKE target, admission installation, and a controlled disposable runner.
They must prove temporary identity exchange, GKE identity mapping, allowed lifecycle operations, and the specified Kubernetes and Google denials.
Task 8.2 remains unchecked until these tests pass.
See [the operator procedure](github-gke-access.md) for the deployment requirements and denial cases.

## Controlled runner evidence

The matching-label branch test used [run 43450512721](https://github.com/dlobato/drydock/actions/runs/43450512721).
The dispatcher rejected its non-main workflow reference before runner registration or VM creation.
GitHub recorded no assigned runner or executed steps. The operator canceled the test afterward.

[Attempt 1 of run 43450817485](https://github.com/dlobato/drydock/actions/runs/43450817485/attempts/1) tested the approved runner path with federation disabled.
The root-owned guard accepted the exact approved attempt and trusted workflow SHA.
The official Google authentication action failed as expected because the provider was disabled.
The dispatcher deleted its VM, SSH keys, runner registration, queue session, and scale set.
Final inspection found no disposable runner or VM.

[Run 43451266506](https://github.com/dlobato/drydock/actions/runs/43451266506) requested identical labels while that approved VM prepared.
It remained queued without a runner or steps throughout the approved execution and disposal.
The operator then canceled it.

The second approved attempt tests operator loss.
The operator hard-stopped only the test dispatcher process group after its VM entered `RUNNING`.
The VM had a private address, no service account, and a GCE-enforced 900-second deletion deadline.
The cloud deadline result remains pending in this record.

## Target GKE boundary evidence

The operator created the `drydock-access` GKE Standard target in `drydock-513410`, zone `europe-west1-b`.
It uses Kubernetes `1.36.4-gke.2377000`, one private node, a dedicated VPC, NAT egress, and an IAP-only SSH rule for runners.
The operator restricts the public control endpoint to the operator's address.
The GitHub probe selects the private endpoint and the cluster CA certificate.

The target contains the real clabernetes CRDs without a controller or switches.
This installation tests API authorization and admission. It does not qualify clabernetes runtime behavior.
The reviewed admission and cleaner image is:

```text
europe-west1-docker.pkg.dev/drydock-513410/drydock-access/admission@sha256:849c92f1c97113eb8bf8384f88dbe9bc168d1fa69c04578e77274ab840b4d73e
```

GKE authenticated the dedicated Google account as `drydock-github@drydock-513410.iam.gserviceaccount.com`.
The operator used a 900-second local impersonation token to establish that mapping.
The temporary impersonation grant was removed. The local token files were deleted after testing.
No operator credential entered a GitHub job or private runner.

All 18 actual GKE API cases passed:

- RBAC denied unrelated Secret and Pod reads, permission escalation, and privileged Pod creation.
- Admission denied unrelated namespace creation, host containers, execution hooks, host mounts, and per-node images.
- Admission denied external payloads, arbitrary Secret references, public exposure, and expiry extension.
- The generated Topology and startup payloads were accepted with the real CRD defaults.
- Two cluster-side cleaner sweeps removed the owned namespace and retained the unrelated namespace and synthetic Secret.
- Repeated caller deletion succeeded. Stopping admission caused restricted requests to fail closed.

The running admission source matched all five inspected source files in this checkout.
Google's `testIamPermissions` allowed only `container.clusters.get`.
It denied cluster creation, deletion and updates, compute and disk creation, service-account impersonation, and IAM administration.
These checks used the dedicated account's real access token.

## Merged probe correction

The live cloud check found two prerequisites missing from the original setup.
The Cloud Resource Manager API must be enabled for `testIamPermissions`.
Also, `container.nodePools.create` is not a valid permission for that request.
GKE node-pool changes use `container.clusters.update`.
The corrected probe also tests `compute.instances.create` for direct VM allocation.
PR #21 supplies both corrections and their regression tests.

The final successful GitHub probe requires that correction on protected `main`.
The credentialed job must continue to execute the reviewed default-branch revision.
Executing the amended PR script in that job would break the source trust boundary.
Keep task 8.2 unchecked until the corrected trusted workflow passes the complete probe.
