# Proposal

## Why

Pull requests need temporary switch labs that the pipeline can test with its standard Ansible playbooks.
Drydock must supply those labs through clabernetes without depending on a cloud provider, a fixed fabric, or AVD test internals.

## What Changes

The November 12 review and November 13 workflow decisions establish the following target:

- Provide a CLI for lab creation, readiness, connection inventory, status, and deletion on an existing Kubernetes cluster with clabernetes.
- Accept arbitrary cEOS switch topologies and their complete rendered startup configurations. Use 100 switches per lab as the first scale target.
- Create a separate ephemeral lab for each approved workflow attempt. Support concurrent labs with identical device names and management addresses.
- Leave worker pools, autoscaling, networking, authentication setup, and registry access with the cluster operator.
- Leave AVD builds, ANTA execution, test policy, and report retention with the pipeline and its standard Ansible playbooks.
- Preserve admitted topology fields and delegate their network semantics to clabernetes. Limit lifecycle inspection to file delivery, safety policy, and readiness expectations.
- Run lint and unit tests automatically on every PR and update without custom author restrictions or cloud approval.
- Keep GKE pre-deployment testing opt-in for an identified PR commit. Require approval through the protected `gke` environment before lab work.
- Accept `[digital-twin-test]` in the latest PR commit as an opt-in request. Retain manual dispatch and native environment approval.
- Use a dedicated self-hosted runner with private connectivity and temporary, limited credentials for approved lab work. Keep personal cloud credentials out of GitHub.
- Wait for capacity within a startup deadline. Default lab lifetime to 30 minutes and limit it to 60 minutes from acceptance.
- Retain immediate deletion after completion and independent expiry after runner loss. Waiting for capacity does not extend expiry.

BREAKING: The lifecycle input no longer requires six fixed devices, AVD structured configurations, or a Google Artifact Registry address.
BREAKING: GKE infrastructure management and the integrated ANTA test command move outside the reusable lifecycle core.
The six-switch fabric remains an anonymized acceptance example with both MLAG pairs.

Task 8.1 implements automatic PR checks and a separate opt-in approval placeholder for an exact PR commit.
The user authorized the placeholder and commit marker to test native environment approval without cloud access or lab allocation.
Live GKE integration and runtime acceptance remain incomplete.

## Capabilities

### New Capabilities

- `switch-lab-lifecycle`: Provider-independent, concurrent cEOS labs with private management access, bounded waiting, ownership records, and independent cleanup.
- `digital-twin-pipeline`: Automatic PR lint and unit tests with optional, environment-approved pre-deployment labs through the lifecycle CLI and standard playbooks.
- `example-fabric`: An anonymized six-switch acceptance example that preserves routing, EVPN, VXLAN, switch-link, and both MLAG-pair coverage.

### Modified Capabilities

None. These capabilities remain in the active, unarchived change. No main specifications exist yet.

## Impact

Later implementation affects the CLI, topology admission, Kubernetes orchestration, endpoint discovery, cleaner, tests, examples, and GitHub workflow.
Cloud-specific demo setup remains separate from lifecycle operations.
AVD and ANTA dependencies belong to the example and pipeline. The lifecycle core does not interpret their structured configurations or results.
GKE is the current test platform. Kubernetes on AWS is a portability target that requires separate evidence.
The PR checks and approval placeholder provision no cloud resources.

The November 11 demo passed 54 ANTA results and complete lab deletion on the recorded private clabernetes build.
That evidence does not establish arbitrary topology support, 100-switch capacity, concurrent isolation, or AWS compatibility.
See the [live validation record](../../../docs/live-gke-validation.md) for the exact runtime and historical results.

CloudVision, host containers, interactive switch access, direct Containerlab execution, a central HTTP service, and a database remain excluded.
PR events without the marker start lint and unit tests without requesting GKE tests or lab approval.
Fork PRs can run those hosted checks under GitHub's native policies. Fork execution on private runners remains excluded.
The reference provides lifecycle behavior, not a requirement to reproduce ACT resource identifiers or its separate topology registry.
See the [reference notes](../../../docs/references.md). Reference repositories and private evidence remain unchanged.
