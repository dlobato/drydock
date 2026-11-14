# Live GitHub pipeline acceptance

The bounded six-switch workflow passed on November 14, 2026.
All 54 required ANTA results passed, including both MLAG pairs.
The workflow uploaded its safe reports after complete lab deletion.
Inspection of the downloaded artifact passed.
Task 8.5 is complete. Section 9 retains scale, concurrency, failure, and provider qualification.

## Accepted attempt

| Item | Recorded value |
| --- | --- |
| Pull request | [#27](https://github.com/dlobato/drydock/pull/27) |
| Selected input | `5626f17e853bf6a226b415509f40b2784dc58a6e` |
| Trusted protected `main` | `33774b867491e88636397924f1345baa5a816331` |
| Dispatched run | [43592511128](https://github.com/dlobato/drydock/actions/runs/43592511128), attempt 1 |
| Native environment review | Fresh `gke` approval by `dlobato` |
| Workflow lab | `lab-84ce30d51d84` |
| Input digest | `abf3320aafc27d0804e02f80bfabfb3a2e84a705e97dcfa30d8ef7fcdf8b2b7b` |
| Uploaded artifact | `digital-twin-43592511128-1`, ID `14112953266`, seven-day retention |
| Artifact SHA-256 | `b8ee8d10cf8987abef627243464edc05e43184c11ace241648d910ff7290c538` |
| Final workflow result | Success |

The user approved the bounded test and the merge of [PR #28](https://github.com/dlobato/drydock/pull/28).
That merge supplied the corrected report collector through protected `main`.
Credentialed lifecycle code came from that exact trusted revision.
The proposed AVD build remained isolated from cloud credentials.

Before approval, GitHub recorded a waiting private job with no runner, executed steps, credentials, or lab.
Fresh native owner review approved this exact attempt.
The corrected dispatcher authorized the queued job before runner registration or VM creation.
The root-owned guard accepted the exact approved workflow attempt before workflow steps.
During execution, independent scale-set reads reported one assigned job, one running job, and one busy runner.

## Test boundary

The test reused `drydock-shared` in project `drydock-513410`, zone `europe-west1-b`.
Temporary capacity contained two `e2-standard-8` switch workers, each with an 80 GB disk.
One disposable `e2-standard-2` runner used private networking without a public IP or attached cloud service account.
GCE enforced its 4800-second deletion deadline.
The operator supplied no personal cloud credential, administrative kubeconfig, or registry credential to the runner.

An SSH tunnel supplied the pinned toolchain image through a loopback-only registry.
The operator compared the immutable manifest and its configuration digest.
The operator closed the tunnel before workflow execution.
Docker 29 reports the manifest digest as the image ID, so the preload used separate manifest and configuration comparisons.

| Component | Immutable image digest |
| --- | --- |
| Pipeline | `sha256:58869e47c528dc5dbbcb2b676f669b935fb60bdd729dfac13929fb1dc005d3ab` |
| Private clabernetes runtime | `sha256:d024ebf2e1a8322bb42fbf8a236985ba1f305de764db4c81fa005edebf329e12` |
| cEOS | `sha256:0a4da973f076a23aa83a598a57b08bd1a5a723f9f2e5cc5c0c44e92813f1e25b` |
| Cleaner | `sha256:682c3ffa4c8c8b8950a4e1cfb869d6e0ffd3cc35a493cd9887dee4ba28c057a4` |

The runtime used chart `0.11.0`, with chart digest `sha256:e003a8b4e0cc70b0147a6ed480494941d92418cd63f2be187b956f3733532a4b`.
The pipeline used Python `3.13.13`, AVD `6.5.0`, and ANTA `1.10.0`.
All six switches reported `4.36.1F-48405728.4361F (engineering build)`.
The switch TLS exception applied only to private switch endpoints.
Kubernetes and Google certificate verification remained enabled.
The operator installed no experimental EOS firewall rule, CloudVision, or host container.

## Network and report acceptance

The build and preflight stages established model consistency and mandatory catalog coverage before allocation.
All six switches ran across the two temporary workers.
The trusted lifecycle established all 12 accepted links and authenticated management readiness.
All 54 required ANTA results passed, including routing, EVPN, VXLAN, switch links, and both MLAG pairs.
No required result was missing, skipped, duplicated, errored, or failed.

Both immediate deletion stages succeeded before report collection and upload.
Independent Kubernetes reads observed the ownership record reach `deleted` and found no lab namespace or topology.

The downloaded archive matched GitHub's recorded SHA-256 digest.
Its 11 files contained ANTA JSON, JUnit, six catalogs, a run summary, diagnostics, and a manifest.
Inspection matched every manifest hash and parsed all six catalogs with ANTA.
The catalogs retained 54 tests, and JUnit retained 54 passing cases.
The reports identified the exact selected commit, trusted commit, run, attempt, input digest, lab, and runtime versions.
The EOS labels retained their spaces.
The byte scan found no credential patterns, startup files, allocation identifier, or structured configuration files.
The trusted collector also scanned for the actual generated lab secrets before upload.
GitHub recorded a seven-day artifact lifetime.

## Automatic checks and unmarked updates

The initial marked PR commit requested an exact-input test through the trusted metadata workflow.
Its ordinary hosted lint and tests also passed.
The later unmarked head `5626f17e853bf6a226b415509f40b2784dc58a6e` passed hosted [run 43592210088](https://github.com/dlobato/drydock/actions/runs/43592210088).
Its metadata-only [run 43592207068](https://github.com/dlobato/drydock/actions/runs/43592207068) passed selection and skipped the GKE job.
That update received no private runner, approval request, or inherited lab.
The accepted live attempt required a separate explicit dispatch and fresh native review.
The final evidence update is also unmarked.

## Earlier attempts and corrections

[Run 43587002589](https://github.com/dlobato/drydock/actions/runs/43587002589) stalled before private workflow execution and was canceled.
Its runner connected but remained idle while the approved job stayed queued.
Source inspection found that VM execution blocked queue polling and left the selected queue message unacknowledged.

The correction acknowledges that message before VM creation and continues polling until the VM driver finishes.
It permits one job and rejects another job or an additional reservation.
Queue failures cancel execution and wait for disposal.
Race tests cover blocked startup, unexpected jobs, excess capacity, API failures, and disposal before return.

[Run 43590604930](https://github.com/dlobato/drydock/actions/runs/43590604930) established the corrected live queue behavior.
It passed all 54 required results and deleted its lab, but report collection rejected spaces in the EOS build label.
It uploaded no artifact and did not establish complete workflow acceptance.
PR #28 fixed that separate issue and retained the length limit, control-character rejection, and final credential scan.
The accepted attempt above exercised that fix from protected `main`.

Local preparation passed 162 Python tests for the queue change and 163 Python tests for the separate report correction.
Both revisions passed six bundle tests, 33 selector tests, Go race tests, static analysis, repository hooks, actionlint, and strict OpenSpec validation.
Both offline AVD variants and the restricted container preflight passed.
The accepted live run supplied the remaining runtime and uploaded-artifact evidence.

## Cleanup and limits

The operator disabled federation and restored protected variables to their saved values.
The independent cleaner remained installed until lab deletion completed.
The dispatcher removed its VM, disk, SSH keys, registration, queue session, and scale set.
Independent final reads found no resource added for this attempt.
They matched namespace, firewall, and cluster-wide resource names against the saved baselines.
Only the original `default-pool`, running system node, and disk remained.
The original node was Ready, and the shared cluster and network remained in place.
The temporary runtime, admission service, cleaner, permissions, CRDs, workers, repository, registry, and local credential files were absent.
The temporary token-minting grant was also absent.

This result qualifies the recorded six-switch example on the exact private runtime only.
It does not qualify official clabernetes, arbitrary topologies, 100-switch capacity, concurrent labs, or AWS.
The remaining live failure and provider tests stay open in section 9.
