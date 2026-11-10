# Tasks

The first PR covers only the anonymized example and offline build evidence.
Runtime design decisions and the separate MLAG investigation do not block offline generation.
The broader milestone remains active. Unperformed work stays unchecked.

## 1. Establish the implementation baseline

- [ ] 1.1 Record the reviewed configuration delivery and command interface choices in `design.md`, with their acceptance evidence.
- [ ] 1.2 Record the separate MLAG investigation outcome and supported runtime versions, with evidence for both MLAG pairs without the experimental rule.
- [ ] 1.3 Document the finite lab expiry, cleanup cadence, retry policy, and deletion bound, with explicit operator-owned development infrastructure lifetime.

## 2. Build the anonymized example

- [x] 2.1 Add the six-switch AVD inventory with synthetic names, addresses, and identifiers. Demonstrate two spines and two MLAG pairs in generated output.
- [x] 2.2 Add pinned AVD dependencies and build commands. Demonstrate a clean build with AVD 6.5.0 without source repository access.
- [x] 2.3 Supply lab credentials at runtime. Inspect retained build output to establish that it contains no source identity or authentication material.
- [ ] 2.4 Produce the complete switch-only Containerlab topology and configuration bundle. Demonstrate matching device identities, links, and a recorded bundle digest.
- [x] 2.5 Document the example build and test boundary. Run the documented commands from a clean checkout and compare the topology with the reference behavior.

## 3. Implement the lab lifecycle

- [ ] 3.1 Add request validation and durable ownership records. Test missing configurations, unsupported devices, invalid expiry, and distinct workflow attempts before allocation.
- [ ] 3.2 Add creation on dedicated temporary GKE workers and clabernetes. Use controlled tests to cover partial allocation and discover resources after interrupted updates.
- [ ] 3.3 Add status and private connection inventory output. Test an unreachable management API and original device identity preservation.
- [ ] 3.4 Add repeatable deletion. Test already deleted resources, provider failure, and preservation of other labs and shared infrastructure.
- [ ] 3.5 Add cleanup independent of the runner. Demonstrate expiry and retry after runner loss, with evidence that owned resources disappear within the documented bound.
- [ ] 3.6 Document lifecycle commands, infrastructure prerequisites, cleanup diagnostics, and separate shared teardown. Exercise the documented commands in the authorized development environment.

## 4. Integrate GitHub Actions and ANTA

- [ ] 4.1 Add the workflow for trusted private repositories and private runners. Demonstrate that an AVD build failure does not allocate a lab.
- [ ] 4.2 Add bounded network acceptance for routing, EVPN, VXLAN, and both MLAG pairs. Demonstrate that failed, errored, missing, or skipped required tests fail the run.
- [ ] 4.3 Retain JSON, JUnit, catalog, logs, and available diagnostics with commit, runtime, bundle, and lab identity. Test report upload failure without blocking deletion.
- [ ] 4.4 Add immediate cleanup and separate test and cleanup outcomes. Demonstrate that deletion failure prevents success without hiding an ANTA failure.
- [ ] 4.5 Document runner access, credentials, workflow triggers, report retention, and observed traffic coverage. Run the documented workflow manually before enabling automatic triggers.

## 5. Prove the milestone

- [ ] 5.1 Run an authorized cold-start six-switch lab without the experimental MLAG rule. Retain passing network results and evidence of deleted temporary resources.
- [ ] 5.2 Exercise failure, cancellation, timeout, and runner-loss paths. Retain partial reports when available and demonstrate cleanup within the documented bound.
- [ ] 5.3 Run strict OpenSpec validation and compare the delivered behavior with every scenario. Record the exact commands and runtime evidence before archive.

## Workflow follow-up

- Archive this change after implementation, validation, and review.
- Run strict validation again after the requirements enter `openspec/specs/`.
