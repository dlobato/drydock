# 100-switch qualification

Task 9.1 requires live creation, authenticated readiness, ANTA acceptance, and complete deletion of one 100-switch lab.
The `scale-100` selection prepares that test through the existing isolated pipeline.
The default `example` selection still requires the original six switches and both MLAG pairs.
Offline results do not qualify live capacity or network behavior.
Task 9.1 remains open until the complete live attempt passes.

## Fabric and coverage

The scale fabric contains `spine1`, `spine2`, and `leaf1` through `leaf98`.
Its 49 MLAG pairs use the existing synthetic tenants, VRFs, and authentication supplied at runtime.
The trusted build helper expands a private copy of the proposed inventory.
It preserves the checked-in six-switch example and uses the existing AVD playbooks.
The larger uplink address pool and spine interface range accommodate all 98 leaves.
The resulting topology contains 196 leaf-to-spine links and 98 MLAG links.

The pipeline requires a matching model and complete startup file for every selected switch before allocation.
Every leaf must retain MLAG, VXLAN, routing, and link coverage.
The catalog policy accepts exactly the six-switch set or the selected 100-switch set.
A manual request without a fabric selection uses `example`.
A commit marker always requests `example`.
Only an explicit manual selection requests `scale-100`.
The approval job names the selected fabric before private work starts.

The report collector retains all selected switch identities and rejects results outside that set.
It keeps the existing test allowlist, credential scan, file limits, and seven-day retention.
Reports record the selected fabric beside the exact commit, trusted revision, input digest, run, and attempt.
Missing, duplicate, skipped, errored, and failed required results still prevent acceptance.

The November 14 offline run built all 100 switches through the actual restricted build and preflight containers.
It produced a 1,105,920-byte admitted bundle, 294 links, and 1,088 required ANTA entries.
The safe report directory contained 105 files, and ANTA parsed all 100 sanitized catalogs.
Removing MLAG coverage from `leaf98` failed the required coverage policy.
The run used local toolchain image `sha256:0f5d2988fbcef7004e1d67186c7ca79ef10ec2d06454602acfb4d017655bb853`.
It used no cloud credentials and allocated no lab.

## Proposed live boundary

The November 14 read-only inspection found the shared `drydock-shared` cluster running in `europe-west1-b`.
Only its original system node and baseline namespaces remained.
Regional quotas allowed 200 N2 vCPUs with zero recorded N2 usage.
The E2 limit was 24 vCPUs, so the earlier E2 worker arrangement cannot meet the existing switch requests.
Quota availability does not establish available zonal capacity or approval to allocate it.

The proposed single attempt uses this ceiling:

| Resource | Proposed limit |
| --- | --- |
| Existing shared cluster | Preserve `drydock-shared` and its original system pool |
| Temporary switch pool | Four private `n2-standard-32` Ubuntu workers |
| Added worker capacity | 128 vCPUs and 512 GB machine memory before Kubernetes reservations |
| Worker disks | Four 100 GB standard disks |
| Switch requests | One vCPU and 2 GiB each, 100 vCPUs and 200 GiB total |
| Switch limits | Two vCPUs and 3 GiB each, with CPU contention measured during startup |
| Disposable runner | One private `e2-standard-2`, no attached cloud service account |
| Runner disk | One 30 GB standard disk |
| Accepted lab lifetime | Keep the 30-minute default and the 60-minute maximum |
| Initial startup deadline | Keep 900 seconds, bounded by accepted expiry |
| Capacity window | Start removal within 90 minutes of the first temporary worker allocation |
| Attempts | One attempt, with no automatic larger retry |

This plan requires separate approval for cloud allocation and the temporary trust changes.
`AGENTS.md` requires authorization before cloud provisioning.
Merge the reviewed pipeline change into protected `main` before credentialed execution.
Rebuild the operator dispatcher from that revision to accept the job name with its selected fabric.
The live workflow must use that exact trusted revision and fresh native `gke` approval.
Approval of this preparation PR does not establish live acceptance.

Reuse the exact private runtime from [task 8.5](live-github-pipeline.md) after its image identities and availability pass inspection.
Install the same admission boundary, independent cleaner, scoped permissions, and isolated image delivery before enabling federation.
Keep the existing switch TLS exception and certificate verification for Kubernetes and Google.
Do not install the experimental firewall workaround.
If preparation exceeds a pipeline limit, stop before allocation and retain the failure evidence.

## Acceptance and cleanup

Record the baseline cluster, namespaces, node pools, firewall rules, registry resources, federation restrictions, and protected variables before allocation.
Record the exact source revisions, image digests, runtime versions, switch requests, and admitted topology digest.
Measure acceptance, capacity waiting, authenticated readiness, ANTA completion, deletion request, and complete deletion separately.
Record switch placement, node allocatable resources, memory pressure, CPU contention, and scheduling failures during startup.
Require all 100 authenticated switch identities, all 294 links, every required result, and all 49 MLAG pairs.
Inspect the downloaded artifact and its hashes after upload.

Use the initial startup deadline as an unqualified test bound.
If the attempt misses that bound, report the failure and request deletion.
Set a qualified startup deadline only from measured evidence within the accepted lifetime.
Do not extend expiry or increase capacity to force a passing result.

Request immediate deletion after every allocated outcome.
Keep the independent cleaner installed until Kubernetes reads establish complete lab deletion.
Then remove the temporary workers, runner, registry, runtime, admission components, scoped permissions, and temporary access grants.
Restore federation and protected variables to their recorded state.
Make sure that final resource inventories match the saved baselines and that the original system node remains Ready.
Preserve the shared cluster and network for other sessions.

This first attempt does not qualify concurrent labs, other providers, or the official clabernetes release.
Tasks 9.2 through 9.4 retain those separate requirements.
Cloud cost includes temporary compute, disks, registry storage, and network traffic.
The capacity ceiling and removal window bound resource use, but this plan does not quote a monetary price.
