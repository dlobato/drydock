# Tasks

The November 12 planning revision records the lifecycle-only requirements without authorizing automatic workflow execution.
Sections 1 through 5 retain completed work from the earlier GKE demo.
Task 6.1 records the first revised implementation and its offline and live evidence.
Tasks 6.2 and 6.3 record topology admission, ownership isolation, and their offline evidence.
Task 6.3 also records bounded live ownership and two-lab isolation evidence.
Task 6.4 records registry admission, offline tests, and bounded live image-access acceptance.
Task 7.1 records bounded startup waiting and controlled capacity and timeout evidence.
Task 7.2 records authenticated runtime inventory and controlled endpoint replacement evidence.
Task 7.3 records the 30-minute default, 60-minute maximum, and controlled expiry evidence.
Task 7.4 records the Kubernetes-only cleaner, image build, and controlled cleanup recovery evidence.
The remaining revised implementation and live acceptance tasks remain unchecked.

The former open demo tasks are replaced without claiming their completion:

| Former task | Replacement scope |
|---|---|
| 3.7: Concurrent isolation and expiry | 7.4, 9.2, and 9.3 |
| 4.1: GitHub orchestration | 8.1 through 8.5 |
| 4.5: Artifact upload and future automatic triggers | 8.1 and 8.4. Automatic triggers are excluded. |
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
- [ ] 7.5 Exercise the documented standalone creation, readiness, inventory, status, and repeated deletion commands. Demonstrate JSON outcomes and complete removal of lab-owned resources. Keep the switch TLS exception explicit and preserve verification for Kubernetes endpoints.
- [x] 7.6 Replace optional demo ANTA results after every completed invocation, including empty results. Test that acceptance uses the current attempt and preserves diagnostics if invocation raises.
- [x] 7.7 Skip completed cleanup records with absent namespaces using one namespace list per cleaner sweep. Test bounded API work, expired-lab cleanup, and late namespace discovery while preserving deletion ownership guards.
- [x] 7.8 Clear the overdue flag after successful deletion. Test repeated deletion after the cleanup deadline and retain overdue status for incomplete cleanup.

## 8. Integrate the owner-launched pipeline

- [ ] 8.1 Replace automatic triggers with manual dispatch in every workflow, including offline builds. Enforce the authorized launch and rerun actor before private runner assignment. Test exact-commit selection, trusted workflow revisions, and rejection of unauthorized runs.
- [ ] 8.2 Document and configure temporary GKE authentication through GitHub OIDC federation outside the lifecycle core. Deliver scoped RBAC and admission policy for the lab boundary. Demonstrate denial of unrelated Secret access, RBAC changes, cloud worker allocation, and unsafe workloads without personal keys.
- [ ] 8.3 Connect the standard AVD build and ANTA playbooks through the lifecycle CLI and runtime connection inventory. Isolate Ansible from Kubernetes credentials and use a pinned trusted CLI. Test model consistency, mandatory coverage, preserved inventory groups, and cleanup after each failure stage.
- [ ] 8.4 Select a finite artifact retention duration and retain safe reports with exact input provenance. Test upload failure without blocking deletion. Inspect final artifacts for credentials, startup files, and sensitive structured data. Document report paths and cleanup outcomes.
- [ ] 8.5 Run the documented workflow through an owner-authorized manual launch on the private self-hosted runner. Demonstrate temporary access, complete test reports, and lab deletion. Show that a new PR commit does not start another run or reuse the previous lab.

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

These tests do not measure live CronJob scheduling, runner-loss recovery, or the 30-minute deletion target.
Tasks 7.5, 8.2, and section 9 retain live command acceptance, enforced authorization policy, and runtime qualification.

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

## Workflow follow-up

- Use the apply-change workflow only after explicit implementation authorization for the revised plan.
- Keep the change active until the revised implementation, scenario evidence, and review are complete.
- Archive and inspect the archived specifications only after the project acceptance requirements are satisfied.
