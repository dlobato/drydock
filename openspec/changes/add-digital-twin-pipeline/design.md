# Design

## Context

The offline six-switch example and deterministic Containerlab bundle already exist.
The user accepted a CLI-first demo with startup delivery, Kubernetes ownership records, finite lab expiry, and manual shared teardown.
The user also selected `arista.avd.anta_runner` to own ANTA catalogs.
The [operator instructions](../../../docs/demo-flow.md) describe the implemented commands and remaining validation boundary.

The initial authorized GKE test reached six running switch pods, but authenticated management readiness failed through Kubernetes port forwarding.
The separate November 11 experiment passed all 54 live ANTA results and both MLAG pairs with the corrected private runtime.
The external runner used private Pod-IP access.
The actual CLI subsequently passed all 54 results, retained reports, and complete lab deletion.
Standalone create, authenticated status, invalid-password rejection, and repeated deletion also passed on the retained cluster.
See [the live validation record](../../../docs/live-gke-validation.md) for evidence and limits.

## Goals / Non-Goals

Connect the six-switch example to temporary GKE workers, observable readiness, AVD-managed acceptance, retained reports, and independent cleanup.
Keep the runner outside GKE and preserve original switch names.
Do not add an HTTP service, database, interactive access command, host container, CloudVision, or automatic infrastructure expiry.
Do not modify references or install the experimental MLAG firewall rule.

## Decisions

### Keep the existing offline build

Use `pyavd[ansible]==6.5.0` with the matching `arista.avd` collection.
Keep the original example build separate from the Containerlab digital twin build.
The digital twin removes unsupported BGP convergence commands and enables HTTPS eAPI in the management VRF.
AVD digital twin metadata excludes unused endpoint interfaces from validation.
Required spine and MLAG peer links remain included.
Generated artifacts stay ignored and private.
Use the reference VNIs 1001 and 1002 for VRF_A and VRF_B.
AVD derives valid MLAG peer VLANs 4000 and 4001 without explicit overrides.
Test generated VLAN numbers because AVD 6.5.0 accepts out-of-range values in structured configurations.

### Bundle the complete AVD input

Package the topology, interface mapping, six rendered startup configurations, and six matching AVD structured configurations.
Normalize archive metadata and record its SHA-256 digest.
Require a digest-pinned cEOS image in regional Artifact Registry at runtime.
Reject unsafe members, extra files, missing devices, unsupported topology attributes, and invalid identities before allocation.
Render each structured configuration with the pinned PyAVD version and compare it with the submitted startup configuration.
This prevents testing a different AVD model from the configuration that boots.
The archive contains authentication material and is never a retained public report.

### Use the platform CLIs

The Python CLI uses `gcloud`, `kubectl`, and Helm with explicit project and zone values.
It does not change the active Google Cloud project or the default kubeconfig.
A private local journal records infrastructure ownership before allocation.
A deployment creates a network, subnet, system pool, service accounts, an IAM role, clabernetes, and the cluster-side cleaner.
One invocation waits for deployment and configuration.
A failed or interrupted deployment retains the journal for manual destruction.
A completed teardown permits another demo session, including restoration of its owned soft-deleted IAM role.

Use an existing dedicated demo project, existing registry, and uploaded licensed images.
Do not create or delete the project, registry, images, or enabled APIs.
The operator supplies explicit GKE and chart versions and a digest-pinned cleaner image.
Limit runtime evidence to the exact recorded private build until another combination passes live acceptance.

### Allocate a dedicated lab pool

Create a unique lab ID and a durable Kubernetes ConfigMap before requesting workers.
Record repository, commit, run, attempt, acceptance time, expiry, bundle digest, and requested runtime.
Allocate two temporary `e2-standard-4` workers with lab labels and a scheduling taint.
Create a separate namespace and private Secrets for startup files, the interface mapping, and registry authentication.
Constrain every lab pod to its owned pool.
Use a unique management network name while preserving synthetic switch addresses and names.
Live concurrent-lab isolation remains an acceptance requirement.

Updates require Kubernetes resource versions.
A stale allocation update cannot overwrite cleanup state.
Check the allocation lease between resource requests.
Retain records after deletion and revisit them to catch late asynchronous allocation.

### Keep access inside the test command

Require current topology generation, ready switch conditions, accepted links, and ready pods without restarts.
Require private ClusterIP eAPI services.

Discover one current Pod for each original switch name through authenticated Kubernetes access.
Reject missing or duplicate switch Pods and missing or invalid private IPv4 endpoints.
Refresh endpoint discovery on every readiness attempt and record the Pod name and UID with its address.
Use the same private Pod-IP HTTPS endpoints for readiness, status, ANTA, and diagnostics.

Authenticate to eAPI and compare reported EOS hostnames with the bundle.
The external runner requires private routes and TCP port 443 access to the Pods.
Kubernetes Service DNS and ClusterIP routing from a VM are not prerequisites for this direct path.
The private demo skips TLS certificate verification by explicit user agreement.

Do not retrieve or pin switch certificates. Keep password authentication and EOS hostname comparison.
The runner sends credentials before it reads the EOS hostname, without certificate-based proof of the switch identity.

Keep the existing AVD role for both catalog generation and execution.
Return original switch names, private Pod addresses, and Pod identities from status.
Keep Management1 and HTTPS eAPI in MGMT. Do not enable default-VRF eAPI to repair forwarding.
Infrastructure readiness does not establish routing convergence.

### Let AVD manage ANTA catalogs

Run the pinned `arista.avd.anta_runner` role in dry-run mode before lab allocation.
It reads the private bundled structured configurations and saves per-device catalogs.
Select documented generated tests for BGP peer sessions, interface state, LLDP, port channels, MLAG, VXLAN consistency, reachability, and route presence.
Enable extra fabric validation for underlay reachability and routes.
Do not hand-build a second catalog or copy expected peer addresses and VNIs into Drydock.

Inspect the generated catalogs for mandatory test classes on every relevant device.
Require every switch-link interface and each leaf Vxlan1 interface in the generated interface test.
Run the same role with private Pod-IP addresses for bounded convergence attempts.
Enable privileged mode through `anta_enable` for generated ping tests.
A new role invocation creates fresh ANTA clients and command caches.
Retain the expected multiplicity of generated device-test results.
Missing, extra duplicate, skipped, errored, or failed required results prevent acceptance.
A dry-run result never proves network acceptance.

### Separate tests, reports, and cleanup

The test command validates input and generates catalogs before allocation.
After any allocation attempt, it attempts deletion even if ANTA, diagnostics, report writing, or cancellation fails.
It handles SIGINT and SIGTERM and ignores repeated interrupts during immediate cleanup.
Independent expiry covers SIGKILL and operator or runner loss.
A zero exit code requires passing acceptance, saved reports, and complete lab deletion.
Preserve test and cleanup failures separately.

Retain AVD catalogs and reports, JUnit conversion, safe protocol diagnostics, lifecycle events, provenance, and requested and observed versions.
Do not retain startup files, Secrets, raw manifests, arbitrary container logs, or authentication material.
Keep structured configurations in a private temporary directory outside the report tree.
Report upload and retention policy belong to later GitHub integration.

### Expire labs independently

Default lifetime is 120 minutes, with a maximum of 240 minutes from acceptance.
The cluster-side CronJob runs every five minutes on the shared system pool.
Workload Identity supplies Google credentials without a key file.
Refresh registry tokens for active labs because their lifetime exceeds a single token lifetime.
Delete expired or deleting labs and retry every five minutes indefinitely.
Deletion inspects owned namespaces, worker pools, and pending GKE operations.
A missing namespace alone does not establish complete cleanup.

Target complete deletion within thirty minutes after expiry while provider APIs are available.
Flag overdue records and retain incomplete cleanup outcomes.
Do not remove finalizers forcibly or delete resources with different ownership.
The timing target requires live evidence and can be exceeded during outages.

### Destroy shared infrastructure manually

The operator deploys shared infrastructure for a session and destroys it afterward.
No automatic infrastructure expiry service runs.
Destroy the owned cluster before removing its network and service accounts.
Keep prerequisites if cluster deletion fails.
Remove only owned project IAM bindings and resources.
Make destruction repeatable and preserve the existing project.
Retain final inventory counts for infrastructure, dependent compute and network resources, and IAM bindings.
Unknown inventory or remaining resources prevents a successful teardown result.
Report unknown leftovers for operator action instead of deleting them blindly.

## Risks / Trade-offs

The separate MLAG experiment passed a cold start without an EOS firewall exception.
It scoped OUTPUT connection-tracking zone assignment to the existing management interfaces in the private clabernetes runtime.
The tested combination used GKE `1.36.4-gke.2377000`, engineering EOS `4.36.1F-48405728.4361F`, and fork chart `0.0.0`.
ANTA `1.10.0` executed the 54 AVD-generated results with exact expected multiplicity.

Both MLAG pairs and all six authenticated endpoints passed, as did focused Make conformance with the race detector.
Independent inventory found zero owned resources across fifteen infrastructure categories after teardown.
The subsequent actual CLI run passed all 54 results with exact expected multiplicity and complete lab deletion.
Standalone lifecycle tests and independent lab cleanup observations also passed.
Both lifecycles retained the same cluster identity and creation time.
The evidence does not qualify official clabernetes `0.11.0`.

Live tests cover the cleaner image build, infrastructure deployment, cleaner authentication, and cancellation cleanup.
Independent expiry deleted a lab after runner loss, with complete deletion observed 6 minutes 16 seconds after expiry.
The earlier failed port-forward test remains historical evidence.
Concurrent switch isolation and the remaining failure-path qualification remain unproven.
Offline mocks do not establish those behaviors on Google Cloud.

The six-switch catalog tests switch and protocol state plus generated switch-to-switch reachability.
It does not establish tenant application traffic through attached hosts.
Endpoint containers remain excluded.

Shared infrastructure continues to cost money until the operator destroys it.
A lost local journal requires ownership investigation before shared teardown.
The initial cleaner permissions assume a dedicated demo cluster and project.

## Migration Plan

No production deployment exists to migrate.
The bundle now includes six structured configurations. Rebuild old bundles before using the CLI.
Deliver the CLI and offline gates first.
Run an explicitly authorized demo and failure-path acceptance before adding automatic live GitHub triggers.
Keep the cleaner active until every lab is deleted.
Keep this OpenSpec change active until implementation, live evidence, and review are complete.

## Open Questions

Qualify concurrent isolation and the remaining failure paths before archive or additional runtime combinations.
Select artifact retention and runner policy when adding GitHub Actions orchestration.
