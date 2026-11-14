# Single 100-switch qualification attempt

The November 14 live attempt reached authenticated readiness for all 100 switches in 414 seconds, within the 900-second startup limit.
Network acceptance failed: the retained ANTA report contains 458 successful results and 630 errors across 1,088 required results.
The workflow deleted the lab within its accepted 30-minute lifetime.
Task 9.1 remains unchecked at 40/44 tasks complete because network acceptance did not pass.
Tasks 9.2 through 9.4 also remain open.

## Source and runtime

[PR #29](https://github.com/dlobato/drydock/pull/29) merged as trusted revision `43eb6a4b0916a6e4903486555f385a65d19ee8d8` before credentialed execution.
[Run 43598152566, attempt 1](https://github.com/dlobato/drydock/actions/runs/43598152566) selected immutable input `b06f9d433a8f596887ae7251c7d3e8a08be48fe8` from [PR #30](https://github.com/dlobato/drydock/pull/30).
The repository owner supplied fresh native `gke` approval for the explicit `scale-100` selection.
The isolated build and preflight passed before Google federation and lab allocation.
The admitted bundle digest was `a1ea9b8ea3e7cec30947b822ee2a782c33deba4badae8985c538aa605c78e716`.

The runtime used Python 3.13.13, AVD 6.5.0, and ANTA 1.10.0.
All 100 authenticated switches reported EOS `4.36.1F-48405728.4361F (engineering build)`.
The clabernetes chart version was 0.11.0, with digest `sha256:e003a8b4e0cc70b0147a6ed480494941d92418cd63f2be187b956f3733532a4b`.
These immutable image digests identify the exact private runtime:

| Image | Digest |
| --- | --- |
| Pipeline | `sha256:58869e47c528dc5dbbcb2b676f669b935fb60bdd729dfac13929fb1dc005d3ab` |
| cEOS | `sha256:0a4da973f076a23aa83a598a57b08bd1a5a723f9f2e5cc5c0c44e92813f1e25b` |
| Runtime | `sha256:d024ebf2e1a8322bb42fbf8a236985ba1f305de764db4c81fa005edebf329e12` |
| Cleaner | `sha256:682c3ffa4c8c8b8950a4e1cfb869d6e0ffd3cc35a493cd9887dee4ba28c057a4` |

The operator installed scoped access, TLS admission, and the independent cleaner before enabling temporary federation.
Live boundary probes passed denial, ownership, expiry-extension, cleaner deletion, and webhook failure tests.
One boundary cleanup Job failed during asynchronous deletion, and the scheduled cleaner completed deletion.
The operator installed no experimental EOS firewall workaround.
The existing private switch TLS exception remained explicit.

## Capacity and observations

Four private `n2-standard-32` workers supplied 128 machine vCPUs and 512 GB machine memory before Kubernetes reservations.
Their aggregate allocatable CPU was 127.4 vCPUs.
Each worker used a 100 GB standard disk and hosted 25 switches.
Each switch requested one CPU and 2 GiB, with limits of two CPUs and 3 GiB.
One private `e2-standard-2` runner used a 30 GB standard disk and no attached cloud service account.
Operator credentials remained outside the runner.

Independent reads established the exact 100 switch identities and all 294 accepted links.
The topology contained two spines, 98 leaves, 196 leaf-to-spine links, and 98 links across 49 MLAG pairs.
All 100 switch Pods became Ready, with no sampled container restarts before deletion.
Samples recorded no node memory, disk, or PID pressure and no failed scheduling events.
Worker CPU peaks ranged from 12.65 to 15.60 cores, and worker memory peaks remained below 33.6 GiB.
The original two-CPU system node reached 93% of allocatable CPU in one sample.
These samples do not establish unsampled peaks or spare capacity for another lab.

A cumulative sample after readiness covered CPU quota counters for all 100 switch containers.
CPU throttling occurred in 28,546 of 347,184 recorded quota periods, or 8.22% in aggregate.
This establishes contention at the configured container limits, but does not prove the cause of the ANTA errors.
A separate runner sample during ANTA showed approximately two CPUs in use and 653 MiB of container memory.

## Timing and outcome

| Event | UTC on November 14 |
| --- | --- |
| Temporary worker allocation requested | 13:05:00 |
| Lab accepted | 13:16:18.755 |
| All switches authenticated and ready | 13:23:12.715 |
| Deletion started after ANTA attempt | 13:33:25.958 |
| Final deletion record observed | 13:35:36.290 |
| Accepted expiry | 13:46:18.755 |

Authenticated startup took 413.960 seconds.
The pipeline retained its 600-second ANTA convergence limit without increasing resources or extending expiry.
The final report records failure at stage `test`, with error category `RuntimeError`.
All 1,088 required result identities appear exactly once, but 630 contain `error` and only 458 contain `success`.
No switch passed its entire required result set, and the complete 49-pair MLAG requirement did not pass.
The safe artifact does not retain raw command errors, so it does not establish their cause.

Independent Kubernetes reads found the ownership record deleted, with its namespace and topology absent.
The final deletion record followed the deletion request by 130.331 seconds and acceptance by 1,157.534 seconds.
The initial cleanup and unconditional repeated deletion both reported success.
The operator made no second live attempt, larger retry, lifetime renewal, or resource increase to force acceptance.
The measured startup supports retaining 900 seconds for another test of this exact profile.
It does not complete qualification without passing network acceptance.

## Retained artifact

The workflow retained `digital-twin-43598152566-1`, artifact ID `14116286804`, for seven days.
Its archive digest is `sha256:224eef5e4e30eb749aa9ca7d8c5a56fc0ad1010b2ac08fd7d0d7924d9cf08eae`.
The downloaded bytes matched GitHub metadata, and every manifest hash matched the extracted file.
The artifact contains 105 files: five reports and 100 sanitized catalogs.
ANTA parsed all catalogs, with 1,088 catalog entries in total.
JUnit contains 1,088 cases and 630 failure elements that represent the ANTA errors.
The source revisions, input digest, runtime labels, failed acceptance, and successful cleanup matched the live records.
The artifact scan found no credentials, startup files, structured configurations, or private allocation identity.
Raw operator observations remain private and are excluded from the PR.

## Cleanup

The operator disabled federation and restored its original trust condition after the workflow ended.
The independent cleaner remained installed until complete lab deletion was established.
The disposable dispatcher removed its VM, disk, SSH keys, registration, queue session, and scale set.
The operator removed the temporary runtime, admission components, permissions, worker pool, registry, repository, firewall rules, and credential files.
Worker removal started at 13:37:05 UTC, about 32 minutes after allocation began and within the approved 90-minute window.
Pool deletion completed at 13:39:48 UTC.
An independent audit then established the original Ready node, pool, disk, namespaces, firewalls, and cluster access baselines.
It also established restored protected variables, disabled federation, and no temporary runner, scale set, registry, access grant, or credential files.

The user separately requested full shared-cluster teardown after the test.
The operator deleted `drydock-shared`, its original node and disk, Cloud NAT, router, subnet, network, and remaining owned firewall rules.
It removed both dedicated cloud service accounts, their project grants, the custom connection role, and the GitHub federation pool.
It also removed obsolete GitHub variables and the local cluster kubeconfig.
Final API inventories at 13:46:52 UTC found no cluster, VM, disk, reserved address, router, image repository, bucket, or private runner.
A separate API read at 13:47:20 UTC found zero project-wide CPU usage.
Only default project networking, the default compute account, and the Google-managed GKE trust domain remained.
Future live work requires fresh cluster and identity setup.

## Earlier quota rejection

An earlier preparation stopped before worker allocation because project-wide `CPUS_ALL_REGIONS` quota allowed only 32 vCPUs.
Two CPUs were already in use, so the 128-CPU worker request exceeded the available quota by 98.
Regional `N2_CPUS` quota allowed 200 vCPUs, but did not override the project-wide limit.
That preparation created no lab or private runner, and independent inspection established complete temporary cleanup.

The user obtained approval for a project-wide increase before this resumed attempt.
A fresh read established an effective limit of 132 vCPUs, which covered 128 worker CPUs, two existing CPUs, and two runner CPUs.
This quota permits the tested allocation but leaves no quota margin at that baseline.
It does not establish zonal availability or the aggregate capacity required for concurrent labs.

## Qualification limit

This attempt establishes bounded startup and deletion for one exact private 100-switch runtime.
It does not establish successful scale network acceptance, concurrent labs, traffic performance, AWS compatibility, or official clabernetes compatibility.
Further live work requires a separate approved attempt and investigation of the ANTA errors.
The [qualification plan](scale-qualification.md) retains the full acceptance requirements.
