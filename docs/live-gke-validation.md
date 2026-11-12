# Live GKE validation

## November 12 registry-independent images

Executable source at commit `68f147b81627a2b0490d2e7f8646f4c626931c49` passed six-switch acceptance with a digest-pinned cEOS image outside Google Artifact Registry.
The operator ran an authenticated TLS registry on a private VM outside the switch lab.
The VM had no public IP. The temporary Artifact Registry repository and project contained no public access grants.
Anonymous and wrong-password registry requests failed. Authenticated requests passed with TLS verification enabled.

The cEOS manifest digest was `sha256:0a4da973f076a23aa83a598a57b08bd1a5a723f9f2e5cc5c0c44e92813f1e25b`.
Independent Kubernetes reads found that digest in all six running switch image identities.
The submitted topology and ownership record retained the private registry reference.
The lifecycle CLI did not obtain registry tokens or create image credentials.

The operator configured controller certificate trust, worker certificate trust, global pull-Secret references, and credentials in the new lab namespace.
Clabernetes remained paused during CLI creation until the operator supplied the namespace Secret.
The operator corrected worker CA trust during startup after initial certificate failures.
Kubernetes retried image pulls within the original lifetime. Registry and Kubernetes TLS verification remained enabled.
This procedure demonstrates operator-managed image access. It does not qualify automatic recovery after late registry credentials.

Standalone CLI creation, authenticated status, six-device inventory, wrong-password rejection, deletion, and repeated deletion passed.
The request used an explicit 30-minute lifetime without changing the current CLI defaults.
The minimal lifecycle image contained no AVD, ANTA, Ansible, or Google Cloud CLI.
A separate ANTA container received connection inventory and matching AVD models without Kubernetes credentials.
It passed exactly 54 required results with the expected multiplicity, including both MLAG pairs.
Private evidence retains JSON, JUnit, generated catalogs, image identities, input digests, and source hashes.

Independent reads found the lab namespace absent and its ownership record deleted before shared teardown.
The cluster identity, worker pools, and unrelated namespace and Secret survived lab deletion.

The operator then removed the temporary cluster, workers, network, IAM grants, runner, and registries.
A fresh independent inventory found zero owned resources across all 15 infrastructure categories.
Baseline resources in ten categories and the existing project remained intact.
Temporary access files and local registry tags were removed. The default kubeconfig remained unchanged.
The original licensed image remained available locally.

The runtime used GKE `1.36.4-gke.2377000`, engineering EOS `4.36.1F-48405728.4361F`, private fork chart `0.0.0`, AVD `6.5.0`, and ANTA `1.10.0`.
The private runtime digest remained `sha256:d024ebf2e1a8322bb42fbf8a236985ba1f305de764db4c81fa005edebf329e12`.
Two shared `e2-standard-8` workers served one six-switch lab. No experimental EOS firewall rule was installed.
Switch probes retained the agreed certificate-verification exception, password authentication, and EOS hostname comparison.
No GitHub workflow ran for this acceptance.

This evidence completes task 6.4 for the tested private registry and runtime.
It does not qualify other registry authentication methods, the official clabernetes release, 100-switch scale, larger concurrency, or AWS.

## November 12 ownership and isolation

Executable source at commit `2fb4057a7fb9a04c24da3b0ca941bb8b7d58eac0` passed ownership tests against live Kubernetes APIs.
Two concurrent six-switch labs used the same bundle, request provenance, switch names, and management addresses.
Their ownership records, allocation labels, namespaces, and twelve switch Pod identities remained separate.
Both labs passed authenticated management readiness and all 54 required ANTA results, including both MLAG pairs.

The operator created one temporary cluster before testing and reused it across all cases.
The operator supplied two shared `e2-standard-8` workers with 80 GB disks.
Each switch requested one CPU and 2 GiB of memory, with limits of two CPUs and 3 GiB.
The caller confirmed initial readiness within eight minutes of acceptance and replacement readiness within three minutes.
These measurements include the operator registry retries described below.

Controlled failure injection exercised the CLI against the live API.
A forced short-ID collision preserved the earlier lab and refused cleanup by the conflicting allocation ID.
Stale ownership updates could not extend expiry or restore a deleted state.
A lost ownership-creation response still allowed cleanup with the matching allocation ID.
Status and deletion refused a namespace with a different allocation label.

Namespace race tests used separate empty test namespaces.
Kubernetes returned `Conflict` when deletion used a stale resource version or a replaced namespace's object ID.
The replacement namespace survived that deletion request.
The reaper also removed a matching namespace that appeared after its record reached the deleted state.
Repeated deletion passed, and deleting one switch lab preserved the survivor's Pod identities and its next 54 ANTA results.

A replacement six-switch lab used an eight-minute lifetime and passed all 54 results alongside the survivor.
The caller then left that lab without requesting deletion or changing its expiry.
Independent observations found deletion starting within 217 seconds after expiry and namespace removal within 263 seconds.
The first scheduled cleaner job reported incomplete cleanup while Kubernetes removed the namespace.
The next scheduled job confirmed complete deletion, observed within 516 seconds after expiry.
That job used the tested minimal lifecycle image and its Kubernetes service-account token without cloud credentials.

The survivor retained its original Pod identities and passed another 54 results after expiry cleanup.
All seven ANTA runs matched the exact expected result counts and passed both MLAG pairs.
They produced 378 successful results in total.

| Case | ANTA runs | Result per run |
|---|---:|---|
| Initial concurrent labs | 2 | 54/54 passed |
| After ownership failure tests | 1 | 54/54 passed |
| After deleting the other lab | 1 | 54/54 passed |
| Before independent expiry | 2 | 54/54 passed |
| After independent expiry | 1 | 54/54 passed |

Independent reads found all seven ownership records deleted and every lab namespace absent before shared infrastructure teardown.
The cluster identity, creation time, worker pools, and unrelated namespace and Secret survived the test cases.
The default kubeconfig also remained unchanged.
The caller used the minimal lifecycle image on a private VM outside Kubernetes. ANTA ran in a separate image.
Private evidence retains source hashes, image digests, ownership and Pod identities, catalogs, JSON and JUnit reports, and cleaner logs.

After testing, the operator removed the temporary cluster, workers, private runner, network, IAM grants, and registry.
A fresh independent cloud inventory found zero owned resources across all 15 infrastructure categories.
Baseline resources in ten inventory categories and the existing project remained intact.
Temporary access files were removed, and the default kubeconfig still matched its original hash.

The runtime used GKE `1.36.4-gke.2377000`, engineering EOS `4.36.1F-48405728.4361F`, private fork chart `0.0.0`, AVD `6.5.0`, and ANTA `1.10.0`.
The private runtime digest remained `sha256:d024ebf2e1a8322bb42fbf8a236985ba1f305de764db4c81fa005edebf329e12`.
No experimental EOS firewall rule was installed.
Switch probes retained the agreed TLS certificate-verification exception, password authentication, and EOS hostname comparison.
Kubernetes TLS verification remained enabled.

Some switch objects first reconciled before the operator supplied their registry Secret.
The operator requested another reconciliation for three switches after those Secrets arrived.
That action changed metadata only. It did not change switch inputs, images, or expiry.
Automatic image-access recovery remains unqualified under task 6.4.

This test covers two concurrent six-switch labs on the recorded private runtime.
Larger concurrency, 100-switch scale, AWS, the official clabernetes release, and the planned lifetime defaults remain unqualified.
This trusted harness does not qualify the planned Kubernetes admission or GitHub identity controls.

## November 12 lifecycle separation

The lifecycle core at commit `632d674c6a96acf856d9e91268361376b4bedbd4` passed standalone creation, authenticated status, and inventory retrieval on GKE.
Deletion and repeated deletion also passed.
All six switches authenticated with their expected hostnames and current Pod identities.
An invalid password prevented readiness.
The caller used a minimal Python image with PyYAML and kubectl, without AVD, ANTA, Ansible, or Google Cloud CLI.
It used an explicit Kubernetes context and a temporary Kubernetes service-account token.

The separate demo passed exactly 54 live ANTA results with the expected multiplicity, including both MLAG pairs.
It retained JSON, JUnit, catalogs, connection inventory, lifecycle events, and diagnostics before complete lab deletion.
The same cluster and shared switch workers served both cases.

A third request created a two-minute lab and exited without requesting deletion.
Independent observations recorded deletion starting 53 seconds after expiry and namespace removal within 105 seconds.
Its next scheduled job confirmed complete deletion 355 seconds after expiry.
The cleaner used the tested minimal image and its Kubernetes service-account token without cloud credentials.
Independent reads found all three lab records deleted, the same cluster and worker pools, and the unrelated namespace and Secret preserved.

The operator supplied worker capacity, scheduling policy, and registry access outside the lifecycle core.
For the tested private runtime, this included global pull-Secret references and credentials in each new lab namespace.
Both image pulls and controller metadata reads used that access.
The caller could not list cloud clusters, create Kubernetes roles or arbitrary Pods, or read an unrelated Secret.
These probes do not qualify the planned admission policy or GitHub identity controls.

The runtime used GKE `1.36.4-gke.2377000`, engineering EOS `4.36.1F-48405728.4361F`, private fork chart `0.0.0`, AVD `6.5.0`, and ANTA `1.10.0`.
It reused the recorded private runtime digest `sha256:d024ebf2e1a8322bb42fbf8a236985ba1f305de764db4c81fa005edebf329e12` without an experimental EOS firewall rule.
All 42 offline regression tests also passed at the tested commit.
Private evidence retains exact source hashes, input digests, image digests, Pod identities, and reports.
No GitHub workflow ran for these tests.

After testing, the operator deleted the shared cluster, workers, network, IAM grants, private runner, and registry.
Independent cloud inventory found zero owned resources across 15 infrastructure categories.
The existing project remained active, and baseline resources in ten inventory categories were preserved.

These results cover the six-switch example and the recorded private runtime.
They do not qualify the official clabernetes release, arbitrary topologies, 100-switch scale, concurrency, AWS, or the revised lifetime defaults.

## November 11 demo

The actual CLI passed its November 11, 2026 live acceptance run on GKE.
It produced exactly 54 successful ANTA results with the expected multiplicity, including both MLAG pairs.
The command saved JSON, JUnit, generated catalogs, connection inventory, lifecycle events, and available diagnostics.
It then deleted the lab completely and returned success.

Standalone create, authenticated status, invalid-password rejection, delete, and repeated delete also passed.
Both successful lifecycles used the same retained cluster and private GCE runner outside GKE.
Independent observations found no namespace, worker pool, or pending operation for either lab or the preceding failed lab.
The cluster identity and creation time remained unchanged.
All six switches reached readiness without observed Pod restarts in both successful lifecycles.

The CLI discovers current private Pod addresses through authenticated Kubernetes access.
It uses HTTPS on port 443 for readiness, status, ANTA, and diagnostics.
Password authentication and EOS hostname comparison remain required.
The private demo skips TLS certificate verification by explicit user agreement.

All 38 offline CLI tests pass.
They cover endpoint replacement, missing and duplicate Pods, invalid addresses, identity failures, report inventory preservation, and cleanup failures.
Ansible uses a separate inventory file so that test execution preserves the recorded Pod identities.
The existing AVD role still generates and executes the catalog.
The playbook enables privileged mode through `anta_enable` for generated ping tests.

A preceding live attempt authenticated to all six switches and retained 38 successes plus 16 ping execution errors.
The missing privileged-mode setting caused those errors.
That attempt timed out, saved its failed reports, and completed lab deletion.
The corrected retry kept the same 54 required results.

The private runner uses limited Kubernetes permissions bound to its authenticated numeric service-account identity.
A real runner probe passed ownership reads and namespace creation, and rejected permission-binding creation.
Namespace deletion permissions named only exact namespaces from labeled ownership records.
The successful run used no cluster-admin binding for the runner.

Final teardown deleted the cluster, private runner, shared infrastructure, and temporary registry after all tests completed.
The final inventory found zero owned resources across fifteen infrastructure categories.
The existing project remained active.
The active OpenSpec change remains unarchived, with 22 of 27 tasks complete.
Concurrent switch isolation, remaining failure-path qualification, scenario review, and GitHub integration remain open.

## Recorded runtime

The observed combination used GKE `1.36.4-gke.2377000` and engineering EOS `4.36.1F-48405728.4361F`.
The private fork chart reported `0.0.0`.
ANTA used version `1.10.0`, and catalog generation used AVD `6.5.0`.
Private provenance records retain the source hashes and exact runtime and CLI image digests.
The saved CLI `runtime.clabernetes` value records the requested chart version `0.11.0`.
The private harness records the observed fork and its override separately.
These results do not qualify the official published clabernetes release.

The separate experiment first passed all 54 live results, both MLAG pairs, and all six authenticated Pod-IP endpoints.
Focused Make conformance passed both reported tests with the race detector enabled.
The private source correction limits OUTPUT connection-tracking zone assignment to the existing management interfaces.
A controlled intervention recovered both MLAG pairs without a restart or switch configuration change.
A fresh corrected image then passed without manual runtime intervention.
No experimental EOS firewall rule was installed.

The earlier runtime restored its old rule before a later diagnostic capture, while the recovered sessions stayed connected.
That capture alone does not establish a persistent rule replacement.
The separate experiment used pinned certificates with TLS hostname matching disabled.
Its complete teardown and runtime evidence remain distinct from the later product CLI run.

## Historical November 10 test

The November 10, 2026 test reached six running switch pods with a local clabernetes patch.
Authenticated management readiness failed, so live ANTA and both MLAG pairs remain untested.
The operator stopped the final attempt before its readiness deadline.
The test installed no experimental firewall workaround.

## Runtime and source

The test used GKE `1.36.4-gke.2377000`, clabernetes chart `0.11.0`, and cEOS image version `4.36.1F`.
The local dependencies were PyAVD `6.5.0` and ANTA `1.10.0`.
These versions describe the initial attempts. They do not establish a supported combination.

The final attempt used a private clabernetes image built from commit `29ff39d5aee9d5633238d3c98f67e4a2057112d9` with the isolated patch.
The local chart identifies itself as `0.0.0`, although the environment requests published chart `0.11.0`.
Manager, planner, initialization, and node runtime images used the recorded private digest.
This experimental override does not establish compatibility with the unmodified published chart.

The example came from commit `7db631f7272309ad9766a666e486a1e804158d98`.
The local CLI and cleaner also included the two fixes below.
Private local provenance records contain the source patch and image digests.

## Observed behavior

- The cleaner image built and pushed to a private temporary registry.
- Infrastructure deployed, was destroyed completely, and deployed again in the same existing project.
- The corrected cleaner completed a Kubernetes job and read GKE pool and operation information through Workload Identity.
- Two canceled CLI attempts deleted their namespaces and worker pools, with no pending GKE operation afterward.
- A later lab request reused the existing cluster. Its cluster ID and creation time matched the earlier running-cluster snapshot.
- A readiness timeout returned a failed test outcome and completed namespace and worker-pool deletion.
- After SIGKILL stopped a separate test process, the scheduled cleaner deleted its abandoned lab without a manual deletion request.
- With the clabernetes patch, all six switch pods ran without restarts, all twelve links were accepted, and Kubernetes readiness conditions passed.
- Authenticated eAPI probes failed on every switch before live ANTA started.

Lab allocation on an existing cluster does not establish switch readiness.
The abandoned lab used a two-minute lifetime and did not reach switch readiness.
The cleaner recorded complete deletion 6 minutes 16 seconds after expiry.
An independent read found no namespace, worker pool, or pending GKE operation for that lab.
This single observation does not establish deletion timing during outages or concurrent switch isolation.

## Drydock fixes

The cleaner originally called `kubectl` without a usable kubeconfig and attempted to connect to localhost.
The cleaner now mounts a kubeconfig that reads the Kubernetes service account token and CA from their existing files.
The kubeconfig embeds no token.

Registry authentication originally used the complete JSON response from `gcloud auth print-access-token` as the password.
The CLI now extracts the response's `token` value before creating the private registry Secret.
The corrected live request passed registry metadata authentication and reached switch preparation.

Both fixes include regression tests. All 35 offline tests passed.
These tests do not establish live network acceptance.

## Preparation failure

The submitted topology binds `/drydock/interface_mapping.json` to `/mnt/flash/EosIntfMapping.json`.
clabernetes resolved complete payload paths but did not resolve the source within this bind string.
The imported cEOS preparation hook reads that source to select its management interface.
An isolated regression reproduced that preparation failure before the patch and passed afterward.

The patch resolves bind sources during preparation and later lifecycle hooks.
It preserves declared mount sources for plan generation, mount destinations, and mount options.
It adds no vendor-specific branch or firewall change.
All 1,214 executed upstream tests passed, and 15 tests were skipped.
Lint passed with zero findings.
The upstream cluster suite did not run because its required local SR-SIM license was absent.

Removing the mapping is not an accepted workaround.
The mapping preserves the bundled management interface and MLAG port identities.
Reference repositories remain unchanged.
The isolated checkout and its patch remain local. No upstream clabernetes PR was opened.

## Management readiness failure

All six localhost tunnel probes returned `SSLEOFError` with `UNEXPECTED_EOF_WHILE_READING` before authentication.
The inspected switch reported that HTTPS eAPI ran in the `MGMT` network namespace.
Port 443 listened there, but not in the default namespace used by Kubernetes port forwarding.
The inspected switch also reported that `Management1` did not exist, despite its declaration in the bundled configuration.
Its `MGMT` namespace contained no management interface.

These observations identify a separate management-access blocker. They do not prove its cause.
The final report contains no live ANTA results. The 54 earlier `unset` rows came from catalog generation in dry-run mode.
No switch configuration or firewall rule was changed to force acceptance.
The separate standalone create, status, and delete test on the running cluster did not run before the operator stopped testing.

## Final cleanup

The final attempt recorded cancellation and complete lab deletion.
All five retained lab records reported no namespace, worker pool, or pending operation.
Shared infrastructure destruction completed without errors.
An independent inventory found zero owned resources across all fifteen infrastructure categories.
The temporary private registry was deleted after infrastructure teardown.
The existing Google Cloud project remained active.

## Credential boundary

Cloud authentication, Docker authentication, kubeconfigs, lab credentials, bundles, and raw runtime files stay in ignored local directories.
Credential files use mode `0600`. Private runtime directories use mode `0700`.
The Docker build context excludes those files.
No live artifact or credential was pushed to GitHub during this validation session.
The final scan found no local credential values in the 53 candidate source files.
The private registry and project IAM policies contained no public access principal when inspected.

These November 10 observations do not establish network acceptance or standalone authenticated readiness.
Use the current evidence above for the later runtime result.
Keep incomplete product and lifecycle tasks unchecked.
