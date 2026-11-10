# Tasks

The CLI demo now precedes GitHub Actions integration by user agreement.
Implementation and PR publication are authorized. Cloud deployment and live acceptance are not authorized in this session.
Offline evidence does not establish runtime support. Keep this change active and unarchived.

## 1. Establish the implementation baseline

- [x] 1.1 Record the agreed startup delivery, CLI, AVD catalog ownership, external runner, and manual infrastructure lifetime in `design.md`.
- [ ] 1.2 Record the separate MLAG investigation outcome and supported runtime versions, with evidence for both MLAG pairs without the experimental rule.
- [x] 1.3 Document the finite lab expiry, cleanup cadence, retry policy, deletion target, and operator-owned infrastructure lifetime.

## 2. Build the anonymized example

- [x] 2.1 Add the six-switch AVD inventory with synthetic names, addresses, and identifiers. Demonstrate two spines and two MLAG pairs in generated output.
- [x] 2.2 Add pinned AVD dependencies and build commands. Demonstrate a clean build with AVD 6.5.0 without source repository access.
- [x] 2.3 Supply lab credentials at runtime. Inspect retained build output to establish that it contains no source identity or authentication material.
- [x] 2.4 Produce the complete switch-only Containerlab topology and configuration bundle. Demonstrate matching device identities, links, and a recorded bundle digest.
- [x] 2.5 Document the example build and test boundary. Run the documented commands from a clean checkout and compare the topology with the reference behavior.
- [x] 2.6 Bundle matching AVD structured configurations and enable HTTPS eAPI for the lab. Exercise actual `anta_runner` catalog generation offline.

## 3. Implement the lab lifecycle

- [x] 3.1 Add request validation and durable ownership records. Test missing configurations, unsupported devices, invalid expiry, and distinct workflow attempts before allocation.
- [x] 3.2 Add creation on dedicated temporary GKE workers and clabernetes. Use controlled tests to cover partial allocation and interrupted updates.
- [x] 3.3 Add status and private connection inventory output. Test an unreachable management API and original device identity preservation.
- [x] 3.4 Add repeatable deletion. Test already deleted resources, provider failure, and preservation of other labs and shared infrastructure.
- [x] 3.5 Implement independent expiry, indefinite retry, overdue records, pending operation discovery, and token renewal. Test the behavior with controlled provider responses.
- [ ] 3.6 Exercise the documented lifecycle and infrastructure commands in an authorized development environment, including the cleaner image build and repeated deployment.
- [ ] 3.7 Demonstrate expiry after runner loss, concurrent-lab isolation, and deleted cloud resources within the documented target.

## 4. Deliver the CLI and later GitHub integration

- [ ] 4.1 Add the workflow for trusted private repositories and external runners. Demonstrate that an AVD build failure does not allocate a lab.
- [x] 4.2 Invoke `anta_runner` for bounded acceptance and require generated routing, EVPN, VXLAN, switch-link, and both MLAG-pair coverage. Test missing, skipped, errored, duplicate, and failed results.
- [x] 4.3 Retain local JSON, JUnit, generated catalogs, lifecycle events, and available diagnostics with provenance. Test report write failure without blocking deletion.
- [x] 4.4 Add immediate cleanup and separate test and cleanup outcomes. Test that deletion failure prevents success without hiding an ANTA failure.
- [ ] 4.5 Add GitHub artifact upload and retention policy. Test upload failure without blocking deletion, then run the documented workflow manually before automatic live triggers.

## 5. Prove the milestone

- [ ] 5.1 Run an authorized cold-start six-switch lab without the experimental MLAG rule. Retain passing results, observed runtime versions, and evidence of complete deletion.
- [ ] 5.2 Exercise live failure, cancellation, timeout, and runner-loss paths. Retain partial reports and demonstrate cleanup within the documented target.
- [ ] 5.3 Compare delivered behavior with every scenario and record live evidence before archive. Strict offline specification validation alone does not complete this task.

## Evidence

See [the operator instructions](../../../docs/demo-flow.md) for commands, coverage, reports, and limits.
The implementation PR records the exact local gates and their outcomes.
Live tasks remain unchecked.
