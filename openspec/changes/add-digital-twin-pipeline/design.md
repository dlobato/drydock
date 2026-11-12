# Design

## Context

The [proposal](proposal.md) defines the revised lifecycle boundary.
The existing CLI combines GKE provisioning, a fixed six-switch input, AVD catalog generation, ANTA execution, reports, and lab deletion.
The November 11 demo passed 54 live results and complete deletion on a corrected private clabernetes build.
The [validation record](../../../docs/live-gke-validation.md) retains the exact runtime, MLAG evidence, and remaining limitations.

The November 12 review selects a reusable CLI on an existing clabernetes cluster.
This planning revision does not change executable behavior or demonstrate the new requirements.

## Goals / Non-Goals

Keep lifecycle operations independent of GKE, cloud IAM, AVD internals, and a specific fabric.
Preserve authenticated management readiness, ownership before allocation, private access, and cleanup after partial creation.
Use Kubernetes as the shared state system. No HTTP service, database, or separate queue is selected.

The pipeline owns network acceptance. Readiness ends when the requested infrastructure and management APIs are available.
Worker provisioning, autoscaling, registry authentication, and private routing belong to the platform operator.
Direct Containerlab execution, CloudVision, host containers, and interactive switch access remain excluded.

## Decisions

### Use the Kubernetes boundary

The operator supplies a Kubernetes context, an installed clabernetes backend, registry access, capacity policy, and private runner connectivity.
The lifecycle CLI and independent cleaner operate through Kubernetes without Google project, zone, or AWS account arguments.
Provider-specific authentication prepares temporary Kubernetes access before the CLI runs.
Drydock does not change the active cloud account or global Kubernetes context.

Remove cloud allocation, worker deletion, and Google token refresh from the reusable lifecycle path.
Keep the existing GKE setup as separately documented demo tooling.
A future AWS deployment supplies the same cluster contract through its own operator setup.
This avoids a cloud adapter inside the lifecycle core. AWS support remains unqualified until tested.

### Accept topology data and startup files

A lifecycle request contains an ordinary Containerlab topology, its referenced startup files, and supported auxiliary files such as interface mappings.
Names, links, addresses, and device count come from the topology.
Remove the fixed device set, management subnet, interface map, and exact link pattern from lifecycle admission.
Keep the six-switch fabric as a regression example.

Clabernetes interprets the topology. Drydock does not maintain a second network model.
Admission reads switch identities, the link count, and file references for delivery and lifecycle expectations.
It enforces a documented field allowlist and rejects link references outside the admitted switches.
It does not parse management addresses, EOS startup syntax, or interface mapping contents.
The producer supplies consistent startup files. The example interprets EOS interface mappings only for its ANTA coverage policy.

Copy the admitted topology and change file references, enforced startup delivery, and private eAPI ports.
Keep an empty prefix and set a unique management network name.
Preserve the topology name, defaults, node attributes, address values, and link attributes.
Project referenced files through clabernetes `filesFromSecret` attachments within Kubernetes object limits.
Do not rebuild nodes from a Drydock-owned network model.

The supported device kind is cEOS. Arbitrary topology shape does not permit arbitrary containers or unrestricted Containerlab execution features.
Admission rejects missing files, unsafe paths, unsupported device kinds, execution hooks, arbitrary host mounts, and unsupported attributes before creating workloads.
Support documented file and resource limits. Distribute startup data within Kubernetes object limits for the 100-switch case.
Use approved, digest-pinned cEOS images and operator-supplied registry access without enforcing a Google registry hostname.

The pipeline keeps AVD structured configurations and catalogs beside its test artifacts.
Its build must establish that those configurations match the startup files submitted to Drydock.
Drydock records a digest for the complete admitted lab input but does not render AVD models or interpret ANTA results.
A lifecycle request can come from a producer that does not use AVD.

### Boot the complete proposed configuration

Containerlab can supply arbitrary startup configurations, so switches boot with the complete proposed configuration.
A separate eAPI deployment stage is unnecessary for the initial workflow.
This preserves the reference outcome without carrying ACT's startup limitation into Drydock.

The producer supplies management credentials and HTTPS eAPI configuration suitable for the lab.
Drydock authenticates to each device and compares its reported hostname with the requested identity.
Keep Management1 and eAPI in the intended management VRF. Do not add configuration workarounds to repair backend transport.

### Own one lab per workflow attempt

Create a unique lab ID and durable Kubernetes ownership record before workload allocation.
Record repository, exact commit, workflow run, attempt, input digest, acceptance time, expiry, and requested runtime.
Use a separate namespace for each lab and preserve original switch names in the returned inventory.
The same topology, names, and management addresses can occur in several simultaneous labs.
Network isolation and name preservation require live proof.

Use resource versions to protect state updates and inspect the allocation lease between resource requests.
Expiry or deletion prevents further allocation. A late readiness response cannot restore a deleting lab.
Retain deletion records and revisit them to detect late workloads from interrupted requests.
Deletion operates only on resources whose ownership matches the requested lab.

### Leave capacity with the cluster

The operator configures worker pools, scheduling policy, quotas, and optional autoscaling.
Drydock declares resource requirements for clabernetes workloads and reports scheduling conditions.
It does not create a worker pool for each lab or promise dedicated workers.
The operator can reserve a worker pool for lab workloads without changing the lifecycle interface.

If capacity is unavailable, the lab waits within its startup deadline.
Status distinguishes unavailable capacity from device startup or management failure.
There is no separate Drydock queue. Kubernetes pending workloads provide the waiting mechanism.
The effective deadline cannot exceed expiry, and readiness after either deadline does not make the run successful.
Timeout triggers deletion of partial allocations without preempting other labs.

The first scale target is 100 switches in one lab, with several active labs supported.
This is a qualification target, not a fixed topology size or a claim of unlimited concurrency.
Measure per-switch resource needs, startup duration, and aggregate capacity before publishing supported limits.
Kubernetes resource requests and autoscaling do not guarantee fairness between partially allocated labs.
Deadlines, quotas, and cleanup bound the effect of capacity shortages.

### Return private connection inventory

Require the current topology generation, all requested switch workloads, accepted links, and authenticated management access before reporting readiness.
Discover one current Pod for each original switch identity through Kubernetes.
Reject missing or duplicate endpoints, invalid private addresses, and unexpected EOS hostnames.
Refresh endpoint discovery on readiness attempts and record Pod names and UIDs.

Return JSON containing lab identity, lifecycle state, expiry, input provenance, and connection details for every switch.
The pipeline applies those connection details to its existing Ansible inventory without discarding groups or test variables.
Status and inventory retrieval remain independent of AVD or ANTA execution.
Routing convergence and network test results do not determine infrastructure readiness.

The first transport retains private Pod-IP HTTPS from an external self-hosted runner.
The operator supplies routes to the Kubernetes API and switch endpoints on GKE or the next provider.
The private demo retains its agreed exception for switch TLS certificate verification.
Password authentication and hostname comparison remain required. The exception does not apply to Kubernetes or cloud identity endpoints.
No certificate-based switch identity or hostile-network protection is claimed. Certificate infrastructure is not added by this revision.

### Expire labs independently

Default lifetime is 30 minutes, with a maximum of 60 minutes from acceptance.
Reject nonpositive values and requests above the maximum before allocation.
Capacity waiting, startup, and tests consume the same lifetime. Retries do not renew it.
The pipeline budgets its startup and ANTA deadlines against the remaining lifetime.

The caller requests deletion after success, failure, timeout, or cancellation.
The cluster-side cleaner covers runner loss and starts independently of a GitHub cleanup step.
It runs every five minutes, retries incomplete deletion every five minutes indefinitely, and flags overdue records.
Its Kubernetes identity has the permissions needed for lab cleanup without cloud administration credentials.

Cleanup removes owned workloads, startup Secrets, namespace resources, and other lab-owned objects.
It does not delete cluster workers or wait for cloud scale-down.
Complete lab deletion means that no owned lab resources remain and no allocation can recreate them.
Retained ownership records preserve the outcome without retaining credentials.

Keep the deletion target of 30 minutes after expiry while the Kubernetes API and backend are available.
Expiry starts cleanup. It does not promise that all resources disappear at the expiry instant.
Measure the five-minute discovery delay and complete deletion separately.
Never force-remove finalizers or delete resources with different ownership.

### Keep the pipeline in charge of tests

The workflow builds proposed configurations with standard AVD playbooks before requesting a lab.
It invokes the lifecycle CLI, applies the connection inventory, and runs the standard `arista.avd.anta_runner` playbook.
It retains reports and requests deletion regardless of build, startup, ANTA, report, or upload outcomes after allocation.
The existing integrated test command becomes example orchestration outside the lifecycle core.
Do not preserve a second core test policy or require a compatibility wrapper.

The example retains AVD 6.5.0 and ANTA 1.10.0 as its existing baseline.
The example pipeline establishes startup/model consistency and mandatory coverage before allocation.
It requires routing, EVPN, VXLAN, switch links, and both MLAG pairs for the six-switch fabric.
Other topologies use their pipeline's applicable test policy without inheriting fixed MLAG or fabric assumptions in Drydock.

Pipeline success requires passing required tests, retained reports, and complete lab deletion.
Test and cleanup failures remain separate. A report upload failure does not prevent deletion.
The pipeline retains safe JSON and JUnit reports, catalogs, diagnostics, and lifecycle provenance under a finite retention policy.
It excludes startup files, credential-bearing structured data, Kubernetes credentials, Secret contents, and arbitrary container logs from uploaded artifacts.

### Require a manual, trusted workflow

Use `workflow_dispatch` for all GitHub workflows, including offline builds.
Disable automatic push and pull-request triggers during implementation.
Only the repository owner authorizes a run. Manual dispatch permission alone does not prove owner authorization.
Enforce the allowed actor identity before runner assignment or credential issuance through trusted workflow and identity controls.

Run the workflow definition from the protected default branch and identify the PR input by its exact commit SHA.
Reject a mutable-only ref, an unauthorized actor, or an untrusted workflow revision.
A new PR commit and each rerun require owner authorization for the identified commit.
Rerun authorization uses the triggering actor as well as the original run identity.
Workflow inputs cannot select another privileged workflow or substitute PR code for the installed Drydock CLI.
The trusted workflow uses a pinned lifecycle tool and treats the submitted topology as admitted data.

Use a dedicated self-hosted runner with private connectivity. Prefer a disposable runner for each job.
Separate uncredentialed PR build execution from credentialed lifecycle execution so build processes cannot inherit later credentials.
Run Ansible without Kubernetes credentials. ANTA receives only the lab management credentials and connection inventory.
Use separate disposable execution environments for build, lifecycle, tests, and deletion so background processes cannot cross credential boundaries.
Do not run unapproved PR code on the private runner.
The platform operator owns runner deployment and private networking.
Fork execution remains excluded from the initial trusted workflow.

### Exchange identity for limited credentials

OIDC is an identity token protocol.
For GKE, operator-configured Workload Identity Federation exchanges the trusted GitHub identity for temporary access.
Constrain that trust to the repository, owner actor, and trusted workflow revision.
Use stable numeric identity claims where the provider supports them.
Grant GitHub's `id-token: write` permission only to the credentialed lifecycle jobs.
Do not upload personal Google credentials, service-account keys, or a reusable administrative kubeconfig to GitHub.

Kubernetes RBAC, the API permission system, and operator-installed admission policies enforce the authorized lab boundary.
Namespace prefixes and ownership labels alone do not restrict API access.
The workflow identity cannot administer IAM, allocate workers, change RBAC, or access unrelated resources.
Namespace creation and privileged cEOS workloads must remain inside the operator-enforced lab boundary.
Prove these restrictions before enabling credentialed runs.

The provider handles token exchange and renewal. Drydock consumes the supplied Kubernetes context without cloud-specific login code.
Token validity must cover authorized work and immediate cleanup without extending the lab expiry.
If workflow access expires, the independent cleaner still retains its own Kubernetes cleanup identity.
Keep credentials out of arguments, logs, caches, reports, and uploaded artifacts.
AWS can supply its own temporary authentication setup without a new cloud path in Drydock.

## Risks / Trade-offs

A 100-switch lab and simultaneous labs need capacity measurements. Preserve per-run timing and resource evidence before claiming supported scale.
Privileged cEOS workloads share a cluster. Namespace separation alone does not establish security against hostile tenants.
The operator must enforce the lab boundary and isolate unrelated workloads. This remains a trusted-code workflow.
Temporary credentials can still be used by approved code during their validity period. Limited permissions and exact-commit authorization remain necessary.

Private Pod-IP access depends on operator-supplied routing. A new provider must demonstrate that connection path.
The private switch TLS exception sends credentials without certificate-based identity. Keep this limitation explicit in operator instructions.
Cluster-managed scale-down can retain workers after lab deletion. Lab cleanup does not establish zero cloud cost.
The corrected private clabernetes build does not qualify the official published release or any other runtime combination.

## Migration Plan

This PR updates the plan and project context only. It leaves runtime code, GitHub triggers, and historical evidence unchanged.
Use a skip-CI commit marker when publishing this revision so the current automatic PR workflow does not run without manual launch.
Keep this change active and preserve completed demo tasks as historical evidence.
Replace unfinished demo tasks with explicit tasks for the revised contract.

Later implementation separates GKE setup and ANTA orchestration, updates callers and tests, and replaces the input and lifetime contracts together.
Do not add legacy aliases or fallback paths for the unreleased demo interface.
Update the operator instructions and README alongside each implemented boundary change.
Preserve the original example build, synthetic identities, VNIs 1001 and 1002, peer VLANs 4000 and 4001, and both MLAG pairs.
Keep the cleaner active until all allocated labs are deleted, including failed migration attempts.

## Open Questions

The initial startup deadline and per-switch resource requests require measurements from the 100-switch test.
The evidence will establish the qualified simultaneous lab count and aggregate switch capacity.
The pipeline's finite artifact retention duration remains to select before its first live run.
These values do not change the lifecycle boundary, manual approval requirement, or the 30/60-minute lifetime limits.
