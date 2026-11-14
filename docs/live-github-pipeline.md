# Live GitHub pipeline attempt

Task 8.5 remains incomplete after the November 14, 2026 attempt.
The private runner became available, but GitHub left the approved job queued.
No workflow step, switch lab, ANTA test, or artifact upload started.
The operator canceled the attempt and disabled federation.

## Exact request

| Item | Recorded value |
| --- | --- |
| Pull request | [#27](https://github.com/dlobato/drydock/pull/27) |
| Selected input | `4b8a447ffd4e1da7d8c304fe4b830e745058e62e` |
| Trusted protected `main` | `afe9d1836cea6bf32738d7538df41028606a2011` |
| Dispatched run | [43587002589](https://github.com/dlobato/drydock/actions/runs/43587002589), attempt 1 |
| Native environment review | `gke`, approved by `dlobato` |
| Hosted lint and tests | [43586988996](https://github.com/dlobato/drydock/actions/runs/43586988996), both passed |
| Metadata request | [43586989283](https://github.com/dlobato/drydock/actions/runs/43586989283), passed |
| Final live result | Canceled before private job execution |

The latest input commit explicitly requested testing through its marker.
The metadata workflow selected that exact input and dispatched the trusted workflow.
Before native approval, the private job waited without a runner, cloud credentials, or a lab.
The dispatcher accepted the exact approved attempt before it registered the runner or created its VM.

## Test boundary

The user approved reuse of `drydock-shared` in `europe-west1-b`.
Temporary capacity contained two `e2-standard-8` switch workers, each with an 80 GB disk.
One disposable `e2-standard-2` runner used private networking without an attached cloud service account.
The VM retained its 4800-second deletion deadline and the root-owned job identity guard.
The operator supplied no personal cloud credential, administrative kubeconfig, or registry credential to the runner.

An SSH tunnel supplied the pinned toolchain image through a loopback-only registry.
The operator compared the immutable manifest and its configuration digest.
Docker 29 reports the manifest digest as the image ID, so the operator adapted the local preload comparison.
The operator closed the transfer listener before workflow execution.

| Component | Immutable image digest |
| --- | --- |
| Pipeline | `sha256:58869e47c528dc5dbbcb2b676f669b935fb60bdd729dfac13929fb1dc005d3ab` |
| Private clabernetes runtime | `sha256:d024ebf2e1a8322bb42fbf8a236985ba1f305de764db4c81fa005edebf329e12` |
| cEOS `4.36.1F` | `sha256:0a4da973f076a23aa83a598a57b08bd1a5a723f9f2e5cc5c0c44e92813f1e25b` |
| Cleaner | `sha256:682c3ffa4c8c8b8950a4e1cfb869d6e0ffd3cc35a493cd9887dee4ba28c057a4` |

The runtime used chart `0.11.0`, with chart digest `sha256:e003a8b4e0cc70b0147a6ed480494941d92418cd63f2be187b956f3733532a4b`.
This private runtime does not qualify official clabernetes compatibility.
The planned switch TLS exception applied only to private switch endpoints.
Kubernetes and Google certificate verification remained enabled.
The operator installed no experimental EOS firewall rule, CloudVision, or host container.

## Queue failure and source correction

The runner connected at `11:12:22Z` and reported that it listened for jobs.
GitHub independently reported that runner online and idle while the approved job remained queued.
The scale set reported one registered runner and zero assigned jobs.

Source inspection found that the dispatcher stopped queue polling during VM preparation and execution.
It also left the selected queue message unacknowledged while the VM driver blocked.
Those defects can interrupt the queue protocol during slow startup.
The observed stall is consistent with those defects, but this attempt does not prove the corrected live behavior.

The correction acknowledges the selected message before VM creation and continues polling until the VM driver finishes.
It retains capacity for one job and rejects a different job or additional reservation.
A polling or acknowledgement failure stops the VM driver and waits for its disposal handler.
The existing approval policy, workflow identity guard, and provider restrictions remain in force.
No modified lifecycle code ran with cloud credentials.

Race tests cover queue progress during blocked startup, unexpected jobs, excess capacity, API failures, and disposal before return.
The existing runner safety tests, static analysis, and required repository hooks pass.
A fresh protected workflow attempt must establish live acceptance after review of this correction.

## Preparation evidence

The operator installed the TLS admission service, scoped permissions, and independent cleaner on the shared cluster.
Actual Kubernetes probes denied unsafe topology, unrelated reads, privilege escalation, expiry extension, and unavailable admission.
The cleaner deleted the expired fixture namespace.
An initial cleaner job failed during asynchronous deletion, and the scheduled retry completed it.
The runtime manager stayed paused during these probes, so they allocated no switches.

All 18 focused Python tests and 33 selector tests passed during preparation.
Actionlint and strict OpenSpec validation passed.
The restricted toolchain built six catalogs with all 54 required entries, including both MLAG pairs.
The offline archive contained 11 approved files and passed credential inspection.
These results do not establish live network acceptance.

## Cleanup

Independent reads found no workflow lab namespace, topology, switch workload, or uploaded artifact.
The only retained lab record belonged to the earlier deleted admission fixture.
The operator removed that record with the temporary system namespace after it retained the local evidence.

The dispatcher journal records VM deletion and scale-set removal after cancellation.
Independent GitHub reads found zero registered runners and no scale set.
The runner disk and generated SSH keys are absent.
The operator restored the protected environment variables to their saved values.
Federation is disabled and retains the exact trusted revision and narrowed dispatch restriction.

The operator removed the temporary runtime, admission service, cleaner, permissions, and five empty runtime CRDs.
It also removed the private image repository, repository grant, two firewall rules, and local loopback registry.
Independent reads found only the original `default-pool`, its running system node, and its disk.
The original node is ready, and the namespace and firewall inventories match their saved baselines.
The shared cluster and network remain in place.
No resource added for this attempt remains.

## Remaining acceptance

A fresh approved attempt must pass all 54 live ANTA results, including both MLAG pairs.
Its downloaded seven-day artifact must establish safe contents, exact provenance, and complete network results.
Independent Kubernetes reads must establish complete workflow lab deletion.
The correction uses an unmarked PR update.
PR #27 records its final hosted results and metadata-only selector outcome.
That path must start no GKE request or inherited approval.

Task 8.5 remains unchecked at 39/44 tasks complete.
Section 9 retains scale, concurrency, failure, and provider qualification.
