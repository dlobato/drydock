# Tasks

The CLI demo now precedes GitHub Actions integration by user agreement.
The user authorized evidence reconciliation, private Pod-IP transport implementation, and live CLI acceptance on November 11, 2026.
The runner stays outside GKE. TLS certificate verification is disabled for this private demo by user agreement.
GitHub integration and archive remain outside this increment.
The user authorized commit, push, and an update to the existing PR after final validation.
Offline evidence does not establish runtime support. Keep this change active and unarchived.

## 1. Establish the implementation baseline

- [x] 1.1 Record the agreed startup delivery, CLI, AVD catalog ownership, external runner, and manual infrastructure lifetime in `design.md`.
- [x] 1.2 Record the separate MLAG investigation outcome and exact tested private runtime. Retain evidence for both pairs without the experimental rule.
- [x] 1.3 Document the finite lab expiry, cleanup cadence, retry policy, deletion target, and operator-owned infrastructure lifetime.

## 2. Build the anonymized example

- [x] 2.1 Add the six-switch AVD inventory with synthetic names, addresses, and identifiers. Demonstrate two spines and two MLAG pairs in generated output.
- [x] 2.2 Add pinned AVD dependencies and build commands. Demonstrate a clean build with AVD 6.5.0 without source repository access.
- [x] 2.3 Supply lab credentials at runtime. Inspect retained build output to establish that it contains no source identity or authentication material.
- [x] 2.4 Produce the complete switch-only Containerlab topology and configuration bundle. Demonstrate matching device identities, links, and a recorded bundle digest.
- [x] 2.5 Document the example build and test boundary. Run the documented commands from a clean checkout and compare the topology with the reference behavior.
- [x] 2.6 Bundle matching AVD structured configurations and enable HTTPS eAPI for the lab. Exercise actual `anta_runner` catalog generation offline.
- [x] 2.7 Restore the reference VRF VNIs and MLAG peer VLANs. Rebuild both example variants and test legal VLAN numbers, reference values, and the primary MLAG interface.

## 3. Implement the lab lifecycle

- [x] 3.1 Add request validation and durable ownership records. Test missing configurations, unsupported devices, invalid expiry, and distinct workflow attempts before allocation.
- [x] 3.2 Add creation on dedicated temporary GKE workers and clabernetes. Use controlled tests to cover partial allocation and interrupted updates.
- [x] 3.3 Add status and private connection inventory output. Test an unreachable management API and original device identity preservation.
- [x] 3.4 Add repeatable deletion. Test already deleted resources, provider failure, and preservation of other labs and shared infrastructure.
- [x] 3.5 Implement independent expiry, indefinite retry, overdue records, pending operation discovery, and token renewal. Test the behavior with controlled provider responses.
- [x] 3.6 Exercise the documented lifecycle and infrastructure commands in an authorized development environment, including the cleaner image build and repeated deployment.
- [ ] 3.7 Demonstrate expiry after runner loss, concurrent-lab isolation, and deleted cloud resources within the documented target.
- [x] 3.8 Replace port forwarding with private Pod-IP discovery for status, readiness, ANTA, and diagnostics. Test missing or duplicate Pods, private addresses, hostname mismatch, replacement Pods, and failure cleanup.

## 4. Deliver the CLI and later GitHub integration

- [ ] 4.1 Add the workflow for trusted private repositories and external runners. Demonstrate that an AVD build failure does not allocate a lab.
- [x] 4.2 Invoke `anta_runner` for bounded acceptance and require generated routing, EVPN, VXLAN, switch-link, and both MLAG-pair coverage. Test missing, skipped, errored, duplicate, and failed results.
- [x] 4.3 Retain local JSON, JUnit, generated catalogs, lifecycle events, and available diagnostics with provenance. Test report write failure without blocking deletion.
- [x] 4.4 Add immediate cleanup and separate test and cleanup outcomes. Test that deletion failure prevents success without hiding an ANTA failure.
- [ ] 4.5 Add GitHub artifact upload and retention policy. Test upload failure without blocking deletion, then run the documented workflow manually before automatic live triggers.

## 5. Prove the milestone

- [x] 5.1 Record the completed separate cold-start experiment for the exact private runtime. Retain its 54 results, both MLAG pairs, authenticated endpoints, conformance result, and complete deletion.
- [ ] 5.2 Exercise live failure, cancellation, timeout, and runner-loss paths. Retain partial reports and demonstrate cleanup within the documented target.
- [ ] 5.3 Compare delivered behavior with every scenario and record live evidence before archive. Strict offline specification validation alone does not complete this task.
- [x] 5.4 Run the actual single-command CLI acceptance on the corrected private runtime. Require all 54 results, saved reports, and complete deletion. Prove standalone create/status/delete on the existing cluster and independently inspect cleanup.

## Evidence

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
All 38 offline CLI tests pass.
The cleaner image build and repeated deployment evidence, together with the standalone lifecycle, complete task 3.6.
Earlier live evidence includes repeated infrastructure deployment, cancellation and timeout cleanup, and runner-loss expiry cleanup in 376 seconds.
Those observations remain partial evidence for tasks 3.7 and 5.2. Concurrent switch isolation remains unproven.
