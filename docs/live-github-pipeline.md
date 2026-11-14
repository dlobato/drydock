# Live GitHub pipeline acceptance

Task 8.5 remains incomplete while this acceptance test runs.
This record separates the complete workflow test from the earlier no-lab access probe.

## Test boundary

The user approved a bounded live test on November 14, 2026.
The test reuses the shared `drydock-shared` GKE cluster in `europe-west1-b`.
It preserves that cluster, its original system node, network, and unrelated resources.
Temporary capacity contains two `e2-standard-8` switch workers and one disposable `e2-standard-2` runner.
Each worker has an 80 GB disk.

The trusted workflow revision is `afe9d1836cea6bf32738d7538df41028606a2011` on protected `main`.
The test uses cEOS `4.36.1F` and the previously tested private clabernetes runtime.
It does not install the experimental EOS firewall rule.
The existing switch TLS exception remains limited to private switch endpoints.
Kubernetes and Google endpoints retain certificate verification.

The runner receives no cloud service account, operator credential, or registry credential.
An SSH tunnel supplies the reviewed toolchain image through a loopback-only registry before job execution.
The tunnel closes before the workflow starts.
The toolchain digest is `sha256:58869e47c528dc5dbbcb2b676f669b935fb60bdd729dfac13929fb1dc005d3ab`.
The private runtime digest is `sha256:d024ebf2e1a8322bb42fbf8a236985ba1f305de764db4c81fa005edebf329e12`.
The cEOS digest is `sha256:0a4da973f076a23aa83a598a57b08bd1a5a723f9f2e5cc5c0c44e92813f1e25b`.

## Required acceptance evidence

The final record must identify the selected PR commit, workflow run, attempt, lab, input digest, and observed runtime.
It must retain automatic hosted lint and unit results and native `gke` approval evidence.
The network test must pass all 54 required ANTA results, including both MLAG pairs.
The downloaded seven-day report artifact must contain safe reports with exact provenance.
Independent Kubernetes reads must establish complete lab deletion.

A later unmarked PR commit must run hosted checks without another GKE request or inherited approval.
The operator must remove the disposable runner, registration, disk, keys, queue session, and scale set.
The final inventory must establish removal of this session's temporary resources while preserving the shared cluster.
Federation must be disabled after the test with its reviewed restrictions retained.

## Offline preparation

All 18 focused Python tests and 33 commit-selector tests pass.
Actionlint and strict OpenSpec validation pass.
The restricted toolchain builds all six catalogs with 54 required entries.
The offline archive contains 11 approved files and passes credential inspection.
These dry-run results do not establish live network acceptance.

Live workflow execution, artifact download, and final cleanup evidence remain pending.
Section 9 retains scale, concurrency, failure, and provider qualification.
