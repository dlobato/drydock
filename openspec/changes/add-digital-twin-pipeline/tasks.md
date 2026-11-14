# Tasks

The November 12 planning revision records the lifecycle-only requirements.
The November 13 workflow decision requires automatic PR lint and unit tests and opt-in GKE tests with native environment approval.
Sections 1 through 5 retain completed work from the earlier GKE demo.
Task 6.1 records the first revised implementation and its offline and live evidence.
Tasks 6.2 and 6.3 record topology admission, ownership isolation, and their offline evidence.
Task 6.3 also records bounded live ownership and two-lab isolation evidence.
Task 6.4 records registry admission, offline tests, and bounded live image-access acceptance.
Task 7.1 records bounded startup waiting and controlled capacity and timeout evidence.
Task 7.2 records authenticated runtime inventory and controlled endpoint replacement evidence.
Task 7.3 records the 30-minute default, 60-minute maximum, and controlled expiry evidence.
Task 7.4 records the Kubernetes-only cleaner, image build, and controlled cleanup recovery evidence.
Task 7.5 records standalone command acceptance and complete lab removal on a bounded local private runtime.
Task 8.1 records automatic PR checks, an opt-in approval placeholder, and native environment protection.
Task 8.2 records scoped federation, admission, approved disposable runners, and complete live GitHub-to-GKE access acceptance.
Task 8.5 records bounded live workflow acceptance, inspected uploaded reports, and independent lab deletion.
Section 9 retains the remaining scale, concurrency, failure, and provider qualification.

The former open demo tasks are replaced without claiming their completion:

| Former task | Replacement scope |
|---|---|
| 3.7: Concurrent isolation and expiry | 7.4, 9.2, and 9.3 |
| 4.1: GitHub orchestration | 8.1 through 8.5 |
| 4.5: Artifact upload and future automatic triggers | 8.1 and 8.4. PR checks are automatic. GKE tests remain opt-in. |
| 5.2: Live failure paths | 9.3 |
| 5.3: Complete scenario review | 9.4 |

## 1. Establish the implementation baseline (historical demo)

- [x] 1.1 Record the agreed startup delivery, CLI, AVD catalog ownership, external runner, and manual infrastructure lifetime in `design.md`.
- [x] 1.2 Record the separate MLAG investigation outcome and exact tested private runtime. Retain evidence for both pairs without the experimental rule.
- [x] 1.3 Document the finite lab expiry, cleanup cadence, retry policy, deletion target, and operator-owned infrastructure lifetime.

## 2. Build the anonymized example (historical demo)

- [x] 2.1 Add the six-switch AVD inventory with synthetic names, addresses, and identifiers. Demonstrate two spines and two MLAG pairs in generated output.
- [x] 2.2 Add pinned AVD dependencies and build commands. Demonstrate a clean build with AVD 6.5.0 without source repository access.
- [x] 2.3 Supply lab credentials at runtime. Inspect retained build output to establish that it contains no source identity or authentication material.
- [x] 2.4 Produce the complete switch-only Containerlab topology and configuration bundle. Demonstrate matching device identities, links, and a recorded bundle digest.
- [x] 2.5 Document the example build and test boundary. Run the documented commands from a clean checkout and compare the topology with the reference behavior.
- [x] 2.6 Bundle matching AVD structured configurations and enable HTTPS eAPI for the lab. Exercise actual `anta_runner` catalog generation offline.
- [x] 2.7 Restore the reference VRF VNIs and MLAG peer VLANs. Rebuild both example variants and test legal VLAN numbers, reference values, and the primary MLAG interface.

## 3. Implement the lab lifecycle (historical demo)

- [x] 3.1 Add request validation and durable ownership records. Test missing configurations, unsupported devices, invalid expiry, and distinct workflow attempts before allocation.
- [x] 3.2 Add creation on dedicated temporary GKE workers and clabernetes. Use controlled tests to cover partial allocation and interrupted updates.
- [x] 3.3 Add status and private connection inventory output. Test an unreachable management API and original device identity preservation.
- [x] 3.4 Add repeatable deletion. Test already deleted resources, provider failure, and preservation of other labs and shared infrastructure.
- [x] 3.5 Implement independent expiry, indefinite retry, overdue records, pending operation discovery, and token renewal. Test the behavior with controlled provider responses.
- [x] 3.6 Exercise the documented lifecycle and infrastructure commands in an authorized development environment, including the cleaner image build and repeated deployment.
- [x] 3.8 Replace port forwarding with private Pod-IP discovery for status, readiness, ANTA, and diagnostics. Test missing or duplicate Pods, private addresses, hostname mismatch, replacement Pods, and failure cleanup.

## 4. Deliver the CLI and later GitHub integration (historical demo)

- [x] 4.2 Invoke `anta_runner` for bounded acceptance and require generated routing, EVPN, VXLAN, switch-link, and both MLAG-pair coverage. Test missing, skipped, errored, duplicate, and failed results.
- [x] 4.3 Retain local JSON, JUnit, generated catalogs, lifecycle events, and available diagnostics with provenance. Test report write failure without blocking deletion.
- [x] 4.4 Add immediate cleanup and separate test and cleanup outcomes. Test that deletion failure prevents success without hiding an ANTA failure.

## 5. Prove the milestone (historical demo)

- [x] 5.1 Record the completed separate cold-start experiment for the exact private runtime. Retain its 54 results, both MLAG pairs, authenticated endpoints, conformance result, and complete deletion.
- [x] 5.4 Run the actual single-command CLI acceptance on the corrected private runtime. Require all 54 results, saved reports, and complete deletion. Prove standalone create/status/delete on the existing cluster and independently inspect cleanup.

## 6. Separate the lifecycle core

- [x] 6.1 Move GKE setup and integrated ANTA orchestration outside the lifecycle core. Update callers, dependencies, and command documentation. Demonstrate lifecycle use without AVD, ANTA, or cloud administration access.
- [x] 6.2 Generalize admission without a second network model. Preserve admitted topology fields, inspect only lifecycle identities and safe file references, and delegate network semantics to clabernetes. Keep EOS interface interpretation in the example. Update documentation and test different fabrics, topology preservation, unsafe inputs, and payloads split within Kubernetes limits.
- [x] 6.3 Preserve unique attempt ownership and namespace isolation before allocation. Test competing updates, late creation, repeated input, and deletion that preserves another lab. Document the ownership record and failure output.
- [x] 6.4 Replace Google registry token handling with operator-supplied Kubernetes image access. Demonstrate a digest-pinned image outside Google Artifact Registry. Document the cluster prerequisites and keep authentication setup outside the core.

## 7. Deliver bounded lifecycle operations

- [x] 7.1 Add capacity waiting, scheduling diagnostics, and a startup deadline bounded by expiry. Test capacity arrival, exhaustion, late readiness, and partial cleanup. Document statuses without adding a separate queue.
- [x] 7.2 Derive authenticated readiness and connection inventory from all submitted switches and links. Test endpoint replacement, duplicate Pods, credential rejection, hostname mismatch, and different device names. Document private routing and runtime inventory use.
- [x] 7.3 Set the lifetime default to 30 minutes and the maximum to 60 minutes from acceptance. Test invalid values, capacity waiting, and retries that cannot renew expiry. Update CLI help and operator examples together.
- [x] 7.4 Make the independent cleaner and deletion path Kubernetes-only. Test five-minute retries, overdue cleanup, late resources, interruptions, and unrelated-resource preservation. Document complete lab deletion independently of worker scale-down and cloud cost.
- [x] 7.5 Exercise the documented standalone creation, readiness, inventory, status, and repeated deletion commands. Demonstrate JSON outcomes and complete removal of lab-owned resources. Keep the switch TLS exception explicit and preserve verification for Kubernetes endpoints.
- [x] 7.6 Replace optional demo ANTA results after every completed invocation, including empty results. Test that acceptance uses the current attempt and preserves diagnostics if invocation raises.
- [x] 7.7 Skip completed cleanup records with absent namespaces using one namespace list per cleaner sweep. Test bounded API work, expired-lab cleanup, and late namespace discovery while preserving deletion ownership guards.
- [x] 7.8 Clear the overdue flag after successful deletion. Test repeated deletion after the cleanup deadline and retain overdue status for incomplete cleanup.

## 8. Integrate automatic PR checks and opt-in lab tests

- [x] 8.1 Run hosted lint and unit tests automatically on every PR and update without custom author restrictions or cloud approval. Replace custom actor authorization with a separate opt-in PR test request and native `gke` environment protection. Document both paths. Use the user-authorized hosted placeholder to test approval without cloud access or lab allocation. Test fork eligibility, exact-commit selection, trusted workflow revisions, absence of GKE jobs on PR events, and the environment gate before placeholder execution. Leave live private-execution denial evidence in tasks 8.2 and 8.5.
- [x] 8.2 Document and configure temporary GKE authentication through GitHub OIDC federation bound to the approved `gke` environment and trusted workflow outside the lifecycle core. Deliver scoped RBAC and admission policy for the lab boundary. Deliver the approved operator-controlled dispatcher with queue authorization before runner registration and an independent execution guard and disposable private runners. Prove unauthorized-workflow denial and bounded runner disposal. Demonstrate denial before approval and denial of unrelated Secret access, RBAC changes, cloud worker allocation, and unsafe workloads without personal keys.
- [x] 8.3 Connect the standard AVD build and ANTA playbooks through the lifecycle CLI and runtime connection inventory. Isolate Ansible from Kubernetes credentials and use a pinned trusted CLI. Test model consistency, mandatory coverage, preserved inventory groups, and cleanup after each failure stage.
- [x] 8.4 Select a finite artifact retention duration and retain safe reports with exact input provenance. Test upload failure without blocking deletion. Inspect final artifacts for credentials, startup files, and sensitive structured data. Document report paths and cleanup outcomes.
- [x] 8.5 Exercise automatic PR lint and unit tests plus a separate opt-in pre-deployment request with native `gke` approval. Demonstrate temporary access, complete test reports, and lab deletion. Show that a new unmarked PR commit runs its checks without starting another GKE test, inheriting approval, or reusing a previous lab.

- [x] 8.6 Add `[digital-twin-test]` in the latest PR commit as an explicit request through a trusted metadata-only PR trigger. Preserve hosted checks and native environment approval. Retain the placeholder without cloud access or NRFU. Test exact-marker matching, absent markers, stale events, fork exclusion, fixed commits, and API failures. Document that the trusted trigger must reach `main` before its first live approval test.

## 9. Qualify scale and concurrency

- [ ] 9.1 Exercise one 100-switch lab through creation, authenticated readiness, pipeline-run ANTA, and deletion within its accepted lifetime. Record exact runtime, resource requests, startup duration, and cleanup timing. Set the startup deadline from evidence without extending the 60-minute maximum.
- [ ] 9.2 Exercise several concurrent labs with repeated switch names and management addresses. Delete and expire individual labs while the others continue. Record simultaneous lab count, aggregate switch count, and network acceptance for the surviving labs.
- [ ] 9.3 Exercise live failure, capacity timeout, cancellation, expired workflow credentials, and runner loss. Retain safe partial evidence and independently inspect lab resource deletion. Measure expiry discovery and complete cleanup against the documented target.
- [ ] 9.4 Compare the revised implementation with every specification scenario and review the final operator instructions. Exercise the lifecycle interface with a non-GKE Kubernetes test context. Separate interface evidence from additional live provider qualification, and keep untested AWS or runtime combinations unqualified.

## Lifecycle separation evidence (task 6.1)

The lifecycle CLI uses an explicit Kubernetes context without importing cloud setup or AVD and ANTA orchestration.
The optional demo commands live under `examples.demo`.
The lifecycle bundle contains topology, startup files, and the interface mapping without AVD models.
The example retains model consistency and mandatory network coverage before allocation.
Creation, deletion, and expiry no longer call cloud APIs or handle Google registry tokens.
The operator supplies worker capacity and image access.

An isolated Python 3.13.9 environment contains only pip and PyYAML 6.0.3.
All 19 lifecycle tests pass there without installed AVD, ANTA, or Ansible.
They exercise the actual CLI with controlled Kubernetes and eAPI responses.
Cases include creation, authenticated status, repeated deletion, failed allocation cleanup, and expiry.
All 42 offline regression tests and six bundle tests pass.
The actual AVD role generates all 54 expected dry-run results with both MLAG pairs covered.
Both example builds, dependency consistency, and strict OpenSpec validation pass.
The November 12 live follow-up also passed standalone creation, authenticated status, inventory retrieval, invalid-password rejection, deletion, and repeated deletion.
The lifecycle image contained no AVD, ANTA, Ansible, or Google Cloud CLI.
The separate demo passed all 54 required results with both MLAG pairs, retained reports, and complete lab deletion.
Both cases reused one cluster and its shared switch workers.
An abandoned two-minute lab also expired independently. A scheduled cleaner job confirmed complete deletion 355 seconds after expiry without cloud credentials.
All three cases preserved the cluster identity, worker pools, and an unrelated namespace and Secret.
The [live validation record](../../../docs/live-gke-validation.md) identifies the tested commit, private runtime, and authorization limits.

Broader registry admission and image-access qualification remain task 6.4.
The remaining cleanup qualification stays in task 7.4.
Task 6.2 removes the six-switch admission limit.
Task 7.3 replaces the earlier lifetime values with a 30-minute default and a 60-minute maximum.
The [lifecycle instructions](../../../docs/lifecycle.md) document those limits and the transition from earlier demo deployments.

## Topology admission evidence (task 6.2)

Admission reads expected switch names, link count, and safe file references from the submitted topology.
It preserves admitted topology fields and delegates management address and interface semantics to clabernetes.
Startup and mapping contents remain opaque to the lifecycle core. The example owns EOS interface interpretation for ANTA coverage.
It retains the switch-only restriction and rejects unsupported execution features, unsafe paths, missing files, and oversized resources before allocation.
Startup and mapping files use bounded Secrets with distinct generated file keys.
Ownership records retain switch names and link counts for the existing status operation.

Offline cases cover one, three, five, and 100 switches, including custom mappings and different management subnets.
A synthetic 100-switch input spans multiple Secrets and preserves every startup and mapping file.
Each Secret contains at most 512 KiB of decoded data, and each serialized workload manifest fits within 1 MiB.
The CLI cases exercise creation, authenticated status, repeated deletion, safe input errors, and cleanup after interrupted Secret creation.

The existing native Ansible playbook still generates the example through `arista.avd.eos_designs` and `arista.avd.eos_cli_config_gen`.
The initial revision passed both example builds. The topology-preserving revision passes six bundle tests and all 53 offline regression tests.
Pinned Ruff and mypy hooks and strict OpenSpec validation pass.
The actual AVD role still generates all 54 expected dry-run results with both MLAG pairs covered.
This evidence does not establish live startup of other fabrics, 100-switch capacity, concurrency, or another provider.
Tasks 6.4, 7.2, and section 9 retain their remaining image access, readiness, and live acceptance work.

## Ownership isolation evidence (task 6.3)

Each creation request records an allocation ID before namespace or workload creation.
The standalone CLI and optional demo pass that ID to cleanup after failed creation.
An ID collision cannot authorize cleanup of an earlier request.
Namespace labels must match the record for status and deletion.
Deletion sends the observed Kubernetes object ID and resource version as API preconditions.

Controlled tests cover repeated input, preserved resources in another lab, competing updates, late namespace creation, and expiry without renewal.
They also cover namespace replacement, changed labels, lost ownership responses, and unconfirmed ownership without disclosing provider output.
All 64 offline regression tests pass, including the actual AVD role and its 54 expected catalog results.
Pinned Ruff and mypy hooks and strict OpenSpec validation pass.
A localhost HTTP test confirms that the actual `kubectl` command sends both deletion preconditions.

The [lifecycle instructions](../../../docs/lifecycle.md#ownership-and-failure-output) describe ownership records, JSON failure output, and earlier-deployment cleanup.
The November 12 live follow-up used two concurrent six-switch labs with identical input and request provenance.
Both labs passed authenticated readiness and all 54 required ANTA results, including both MLAG pairs.
Deleting one lab preserved the survivor's Pod identities and its next 54 results.
An eight-minute replacement lab also expired without a caller deletion request.
The independent cleaner removed its namespace within 263 seconds after expiry and confirmed complete deletion within 516 seconds.
The survivor kept its original Pod identities and passed another 54 results after expiry cleanup.
All seven live ANTA runs passed, with 378 successful results and both MLAG pairs covered in each run.
Independent reads found every lab namespace absent and all seven ownership records deleted before shared teardown.
The final cloud inventory found zero owned resources across 15 categories and preserved the project and baseline resources.
Live API cases also passed collision protection, stale updates, lost ownership responses, namespace ownership refusals, deletion preconditions, and late namespace cleanup.
Namespace race cases used empty test namespaces and controlled failure injection.
The [live validation record](../../../docs/live-gke-validation.md) states the tested source, private runtime, capacity, and operator registry retries.
This evidence covers two simultaneous six-switch labs. It does not qualify larger concurrency, live scale, or another runtime or provider.
Task 7.4 records controlled cleanup evidence below. Tasks 9.2 and 9.3 retain concurrency and live failure qualification.

## Registry admission evidence (task 6.4)

The lifecycle CLI accepts digest-pinned cEOS image references without a Google registry hostname restriction.
It preserves the submitted image reference in the clabernetes topology and ownership record.
The ownership record identifies Docker Hub as `docker.io` when the image reference omits an explicit registry.
The cluster operator supplies image access for controller metadata reads and switch workloads in each new namespace.
The lifecycle CLI does not obtain registry tokens or create registry credentials.

Controlled CLI cases cover GHCR, Quay, a registry with a port, localhost, and two implicit Docker Hub forms.
Each case passes creation, authenticated status, deletion, and repeated deletion with controlled Kubernetes and eAPI responses.
All 65 offline regression tests and six bundle tests pass.
The actual AVD role still generates all 54 expected dry-run results with both MLAG pairs covered.
Pinned Ruff and mypy hooks and strict OpenSpec validation pass.

The November 12 live follow-up used a private, authenticated TLS registry outside Google Artifact Registry.
Anonymous and wrong-password requests failed. All six switches ran the submitted digest-pinned cEOS image.
The minimal lifecycle image passed creation, authenticated status, wrong-password rejection, deletion, and repeated deletion.
A separate ANTA container without Kubernetes credentials passed exactly 54 required results, including both MLAG pairs.
The operator supplied namespace credentials before switch preparation and corrected worker certificate trust during startup.
Registry and Kubernetes TLS verification remained enabled. The lab retained its original lifetime.
Independent reads found the lab namespace absent and unrelated resources preserved before shared teardown.
A fresh cloud inventory then found zero owned resources across 15 categories and preserved all baseline resources and the project.
Temporary access files were removed, and the default kubeconfig remained unchanged.
The [live validation record](../../../docs/live-gke-validation.md#november-12-registry-independent-images) identifies the tested source, private runtime, and operator prerequisites.
This evidence does not qualify other registry authentication methods, automatic recovery after late credentials, scale, or another runtime or provider.
The [lifecycle instructions](../../../docs/lifecycle.md#prepare-the-cluster) describe the required operator setup and late-credential limits.

## Bounded startup evidence (task 7.1)

Creation records a startup deadline at acceptance, bounded by the accepted expiry.
Allocation and readiness use that deadline without renewal by retries.
The standalone `lab wait` command distinguishes scheduling capacity, infrastructure startup, and management failure.
Status and demo diagnostics name unschedulable Pods without retaining raw scheduler messages.
The first successful authenticated observation records `ready_at` through a version-protected ownership update.
Late readiness cannot establish success or overwrite a newer deletion state.
Timeout, cancellation, and observation failures request cleanup and retain its separate outcome.
The optional demo also deducts allocation time from its readiness budget.

All 76 offline regression tests and six bundle tests pass.
Controlled CLI cases cover capacity arrival, exhaustion, expiry, late authentication, interrupted allocation, cancellation, and incomplete deletion.
They also cover cleaner retries, unchanged deadlines, and preservation of another lab during partial cleanup.
Both example builds, pinned Ruff and mypy hooks, and strict OpenSpec validation pass.
The actual AVD role generates all 54 expected dry-run results with both MLAG pairs covered.
The [lifecycle instructions](../../../docs/lifecycle.md#create-and-inspect) document the commands, statuses, and deadline behavior.

This evidence does not establish live capacity recovery, scheduling behavior, cleanup timing, or a suitable deadline for 100 switches.
Tasks 7.5 and 9.1 through 9.3 retain live lifecycle, scale, concurrency, and failure qualification.

## Authenticated inventory evidence (task 7.2)

The standalone `lab inventory` command uses the same authenticated readiness gate as status and wait.
It returns every submitted switch under its original name with its private address, namespace, Pod name, and Pod UID.
The ownership record supplies switch identities and link counts without requiring AVD models.
Readiness rejects missing resources, unaccepted links, stale plans, and missing or duplicate Pods.
It also rejects unreachable management APIs, incorrect credentials, and unexpected hostnames without exposing response contents or passwords.

After authentication, readiness re-reads Kubernetes state and requires unchanged endpoints and current infrastructure before success.
If a Pod changes during authentication, the observation fails without recording readiness or returning the stale connection inventory.
The next attempt discovers and authenticates to the replacement endpoint.
Deletion that starts during authentication also prevents success after an earlier ready observation.

All 83 offline regression tests and six bundle tests pass.
The actual AVD role generates all 54 expected dry-run results with both MLAG pairs covered.
Both example builds, pinned Ruff and mypy hooks, and strict OpenSpec validation pass.
The [runtime inventory instructions](../../../docs/lifecycle.md#use-runtime-connections) document private routing, returned fields, and use with an existing Ansible inventory.

These controlled tests do not establish live replacement behavior, scale, concurrency, or provider compatibility.
Task 7.5 and section 9 retain live lifecycle and qualification work.
The private switch TLS exception remains explicit. Kubernetes certificate verification remains enabled.

## Lifetime evidence (task 7.3)

Lifecycle creation and the optional demo default to 30 minutes and reject lifetimes above 60 minutes before allocation.
The accepted record fixes expiry at acceptance plus the requested lifetime.
Capacity waiting, startup, status observations, and retries preserve that expiry.
The demo defaults to 900 seconds for readiness and 600 seconds for ANTA, with five minutes left before expiry.
The CLI help and operator examples use the same limits.

All 86 offline regression tests and six bundle tests pass.
Controlled CLI cases cover the default, one-minute and 60-minute requests, and invalid lifetimes before ownership creation.
Direct API cases also reject booleans, fractional values, strings, and `None`.
Capacity arrival and repeated waits preserve acceptance and expiry, and another wait at expiry fails and requests deletion.
The demo accepts its default budgets and rejects invalid lifetimes or combined deadlines that exhaust the lifetime before allocation.

Both example builds, pinned Ruff and mypy hooks, and strict OpenSpec validation pass.
The actual AVD role generates all 54 expected dry-run results with both MLAG pairs covered.
The [lifecycle instructions](../../../docs/lifecycle.md#create-and-inspect) document lifetime selection and expiry.
The [demo instructions](../../../docs/demo-flow.md#build-and-run-the-example) document its shorter readiness budget.

These controlled tests do not establish live expiry timing, cleaner recovery, scale, or provider compatibility.
Task 7.4 records controlled cleanup evidence below. Task 7.5 and section 9 retain live qualification work.

## Kubernetes cleanup evidence (task 7.4)

The reusable cleaner generator consumes the lifecycle environment and a digest-pinned image without GKE fields.
The operator can render its Kubernetes manifests with `python -m drydock.cleaner` before installation.
The optional GKE setup reuses those manifests and adds its system-node selector outside the core.
The cleaner image uses Python 3.13 slim and upstream kubectl without Google Cloud CLI.
Its mounted Kubernetes token and CA certificate remain the only runtime identity.
Deletion records its first attempt and the latest outcome observation without deleting workers or measuring cloud cost.

All 93 offline regression tests and six bundle tests pass.
Controlled CLI sweeps retry at five-minute intervals beyond the overdue deadline, preserve another lab, and clear overdue status after success.
Interrupted deletion recovers before expiry whether Kubernetes accepted the deletion request or not.
A namespace with finalizers remains incomplete, and a failed ownership guard does not block cleanup of another lab.
Existing tests retain coverage for late namespaces, competing allocation, replaced namespaces, and completed cleanup history.
Both example builds, pinned Ruff and mypy hooks, and strict OpenSpec validation pass.

The local image build uses Python digest `sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90`.
Its kubectl v1.36.0 stage uses digest `sha256:63e5e76b746bb8b891a94968d380736c035e768dab0d56ddad1f50c750a4be39`.
The built image passes all 70 lifecycle tests with networking disabled and only the tests mounted read-only.
A separate container smoke test passes manifest generation, CLI help, and kubectl execution without cloud tools or credentials.
The [cleaner installation procedure](../../../docs/lifecycle.md#install-the-independent-cleaner) documents permissions, scheduling, retries, and cleanup observations.

The offline tests do not measure live CronJob scheduling, runner-loss recovery, or the 30-minute deletion target.
Tasks 7.5, 8.2, and section 9 retain live command acceptance, enforced authorization policy, and runtime qualification.

The November 13 [focused live cleanup test](../../../docs/live-cleanup-validation.md) adds evidence for Kubernetes 1.36.4 with the same executable source.
Two native CronJob sweeps ran exactly 300 seconds apart.
Live namespace fixtures passed interruption recovery, overdue retries, late-resource discovery, ownership preservation, repeated deletion, and cleanup timestamp assertions.
The cleaner used its mounted Kubernetes identity with CA verification and no cloud tools.
Independent observations found all fixture namespaces absent before the temporary local cluster and kubeconfig were removed.
Default access configuration remained unchanged, and no cloud resources were provisioned.
These results do not qualify clabernetes deletion, real switch workloads, GKE, or the broader live acceptance tasks.

## Standalone lifecycle evidence (task 7.5)

The November 13 [standalone lifecycle test](../../../docs/live-lifecycle-validation.md) used executable source `ad434368e4693031245f345808487c569605f204` on local Kubernetes 1.36.4.
Two real cEOS switches with synthetic startup files passed creation, authenticated readiness, status, inventory retrieval, deletion, and repeated deletion.
Each command returned JSON with the expected exit code. Wrong and missing credentials prevented readiness.
The external runner retained original switch names and current Pod identities without AVD, ANTA, Ansible, or cloud tools.
Readiness took 97.9 seconds from acceptance, and deletion took 47.5 seconds without changing the accepted lifetime.

The agreed switch certificate exception remained explicit. Kubernetes rejected an unrelated CA, and registry access retained certificate verification.
Independent API reads found all lab namespaces and workloads absent while baseline namespaces and cluster nodes retained their identities.
Ownership records retained successful deletion outcomes for the accepted lab and rejected input fixtures.
The temporary infrastructure and credentials were removed without changing default access configuration or provisioning cloud resources.
All 93 offline regression tests and strict OpenSpec validation pass.

This evidence covers the recorded private runtime and two-switch lifecycle behavior only.
It does not qualify the official release, cloud providers, 100-switch scale, concurrent labs, or the pipeline authorization policy.
No network acceptance or MLAG test ran in this task. Section 8 and section 9 retain their separate implementation and qualification work.

## Historical demo evidence

The following record describes the earlier demo, including its dedicated GKE workers and integrated ANTA command.
It does not qualify the revised lifecycle-only contract, current lifetime limits, scale target, or provider independence.

See [the operator instructions](../../../docs/demo-flow.md) for commands, coverage, reports, and limits.
The implementation PR records the exact local gates and their outcomes.
See [the live validation record](../../../docs/live-gke-validation.md) for historical lifecycle results and the separate successful runtime experiment.
Incomplete live tasks remain unchecked.

The November 11 correction restores reference VRF VNIs 1001 and 1002 and peer VLANs 4000 and 4001.
Both offline builds and all five bundle tests passed.
The corrected bundle passed admission and generated 54 expected ANTA results in dry-run mode.
The original diagnostic artifacts remain unchanged.

The later November 11 source correction passed all 54 live results and both MLAG pairs without an EOS firewall exception.
The exact tested runtime used GKE `1.36.4-gke.2377000`, engineering EOS `4.36.1F-48405728.4361F`, and fork chart `0.0.0`.
The private record retains source provenance and the exact image digest. It does not qualify the published release.
The experiment also passed all six authenticated endpoints and focused Make conformance with the race detector.
Independent inventory found zero owned resources across fifteen infrastructure categories, and the existing project remained active.
The separate experiment used a private harness.
The subsequent actual CLI run passed all 54 required results with exact expected multiplicity.
JSON and JUnit reports, generated catalogs, and Pod identities remain in private evidence.
Standalone create, authenticated status, invalid-password rejection, delete, and repeated delete also passed.
Independent observations found no namespace, worker pool, or pending operation for either lab or the preceding failed lab.
Cluster identity and creation time remained unchanged across retries and both successful lifecycles.
The existing AVD playbook enables privileged mode through `anta_enable` for generated ping tests.
All 38 offline CLI tests passed in the recorded demo validation.
The cleaner image build and repeated deployment evidence, together with the standalone lifecycle, complete task 3.6.
Earlier live evidence includes repeated infrastructure deployment, cancellation and timeout cleanup, and runner-loss expiry cleanup in 376 seconds.
Those observations remain partial historical evidence. Tasks 9.2 and 9.3 require fresh concurrency and failure-path qualification.

## Audit follow-up evidence (tasks 7.6 through 7.8)

Task 7.6 passes all seven offline ANTA tests, including actual AVD catalog generation.
The controlled invocation sequence rejects empty current results after an earlier attempt returned successful rows with a failed process status.
An invocation timeout still preserves the last available diagnostics.
The pinned AVD role already rejects zero-test runs, so this fix adds defensive handling rather than proving a live pipeline false pass.
Task 7.7 passes all 63 lifecycle tests.
Three retained completed records add no individual API operations while an expired lab still completes deletion.
A subsequent sweep makes two list calls, writes no records, and retains all cleanup history.
Existing tests still cover late namespaces, competing allocation, replacement namespaces, ownership mismatches, and unrelated-lab preservation.
Task 7.8 passes all 64 lifecycle tests.
Repeated deletion after the cleanup deadline keeps a completed record free of the overdue flag.
Failed cleanup remains overdue until a later successful retry clears the flag.
The final follow-up passes all 88 offline regression tests, six bundle tests, strict OpenSpec validation, and the pinned Ruff and mypy hooks.
These follow-up tests do not add live runtime qualification.
Task 7.4 records broader controlled cleanup evidence above. Task 7.5 retains live command acceptance.

## Historical manual-only workflow evidence (former task 8.1)

The following evidence records the earlier manual-only policy.
The November 13 decision supersedes that policy with automatic PR checks and optional, environment-approved GKE tests.
The initial planning revision reopened task 8.1 because the earlier workflow code did not implement the revised policy.
The implementation evidence below supersedes that earlier workflow without adding cloud access.

The offline workflow accepts only manual dispatch for an exact PR head commit.
Every job requires the original owner ID, triggering owner, and workflow reference on protected `main` before runner assignment.
The authorization job runs trusted code from the workflow commit on a hosted runner.
It rejects forks, closed PRs, changed heads, unprotected defaults, and mismatched identities or workflow revisions.
The separate build uses the approved SHA and read-only repository permissions without retained checkout credentials.
Every job repeats the owner condition because failed-job reruns can reuse a successful authorization job.
The authorization summary identifies the input commit, workflow commit, repository, run, and attempt.

All 25 Node.js authorization tests and 96 Python regression tests pass.
The Python cases exercise the actual job conditions, including refusal of unauthorized failed-job reruns.
Both example builds, six bundle tests, actionlint 1.7.12, pinned Ruff and mypy hooks, and strict OpenSpec validation pass.
The [workflow instructions](../../../docs/workflows.md) document launch, rerun, and trust requirements.

No GitHub Actions run or cloud allocation occurred during this task.
The shipped workflow uses hosted runners without private access or lab allocation.
A modified branch workflow can remove its own guard.
Tasks 8.2 and 8.3 retain platform restrictions on private runners, temporary credentials, isolated execution, and the pinned lifecycle tool.
Task 8.5 retains live workflow acceptance.

## Automatic PR checks and opt-in approval evidence (task 8.1)

The user authorized implementation and an approval-only placeholder on November 13.
PR opening, reopening, and update events now start hosted lint and unit jobs without custom actor restrictions.
Eligible fork PRs use the same jobs under GitHub's native execution policies.
These jobs run the offline builds and tests without private runners, cloud credentials, or environment approval.

A separate manual workflow accepts one PR number from protected `main`.
Its selector records the exact open same-repository PR head, trusted workflow commit, run, and attempt before requesting approval.
The hosted placeholder depends on that selection and references `gke` before execution.
It executes no PR code and has no repository token permissions or cloud access.
Its summary explicitly records that no lab was created and no network tests ran.
New PR commits start automatic checks without another GKE request or an inherited approval.
The selected commit remains fixed within the waiting approval job.

The repository's `gke` environment now requires reviewer `dlobato`, allows self-review, and disables administrator bypass.
Its selected-branch policy contains one branch rule for `main` and no tag rules.
API readback confirms these rules. No environment credentials or cloud resources were added.
The [workflow instructions](../../../docs/workflows.md) cover automatic checks, environment configuration, and manual approval tests after merge.

All 18 Node.js selection tests, 97 Python regression tests, and six bundle tests pass.
Both offline AVD builds, actionlint 1.7.12, pinned Ruff and mypy hooks, strict OpenSpec validation, and local link targets pass.
Tests cover immutable selection, invalid input, untrusted workflow revisions, fork eligibility for hosted checks, and the separate environment boundary.
No manual workflow was dispatched. The new manual definition must reach `main` before its first launch.
Live approval enforcement, temporary GKE access, private-runner denial, and network acceptance remain in tasks 8.2 through 8.5.

## Commit-marker request evidence (task 8.6)

The user selected `[digital-twin-test]` and retained the hosted placeholder until live integration is complete.
The trusted `pull_request_target` workflow reads the current event commit through GitHub's API without executing PR code.
The exact, case-sensitive marker in the head commit subject or body requests `gke` approval.
Unmarked heads, earlier markers, stale events, and fork PRs request no approval.
The existing manual request remains available. Hosted lint and unit jobs remain independent.

All 32 Node.js selection tests and 97 Python regression tests pass.
Actionlint, Ruff, mypy, strict OpenSpec validation, and local link targets pass.
The existing `gke` environment still requires owner review with administrator bypass disabled.
API inspection found only `example-build.yml` on `main` before publication of this change.
The new trusted trigger must reach `main` before a marker commit can test its live approval flow.
No live marker-triggered approval, cloud allocation, or NRFU result is claimed by this implementation evidence.

## Workflow follow-up

- Continue tasks 8.2 through 8.5 as separate authentication, integration, report, and live acceptance work.
- Keep the change active until the revised implementation, scenario evidence, and review are complete.
- Archive and inspect the archived specifications only after the project acceptance requirements are satisfied.

## Scoped access implementation evidence (task 8.2, acceptance incomplete)

The user authorized the required changes in the existing Google project and approved a small admission webhook.
The operator setup creates a disabled federation provider and a dedicated service account with only `container.clusters.get`.
The provider pins numeric repository identities, the protected environment subject, branch, workflow, event, and exact workflow commit.
No personal key is stored in GitHub.
The two nonsecret provider and service-account variables are configured on `gke`.

The requested workflow now performs an environment-approved, no-lab access probe on a controlled private runner.
Only that job can request a 900-second token. It executes no PR code and removes its temporary kubeconfig.
Scoped RBAC denies Secret reads, permission changes, and direct workload creation.
The operator-installed TLS webhook reuses topology validation and enforces namespace ownership, approved images, safe payloads, expiry, and cleanup state.
A separate reconciliation loop gives readiness reads only in owned namespaces.

Local Kubernetes 1.36.4 accepted generated topology with the real private-runtime CRD defaults.
Actual API calls denied unrelated Secret and Pod reads, permission escalation, privileged Pods, and unrelated namespace creation.
Admission denied host containers, execution hooks, host mounts, per-node images, external payloads, arbitrary Secret references, public exposure, and expiry extension.
The independent cleaner removed the owned lab and preserved the unrelated namespace and Secret.
Repeated caller deletion passed. Stopping admission made restricted API requests fail closed.
The running source hashes matched the checkout.
All 115 Python regression tests, 32 Node.js selection tests, and six bundle tests pass.
Both offline AVD builds, actionlint, Ruff, mypy, strict OpenSpec validation, and whitespace validation pass.

The project had no GKE cluster or registered private runner during this implementation.
The trusted workflow must reach protected `main` before its token exchange can be exercised.
Federation remains disabled. No live GitHub token exchange, private-runner authorization, GKE identity mapping, or network acceptance is claimed.
An auxiliary operator impersonation probe was denied. Its temporary token-creation grant was removed and the final policy was inspected.
Google permission denial remains a required live probe outcome, rather than a claim from the configured role alone.
Task 8.2 remains unchecked until that approved target-cluster test and its denial scenarios pass.
See [the operator instructions](../../../docs/github-gke-access.md) for installation and remaining acceptance steps.

## Live approval denial evidence (task 8.2, acceptance incomplete)

PR #20 merged into protected `main` as `44e6caa176108eb5be62252bf1363678086680e0`.
The disabled federation provider now pins that revision and retains all other claim restrictions.
Provider readback confirms that federation remains disabled.

PR #21 requested the access probe through its marked head commit.
The native `gke` gate held the access job without a runner or executed steps while approval was absent.
The operator rejected that deployment. Final API inspection found no runner or executed credential steps after rejection.
The expected failed run establishes rejection enforcement, not a successful access probe.
See [the live access record](../../../docs/live-github-gke-access.md) for the exact run and selected input.

No GKE cluster, compute instance, or registered private runner existed at inspection.
The personal repository cannot supply an organization runner group with workflow restrictions.
The user approved the operator-controlled dispatcher. Its implementation and live tests continue below.
Task 8.2 remains unchecked. GKE identity mapping, token exchange, and cloud denial evidence remain unperformed.

## Controlled private execution and target boundary (task 8.2, acceptance incomplete)

The user approved the operator-controlled disposable runner dispatcher.
The implementation uses GitHub's official scale-set SDK, one approved job per process, and no warm capacity.
It inspects queue identity and native review before registration or VM creation.
A root-owned guard stops unexpected attempts and workflow revisions before any workflow steps, including unconditional steps.
Runner VMs receive no cloud service account or operator credential.
GCE enforces a 900-second deletion deadline. Operator recovery preserves unrelated resources.

Live run `43450512721` proved matching-label workflow refusal before registration or VM creation.
The first approved attempt of run `43450817485` passed the guard and disposed its VM, keys, registration, and scale set.
Federation was disabled, so its authentication failure was expected.
Concurrent untrusted run `43451266506` received no runner or steps.
The operator-loss test also passed. GCE independently removed the VM and boot disk after its fixed runtime.
The documented recovery command then removed its orphaned GitHub registration, scale set, and local keys.

The isolated GKE `drydock-access` target passed 18 actual API boundary cases with real workflow and cleaner tokens.
These cases include unsafe Topology requests, unrelated reads, privilege escalation, expiry protection, independent cleaner execution, and unavailable admission.
The generated safe Topology was accepted. No controller or switch started.
The dedicated identity received only `container.clusters.get` in the live Google permission test.
Worker allocation, impersonation, and IAM administration were denied.
The temporary operator impersonation grant and local token files were removed.

Live testing found that the merged probe requests the invalid `container.nodePools.create` permission.
This PR replaces it with `container.clusters.update` and adds a direct compute allocation denial.
The setup also enables the Cloud Resource Manager API that the permission probe requires.
The final successful GitHub probe must wait for this correction on protected `main`.
Task 8.2 remains unchecked. No PR code runs in the credentialed job to bypass that requirement.
See [the live record](../../../docs/live-github-gke-access.md) for the target, runs, and evidence limits.

The live exchange also exposed GitHub's immutable subject format for this repository.
The disabled provider and sole impersonation binding now use `repo:dlobato@1379455/drydock@1452964696:environment:gke`.
The old name-only binding was removed. No other identity restriction was relaxed.
The setup and regression tests now require that exact immutable subject.

Attempt 2 of run `43453975643` passed the official Google exchange for a 900-second token on the trusted workflow SHA.
Untrusted hosted run `43455725603` was rejected by the enabled provider's attribute condition.
The trusted probe then failed at the merged script's invalid permission request.
The dispatcher removed all private runner resources and the operator disabled federation again.
The shared access target remains available for the corrected post-merge test.
No active lab or switch remains.

Local validation passed 121 Python tests, 32 selector tests, Go race tests and static analysis, actionlint, pre-commit, and strict OpenSpec validation.
Task 8.2 remains unchecked at 36/44 overall because the complete corrected trusted probe requires the fix on protected `main`.
Start a fresh request after merge with an open same-repository PR, rather than rerunning the old workflow revision.

## Corrected post-merge probe attempt (task 8.2, acceptance incomplete)

PR #21 merged as `f0e6061074b301f6aed1776710087cba18d6db07`.
The operator pinned the disabled provider to that exact trusted revision and requested run `43471711854` with PR #22 as input.
Before owner approval, the access job had no assigned runner or executed steps.
After native approval, queue authorization, the runner guard, and the official 900-second Google token exchange passed.
The access probe failed. A local reproduction showed that the parser rejects valid GKE denials with an explanatory reason after `no`.

The parser now accepts that denial format while requiring exit code 1.
Regression tests reject empty or unrecognized output and excess permissions.
The corrected local probe passed all eight Kubernetes denials and the Google permission boundary with the dedicated workflow identity.
It used the operator-authorized public control endpoint with the cluster CA, so it does not establish private-runner completion.

The dispatcher removed its VM, disk, SSH keys, runner registration, queue session, and scale set.
Independent API inspection found no disposable VM, disk, or registered runner.
Federation is disabled again. The temporary local diagnostic grant and credential files were removed.
No lab or switch was allocated by this request.
Task 8.2 remains unchecked until the parser correction reaches protected `main` and a fresh approved trusted probe passes.
See [the live access record](../../../docs/live-github-gke-access.md#approved-probe-and-denial-parsing) for the exact result and disposal evidence.
Validation after the correction passed 123 Python tests, 32 selector tests, Ruff, mypy, strict OpenSpec validation, and whitespace validation.

## Pre-merge private probe evidence (task 8.2, workflow acceptance incomplete)

The unchanged access probe from PR #22 commit `5feb4c1bfe7eb25ff59aebcfc25ec6d2c599b710` passed on an operator-controlled private VM before merge.
The recorded script SHA256 is `57847dbf75432ad75625a3a00697221c1988b1508301e96556a0f68a606e937b`.
The probe used the private Kubernetes endpoint with the cluster CA and the dedicated workflow identity.
Identity, ownership reads, all eight Kubernetes denials, and the Google permission boundary passed.
The operator supplied a 900-second diagnostic token and removed its temporary impersonation grant before execution.

The test registered no GitHub runner and left federation disabled throughout.
The VM had no public address or cloud service account and used the existing 900-second deletion deadline.
Independent API inspection found no VM or boot disk after deletion. Local credential and SSH files were removed.
No lab or switch was allocated.
Task 8.2 remains unchecked because this standalone test does not exercise the complete corrected GitHub workflow.
See [the pre-merge result](../../../docs/live-github-gke-access.md#pre-merge-private-endpoint-test) for the exact execution and evidence limits.

## Workflow token identity correction (task 8.2, acceptance incomplete)

PR #22 merged as `d3ab11a7cfd486302661e80c217e03e3ad12eee6`.
The user approved the complete no-lab test for PR #23.
The operator pinned disabled federation to that revision and requested run `43480437310` for input `645e91e0ccd87dad59896f5cd3e384f0fcec08db`.
Native approval, queue authorization, the runner guard, and the official 900-second token exchange passed.
The probe then failed the Kubernetes identity comparison.
GKE's audit record identified the caller by its numeric account ID instead of the configured email.

The Google action's default scope omitted `userinfo.email`, which GKE requires for email identity.
The workflow now requests that scope alongside `cloud-platform` without changing IAM grants or Kubernetes permissions.
The regression test fails without the scope and passes with it.
The corrected workflow must reach protected `main` before the next approved GitHub probe.

The dispatcher removed all disposable runner resources.
Independent API inspection found no runner VM, boot disk, or GitHub registration.
Federation is disabled again with every trust restriction retained. No lab or switch was allocated.
Task 8.2 remains unchecked at 36/44 tasks complete.
See [the live request record](../../../docs/live-github-gke-access.md#final-trusted-workflow-request) for the exact failure and cleanup evidence.
All 123 Python tests and 32 selector tests pass after the correction.
Actionlint, pre-commit, strict OpenSpec validation, and whitespace validation pass.

## Complete scoped access acceptance (task 8.2)

PR #23 merged as `5470d057700b8f12f7d92fec8f6e7444065167c5` with both required token scopes.
Approved run `43482680932` passed the complete trusted workflow for PR #24 input `21d8dfcbbd1ba44b9703ff560899fee80a4aa803`.
Native approval, queue authorization, the runner guard, and the official 900-second token exchange passed.
GKE authenticated the dedicated service account by its configured email.
The private-endpoint probe passed ownership reads, all eight Kubernetes denials, and the Google permission boundary.
No PR code executed, and no lab or switch was allocated.

The dispatcher removed its VM, disk, keys, registration, queue session, and scale set.
Independent inspection found no disposable VM, boot disk, or GitHub runner. Local inspection found no SSH keys.
Federation is disabled again with the reviewed SHA and all other claim restrictions retained.
The shared access target remains provisioned.

This completes task 8.2 with the earlier live unsafe-workload denials, unauthorized-runner refusal, native approval denial, and operator-loss disposal evidence.
Overall progress is 37/44 tasks complete.
Tasks 8.3 through 8.5 retain lab orchestration, report handling, and complete workflow acceptance.
Section 9 retains scale, concurrency, failure, and provider qualification.
See [the successful access record](../../../docs/live-github-gke-access.md#email-scope-acceptance-request) for exact provenance and evidence limits.

All 123 Python tests, 32 selector tests, dispatcher race tests, and static analysis pass on the merged revision.
Pre-commit, actionlint, strict OpenSpec validation, and whitespace validation pass.

## Isolated AVD and ANTA orchestration evidence (task 8.3)

The trusted workflow now connects the selected PR build, preflight, lifecycle CLI, runtime inventory, standard ANTA playbook, and deletion.
The PR metadata event dispatches the trusted workflow without executing PR code or assigning private capacity.
The dispatch selector rejects a changed head before native approval. The selected commit remains fixed after approval starts.
Each stage uses a separate restricted container. Only lifecycle stages receive refreshable federation.
The CLI writes a new recovery identity file before allocation. Recovery deletion requires its allocation ID.
The connection overlay retains both MLAG groups and the source test variables.

All 157 Python tests and 33 selector tests pass.
Controlled cases cover build, preflight, allocation, readiness, ANTA, report, cancellation, and deletion failures.
Caller identity tests cover lost ownership responses, existing identity files, and recovery that preserves a different allocation.
Dispatcher race tests, static analysis, actionlint 1.7.12, pre-commit, strict OpenSpec validation, and whitespace validation pass.

The new Dockerfile builds locally from digest-pinned Python, kubectl, and Google Cloud CLI images.
The actual restricted containers build the six-switch example and generate all 54 required catalog entries, including both MLAG pairs.
A changed model fails preflight. A test container cannot read the synthetic host credential canary, GitHub token endpoint, or Docker socket.
The real SDK helper also passes a synthetic exchange against local fake identity endpoints with a 900-second lifetime and both required scopes.
These tests use no cloud credentials and allocate no lab or switch.

The workflow uploads no artifacts in this increment and removes its temporary files after deletion attempts.
Task 8.4 retains safe report retention. Task 8.5 retains complete approved GitHub-to-GKE execution and network acceptance.
The operator must supply the reviewed toolchain image and a usable clabernetes target before that live test.
No federation, cluster, runner registration, or cloud resource was changed during task 8.3.
Overall progress is 38/44 tasks complete. The change remains active.

## Safe report retention evidence (task 8.4)

The trusted workflow collects reports after immediate deletion and its unconditional retry.
It uploads only the separate public directory and retains the artifact for seven days.
Collection or upload failure prevents workflow success without blocking either deletion attempt.
The final unconditional step removes private input, credentials, and local reports after upload failure.

The reports identify the exact PR commit, trusted workflow commit, run, attempt, input digest, lab, and available runtime versions.
They retain safe ANTA JSON, JUnit, catalogs, stage diagnostics, and separate initial and latest deletion outcomes.
Description hashes preserve distinct result identities without retaining free text.
JUnit case names remain distinct when one switch has several tests of the same class.
The collector excludes startup files, models, recovery tokens, raw logs, and credential-bearing fields.
It rejects linked or oversized source files and scans the final upload bytes for credentials.

All 162 Python tests, six bundle tests, and 33 selector tests pass.
Both offline AVD builds, pinned pre-commit hooks, actionlint, and strict OpenSpec validation pass.
Controlled tests inspect final report files and exercise upload failure after actual coordinator deletion with a controlled backend.
They also cover partial build evidence, stale upload removal, and missing, duplicate, skipped, or errored results.

The existing local toolchain image builds the synthetic example inside the restricted build and preflight containers.
Its immutable local image ID is `sha256:0f5d2988fbcef7004e1d67186c7ca79ef10ec2d06454602acfb4d017655bb853`.
The offline harness permits that local image ID instead of a registry digest reference.
Production still requires the reviewed registry digest reference.
The collected ZIP contains 11 approved files and excludes the generated password and its hash.
All six sanitized catalogs parse with ANTA and preserve all 54 required entries, including both MLAG pairs.
The dry-run results remain unaccepted as network evidence.

No cloud credentials, cloud resource changes, lab allocation, or live network tests occur in this validation.
Task 8.5 retains the approved hosted upload and complete GitHub-to-GKE workflow acceptance.
Overall progress is 39/44 tasks complete. The change remains active.

## Live pipeline acceptance (task 8.5)

The first November 14 attempt stalled before private workflow execution and was canceled.
The dispatcher correction maintains queue polling and acknowledges the selected message during VM preparation and execution.
The first retry confirmed that correction and passed all 54 required network tests, but report collection rejected spaces in the EOS version.
It uploaded no artifact and did not complete acceptance.
[PR #28](https://github.com/dlobato/drydock/pull/28) fixed that separate report boundary and merged into protected `main`.

The fresh owner-approved [run 43592511128](https://github.com/dlobato/drydock/actions/runs/43592511128) passed with trusted revision `33774b867491e88636397924f1345baa5a816331`.
It tested PR input `5626f17e853bf6a226b415509f40b2784dc58a6e` in `lab-84ce30d51d84`.
All 54 required ANTA results passed, including both MLAG pairs, and both caller deletion stages succeeded.
Independent Kubernetes reads established complete lab deletion.
The downloaded seven-day artifact matched GitHub's digest and all manifest hashes.
Its 11 files retained six valid catalogs, 54 passing JUnit cases, exact provenance, runtime versions, and safe diagnostics.
Credential and private-file inspection passed, and the EOS labels retained their spaces.
The unmarked input update passed hosted lint and tests while its metadata workflow skipped GKE without another approval or runner.
The accepted live attempt required separate dispatch and fresh native review.
The [acceptance record](../../../docs/live-github-pipeline.md) retains exact identities, earlier failures, validation, and cleanup evidence.
Task 8.5 is complete at 40/44 tasks. The change remains active for section 9.

## Scale preparation for task 9.1

The pipeline adds an explicit `scale-100` selection for two spines and 49 MLAG pairs.
The trusted helper expands a private copy of the existing synthetic inventory.
The default selection still requires exactly six switches.
Catalog generation and safe reports cover every switch in the selected fabric.
Native approval, isolated containers, lifecycle ownership, and unconditional deletion remain required.
The dispatcher accepts only the two reviewed fabric names in the approved job identity.

The actual restricted containers built 100 switches, admitted all 294 links, and generated 1,088 required ANTA entries offline.
All 100 sanitized catalogs parsed with ANTA, and the final safe directory contained 105 files.
Missing MLAG coverage for the last leaf failed acceptance preparation.
The 168 Python tests, six bundle tests, 33 selector tests, dispatcher race tests, and static analysis passed.
Pinned repository hooks, actionlint, and strict OpenSpec validation passed.

The [qualification plan](../../../docs/scale-qualification.md) records the proposed resource ceiling, evidence, approval boundary, and cleanup.
Read-only inspection found the shared cluster available and the E2 quota insufficient for the current 100-switch resource requests.
The proposed worker pool uses four private N2 workers within the observed regional quota.
No scale lab, cloud capacity, or temporary trust change is authorized by this preparation alone.
Task 9.1 remains unchecked at 40/44 tasks until live network acceptance and complete deletion pass.

## Rejected scale capacity request (task 9.1)

The user approved one 100-switch attempt after PR #29 merged as `43eb6a4b0916a6e4903486555f385a65d19ee8d8`.
Google rejected the four-worker `n2-standard-32` pool before allocation.
At that attempt, project-wide `CPUS_ALL_REGIONS` quota permitted 32 vCPUs, with two in use and 30 available.
The 128-vCPU worker request exceeded available quota by 98 vCPUs despite sufficient regional N2 quota.
A separate project quota read confirmed the limit.
No scale worker, lab, switch, private runner, or scale workflow started.
The operator stopped image publication and removed the temporary repository without a retry or quota change.
Independent API inspection found only the original system pool, running Ready node, and disk.
Namespaces, firewalls, and cluster access resources matched their saved baselines.
Federation remained disabled with its original trust condition, and protected variables matched the saved baseline.
No temporary repository, runner registration, scale set, token-minting grant, or local credential file remained.
Task 9.1 remains unchecked at 40/44 tasks complete.
See the [attempt record](../../../docs/live-scale-100.md) for the acceptance boundary and final cleanup evidence.

## Resumed live scale attempt (task 9.1)

The user obtained a quota increase and authorized continuation of the bounded test.
A fresh read established an effective project-wide CPU limit of 132 before worker allocation.
Owner-approved [run 43598152566](https://github.com/dlobato/drydock/actions/runs/43598152566) used trusted revision `43eb6a4b0916a6e4903486555f385a65d19ee8d8` and selected input `b06f9d433a8f596887ae7251c7d3e8a08be48fe8`.
All 100 switches authenticated in 413.960 seconds, within the unchanged 900-second startup deadline.
Independent reads established all 294 links and 25 switches on each of four approved N2 workers.
The ANTA report contains all 1,088 required identities, with 458 successful results and 630 errors.
ANTA and the complete MLAG requirement did not pass.
The workflow deleted the lab, and independent reads found its namespace and topology absent within its accepted 30-minute lifetime.
The downloaded seven-day artifact matched the archive digest and every manifest hash.
All 100 sanitized catalogs parsed, and credential and private-file inspection passed across its 105 files.
The operator made no second live attempt, resource increase, or lifetime extension.
The user separately requested removal of the shared cluster after the test.
The final inventories establish complete removal of the cluster, compute, disks, owned networking, registry, custom cloud identities, and GitHub federation.
Default project resources and the Google-managed GKE trust domain remain.
The [live record](../../../docs/live-scale-100.md) retains timings, resource observations, exact runtime identities, failure limits, and final teardown evidence.
Task 9.1 remains unchecked at 40/44 tasks complete. Tasks 9.2 through 9.4 remain open.
