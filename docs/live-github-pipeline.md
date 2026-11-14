# Live GitHub pipeline attempts

Task 8.5 remains incomplete after two attempts on November 14, 2026.
The first attempt stalled before workflow execution.
The approved retry passed all 54 network tests and deleted its lab, but report collection failed.
Neither attempt uploaded an artifact.
The operator disabled federation and removed all temporary resources after each attempt.

## Initial request

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
The approved retry below establishes live queue progress and runner disposal with this correction.
Complete pipeline acceptance remains open because report collection failed.

## Approved retry

| Item | Recorded value |
| --- | --- |
| Selected input and operator dispatcher revision | `a19de65403904b23e4b6f55febababd0969df2e1` |
| Trusted protected `main` | `afe9d1836cea6bf32738d7538df41028606a2011` |
| Dispatched run | [43590604930](https://github.com/dlobato/drydock/actions/runs/43590604930), attempt 1 |
| Native environment review | Fresh `gke` approval by `dlobato` |
| Workflow lab | `lab-3714cc80d869` |
| Input digest | `b05a1648dc63c576522b3c15e8e9b0fcc70dbae4378a178797a62064f4827418` |
| Final live result | Network tests and lab deletion passed; report collection failed |

The retry reused the same image digests, shared cluster, and two-worker limit.
All 162 Python tests, six bundle tests, and 33 selector tests passed before dispatch.
Both offline AVD builds, Go race tests and static analysis, repository hooks, actionlint, and strict OpenSpec validation passed.
The restricted container preflight generated six catalogs with all 54 required entries.
Its 11-file offline archive passed credential inspection.

Actual Kubernetes probes repeated the permission denials, unsafe-topology rejection, expiry protection, cleaner deletion, and rejection when admission was unavailable.
The runtime controller remained paused during these probes.
The first cleaner sweep encountered asynchronous deletion; the next sweep completed the fixture cleanup.
The operator removed the temporary token-minting grant before runner execution.

The corrected operator dispatcher accepted the exact approved run before it created its private runner.
The root-owned guard accepted the exact workflow attempt.
GitHub reported one busy runner and one running job while the dispatcher maintained its queue session.
The workflow used protected-main lifecycle code and isolated the proposed build from cloud credentials.

All six switches became ready across the two temporary workers, with all 12 links accepted.
The workflow established authenticated management readiness and passed all 54 required ANTA results, including both MLAG pairs.
A bounded status read retained the passing acceptance result and 54 successful result statuses.
Independent Kubernetes reads established that the lab namespace and topology were deleted.

Report collection then failed with `ValueError` and uploaded no artifact.
The observed EOS version was `4.36.1F-48405728.4361F (engineering build)`.
The collector rejected the spaces in that valid build label.
The regression test in [PR #28](https://github.com/dlobato/drydock/pull/28) reproduces this exact failure.
That focused fix retains the length limit, rejects control characters, and preserves the final credential scan.
It still needs a fresh workflow run from protected `main`.
The passing network snapshot does not replace the missing uploaded JSON, JUnit, catalogs, and provenance artifact.

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

Independent reads after the retry reached the same cleanup result.
The dispatcher exited successfully and removed its VM, disk, registration, keys, queue session, and scale set.
The operator removed all temporary workers, repositories, permissions, runtime components, firewall rules, and local credential files.
Namespace, firewall, and cluster-wide resource names match their saved baselines.
Only the original `default-pool`, running system node, and disk remain.
Federation is disabled, and protected variables match their saved values.

## Remaining acceptance

A fresh approved attempt after the report fix must repeat all 54 live ANTA results, including both MLAG pairs.
Its downloaded seven-day artifact must establish safe contents, exact provenance, and complete network results.
Independent Kubernetes reads must establish complete workflow lab deletion.
The correction uses an unmarked PR update.
PR #27 records its final hosted results and metadata-only selector outcome.
That path must start no GKE request or inherited approval.

Task 8.5 remains unchecked at 39/44 tasks complete.
Section 9 retains scale, concurrency, failure, and provider qualification.
