# GitHub-to-GKE access acceptance

This record covers task 8.2 access acceptance. It does not establish network acceptance.

The latest approved run passed the complete trusted GitHub-to-GKE probe with the configured service account email identity.
It passed ownership reads, all eight Kubernetes denials, and the Google permission boundary through the private endpoint.
Independent inspection confirmed disposable runner removal and disabled federation afterward.
Task 8.2 is complete. Lab execution and network acceptance remain separate tasks.
Earlier sections preserve the prerequisites and incomplete results from their respective test stages.

## Trusted revision

PR #20 merged into protected `main` as `44e6caa176108eb5be62252bf1363678086680e0` on November 13, 2026.
The Google federation provider trusts that exact workflow revision and the immutable environment identity described below.
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

The installed GKE target and controlled dispatcher now supply the required test boundary.
The remaining GitHub test must prove temporary identity exchange and complete the trusted access probe after the merged-script correction.
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
GCE started termination at `2026-11-13T15:37:15Z` after the fixed runtime.
At `15:38:17Z`, inspection found both the VM and its boot disk absent, 963.5 seconds after instance creation.
The observer issued no instance or disk deletion command.
The operator then used the documented recovery command to remove the orphaned registration, scale set, and local SSH keys.
The recovery journal records successful removal.

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

## Immutable GitHub subject

The first trusted exchange attempt failed Google's attribute condition.
GitHub's repository API reported `use_immutable_subject: true` and this prefix:

```text
repo:dlobato@1379455/drydock@1452964696
```

The initial setup used the older name-only subject.
The operator corrected the disabled provider and its sole service-account impersonation binding to:

```text
repo:dlobato@1379455/drydock@1452964696:environment:gke
```

The operator removed the old subject binding and retained every repository, environment, branch, workflow, SHA, and event restriction.
GitHub's immutable subject mode remains enabled.
PR #21 updates the setup, documentation, and regression test for this exact identity.

## Live identity exchange and final state

[Attempt 2 of run 43453975643](https://github.com/dlobato/drydock/actions/runs/43453975643/attempts/2) passed the approved Google OIDC exchange.
The official action issued the requested 900-second token to the dedicated service account.
The private job executed the trusted workflow at `44e6caa176108eb5be62252bf1363678086680e0` and selected PR input `366d48777844cad3cd473cb4195b8411e41dc679`.
No PR code executed.

[Hosted run 43455725603](https://github.com/dlobato/drydock/actions/runs/43455725603) used the temporary test branch without the protected environment.
Google rejected its identity through the provider's attribute condition while the provider was enabled.
The test completed successfully because it required that refusal.
This covers a real untrusted branch, workflow reference, and absent environment together.
The numeric repository and owner restrictions remain pinned and covered by setup tests.

The trusted job's probe then failed because the merged script requests the invalid `container.nodePools.create` permission.
The local live API reproduction returned HTTP 400 for that request.
The corrected permission test passed with the real dedicated account, as recorded above.
This is successful token exchange and target-boundary evidence, not a successful complete GitHub-to-GKE probe.

The dispatcher removed its VM, boot disk, SSH keys, registration, queue session, and scale set.
The operator disabled federation again and retained the exact immutable subject and all other restrictions.
The temporary test branch and synthetic unrelated-resource fixtures were removed.
The shared GKE access target, NAT, private registry, admission service, and cleaner remain provisioned for the post-merge test.
No lab or switch remains allocated.

After PR #21 merges, pin the new reviewed `main` SHA while federation remains disabled.
Start a fresh trusted request with an open same-repository PR as its input.
The final evidence update can supply that PR. A rerun of the old run retains its old workflow revision.
Enable federation only for the approved test and retain the complete successful probe result.
Task 8.2 remains unchecked until that result exists.

Local validation passed 121 Python tests, 32 Node.js selector tests, Go race tests and static analysis, actionlint, pre-commit, and strict OpenSpec validation.
The hosted PR checks also run both offline AVD builds and the six bundle tests.
None of this evidence establishes switch startup, network behavior, MLAG, scale, concurrency qualification, or AWS support.

## Post-merge acceptance request

PR #21 merged into protected `main` as `f0e6061074b301f6aed1776710087cba18d6db07`.
That revision contains the corrected permission probe, immutable subject, and runner guard.
The final access request uses that trusted revision and an exact input commit from this evidence PR.
The operator pinned the disabled provider to that revision without changing its other identity restrictions.

[Run 43471711854](https://github.com/dlobato/drydock/actions/runs/43471711854) selected PR #22 input `977089c87025666ad946cc2745b802dfa09e746e` through manual dispatch on `main`.
The selector passed. Before approval, the access job waited with no assigned runner and no executed steps.
The environment still requires owner review, restricts deployments to `main`, and disables administrator bypass.
GitHub reported no registered private runner. The existing GKE access target remains available.
The provider stayed disabled until approval. No disposable VM or lab existed at that stage.

Local validation passed 121 Python tests, 32 selector tests, Ruff, mypy, Go race tests, Go static analysis, and strict OpenSpec validation.
[Hosted run 43471663989](https://github.com/dlobato/drydock/actions/runs/43471663989) passed both PR jobs, including both offline AVD builds and six bundle tests.
The unmarked PR event skipped its access job. Only the separate manual request required approval.

## Approved probe and denial parsing

The owner approved run `43471711854` through the native `gke` review.
The dispatcher accepted the exact approved attempt before registering its runner or creating its VM.
The root-owned guard accepted the trusted workflow at `f0e6061074b301f6aed1776710087cba18d6db07`.
The official Google action issued the requested 900-second token.
The access step then failed. The complete GitHub probe did not pass.

A local reproduction used the dedicated workflow identity and the operator-authorized public control endpoint with the cluster CA.
Google permissions, Kubernetes identity, and ownership reads passed.
The first permission denial returned exit code 1 and `no - <GKE IAM/RBAC reason>`.
The probe required exactly `no` and rejected that valid denial.

The corrected parser accepts `no` with an optional ` - ` reason and still requires exit code 1.
Regression tests reject empty output, unrecognized output, and excess permissions.
The corrected local probe passed all eight Kubernetes denials and the Google permission boundary.
That local result does not establish execution through the private runner.
No lab was created and no network tests ran.

## Disposal and next request

The dispatcher removed its VM, boot disk, SSH keys, runner registration, queue session, and scale set after the failed run.
Independent Google and GitHub API inspection found no remaining disposable VM, disk, or registered runner.
The VM used a private address, no cloud service account, and a GCE-enforced 900-second deletion deadline.
Provider readback showed federation disabled again with all identity restrictions retained.
The temporary local diagnostic grant was removed. Its token and kubeconfig files were deleted.

The shared GKE access target remains available. No lab or switch was allocated by this request.
Merge the parser correction before selecting a new trusted workflow revision.
Then pin that reviewed `main` SHA while federation is disabled and request a fresh approved probe.
Task 8.2 remains unchecked until that complete trusted run succeeds.

Validation after the correction passed 123 Python tests, 32 selector tests, Ruff, mypy, strict OpenSpec validation, and whitespace validation.

## Pre-merge private endpoint test

The operator tested PR #22 commit `5feb4c1bfe7eb25ff59aebcfc25ec6d2c599b710` before merge.
The unchanged probe had SHA256 `57847dbf75432ad75625a3a00697221c1988b1508301e96556a0f68a606e937b`.
It ran as an unprivileged user on disposable VM `drydock-probe-pr22-8ff443c3300f` in the existing private subnet.
The VM used the same pinned Ubuntu image and preparation script as the approved runner.
No GitHub runner was registered or started.

The probe used the private Kubernetes endpoint and the cluster CA without an endpoint override.
Kubernetes identity, ownership reads, all eight permission denials, and the Google permission boundary passed.
The dedicated workflow account supplied a 900-second diagnostic token through local operator impersonation.
The temporary impersonation grant was removed before execution. The token reached the VM through SSH standard input.
This standalone test did not exercise GitHub OIDC or environment approval.

The VM had no public address or cloud service account and retained a GCE-enforced 900-second deletion deadline.
The operator deleted the VM and its boot disk after the successful test.
Independent API inspection found neither resource. Local token, kubeconfig, and SSH files were removed.
Federation stayed disabled throughout. No lab or switch was allocated.

This result establishes the corrected probe's live behavior through the private endpoint before merge.
Task 8.2 retains the complete GitHub workflow test after the correction reaches the trusted default branch.

## Final trusted workflow request

PR #22 merged into protected `main` as `d3ab11a7cfd486302661e80c217e03e3ad12eee6`.
That revision contains the denial parser that passed the standalone private endpoint test.
This evidence PR supplies an exact input commit for a fresh request on the corrected trusted revision.
The requested probe uses the existing access target and creates no switch lab.

The operator pinned the disabled provider to that reviewed revision without changing its other trust restrictions.
[Run 43480437310](https://github.com/dlobato/drydock/actions/runs/43480437310) selected PR #23 input `645e91e0ccd87dad59896f5cd3e384f0fcec08db`.
Before approval, the private job had no assigned runner or executed steps.
The user approved the complete no-lab test, and the operator recorded native `gke` approval.
The dispatcher authorized the exact request. The root-owned guard accepted the trusted workflow and attempt.

The official Google action issued the requested 900-second token with its default `cloud-platform` scope.
The probe failed at `2026-11-13T18:16:20Z`.
GKE's audit log recorded a successful `selfsubjectreviews.create` request with principal `104795665890363084336`.
The configured Kubernetes username was `drydock-github@drydock-513410.iam.gserviceaccount.com`.
The probe therefore rejected the identity before ownership reads or Kubernetes denial tests.
Google's [GKE authentication documentation](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/api-server-authentication#authenticate_users) requires the `userinfo.email` scope for email identity.

The workflow correction explicitly requests `cloud-platform` and `userinfo.email`.
The regression test fails without the additional scope and passes with both scopes.
The correction changes no IAM grants, Kubernetes bindings, token lifetime, or source trust restrictions.
It must reach protected `main` before another trusted workflow test.
Task 8.2 remains unchecked because this complete GitHub probe failed.

The runner used private address `10.140.0.9`, no cloud service account, and a GCE-enforced 900-second deletion deadline.
The dispatcher removed its VM, boot disk, SSH keys, registration, queue session, and scale set.
Independent Google and GitHub API inspection found no disposable VM, disk, or registered runner.
Provider readback confirmed disabled federation with the reviewed SHA and every other identity restriction retained.
The existing shared access target remains available. No lab or switch was allocated.

Local validation passed all 123 Python tests, 32 selector tests, dispatcher race tests, static analysis, and pre-commit before the workflow correction.
[Hosted run 43480273627](https://github.com/dlobato/drydock/actions/runs/43480273627) passed both PR jobs, including both offline AVD builds and six bundle tests.
The unmarked PR event skipped its private job. Only the separate manual request required approval.

After the scope correction, all 123 Python tests and 32 selector tests pass again.
Actionlint, pre-commit, strict OpenSpec validation, and whitespace validation also pass.

## Email scope acceptance request

PR #23 merged into protected `main` as `5470d057700b8f12f7d92fec8f6e7444065167c5`.
The trusted workflow now explicitly requests `cloud-platform` and `userinfo.email` for its 900-second token.
This evidence PR supplies the exact input for a fresh approved no-lab probe.
The earlier approval covers this corrected attempt and its disposable runner.

[Run 43482680932](https://github.com/dlobato/drydock/actions/runs/43482680932) passed on its first attempt.
It selected PR #24 input `21d8dfcbbd1ba44b9703ff560899fee80a4aa803` before native approval.
The private job had no assigned runner or executed steps while approval was absent.
The dispatcher authorized the exact approved attempt before runner registration or VM creation.
The root-owned guard accepted the trusted workflow at `5470d057700b8f12f7d92fec8f6e7444065167c5`.
No PR code executed in the private job.

The official Google action issued the requested 900-second token with `cloud-platform` and `userinfo.email` scopes.
The GKE audit log recorded `drydock-github@drydock-513410.iam.gserviceaccount.com` for the successful identity request.
The probe passed identity comparison and ownership reads through the private endpoint with the cluster CA.
It required explicit refusal of all eight unrelated Kubernetes operations.
Google allowed only `container.clusters.get` among the requested permissions and denied worker allocation and IAM administration.
The unchanged probe removed its temporary kubeconfig after completion.

The runner used private address `10.140.0.10`, no cloud service account, and a GCE-enforced 900-second deletion deadline.
The dispatcher removed its VM, boot disk, SSH keys, registration, queue session, and scale set.
Independent Google and GitHub API inspection found no disposable VM, disk, or registered runner.
Local inspection found no SSH keys. Provider readback confirmed disabled federation with all claim restrictions retained.
The provider still pins the reviewed workflow SHA. The shared access target remains available.

This result completes task 8.2 together with the earlier target-boundary, approval-denial, unauthorized-workflow, and operator-loss evidence.
No lab or switch was allocated. Tasks 8.3 through 8.5 retain lab orchestration, reports, and workflow acceptance.
Scale, network behavior, MLAG, broader concurrency, published clabernetes compatibility, and AWS remain unqualified by this access test.

All 123 Python tests, 32 selector tests, dispatcher race tests, and static analysis pass on the merged revision.
Pre-commit, actionlint, strict OpenSpec validation, and whitespace validation pass.
