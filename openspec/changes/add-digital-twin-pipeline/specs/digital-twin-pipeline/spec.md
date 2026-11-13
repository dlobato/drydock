# Digital twin pipeline

## Purpose

Run automatic PR checks and optional approved lab tests before merge while keeping network acceptance and reports under pipeline control.

## ADDED Requirements

### Requirement: Automatic unrestricted PR checks

Lint and unit tests MUST run automatically when a PR opens, reopens, or receives a new commit.
These checks MUST NOT require a custom author allowlist, manual dispatch, or GKE environment approval.
They MUST use hosted runners without private lab access, cloud credentials, or cloud token issuance permissions.
Fork PRs MUST be eligible under GitHub's native execution policies.

#### Scenario: Contributor opens or updates a PR

- WHEN any contributor opens, reopens, or updates a PR
- THEN the lint and unit jobs start under GitHub's native execution policies without custom actor authorization
- AND those jobs do not receive GKE access or request a lab

#### Scenario: PR comes from a fork

- WHEN GitHub permits a fork PR workflow to execute
- THEN the same lint and unit jobs can run without a repository-specific author restriction
- AND no private runner or cloud access is granted

### Requirement: Opt-in pre-deployment tests

GKE pre-deployment tests MUST require an explicit request for an identified PR commit.
PR opening, reopening, and update events alone MUST NOT request lab work or create a pending GKE approval job.
Each requested run MUST identify its selected commit and distinct workflow attempt.
Automatic lint and unit results MUST remain independent of whether GKE testing is requested.

#### Scenario: PR changes without a GKE request

- WHEN a PR opens or receives a new commit without an explicit pre-deployment request
- THEN lint and unit tests can run
- AND no GKE job waits for approval or allocates a lab
- AND the absence of a GKE run does not report successful live network acceptance

### Requirement: Commit marker requests

The latest same-repository PR commit MUST use the literal, case-sensitive `[digital-twin-test]` marker to request approval.
The trusted workflow MUST read its message through GitHub without executing PR code.
Earlier marked commits and stale events MUST NOT request approval for a new head.
The marker MUST NOT bypass environment approval.
Manual dispatch MUST remain available as an alternative request.

#### Scenario: Latest PR commit requests the access probe

- WHEN an open same-repository PR into `main` opens, reopens, or updates with `[digital-twin-test]` in its latest commit message
- THEN the trusted workflow selects that exact event commit and requests `gke` approval
- AND lint and unit tests remain independent of that request
- AND the access probe requests only temporary scoped access after approval without allocating a lab or running NRFU

#### Scenario: New head has no marker

- WHEN a new PR head omits the marker but an earlier commit contains it
- THEN no approval job starts for that new head
- AND earlier requests retain their selected commits without authorizing the new head

#### Scenario: PR event is stale or comes from a fork

- WHEN the PR head differs from its event SHA or the PR comes from a fork
- THEN the marker selector requests no environment approval
- AND ordinary hosted PR checks remain eligible under GitHub's native policies

#### Scenario: Access probe runs before lab integration

- WHEN the user requests the access probe for a selected PR commit
- THEN the private access job waits for native `gke` environment approval
- AND it executes only the trusted workflow revision with temporary scoped credentials and allocates no lab
- AND successful completion reports only access and permission outcomes without claiming live network acceptance

### Requirement: Native environment approval for lab access

Requested tests MUST require the repository owner's approval through the protected `gke` environment before private runner assignment or credential issuance.
Native GitHub environment protection MUST enforce approval without custom actor authorization code.
A marker MUST only request that approval.

#### Scenario: Requested test receives approval

- WHEN a user requests a pre-deployment test and the owner approves its `gke` environment job
- THEN the run can test its identified PR commit before merge
- AND the run receives its own workflow-attempt identity

#### Scenario: Approval is absent or rejected

- WHEN a requested run does not receive environment approval
- THEN it receives no private runner or cloud credentials
- AND it allocates no lab

### Requirement: Trusted workflow and immutable input

Credentialed jobs MUST use a trusted workflow revision and pinned Drydock tool from the protected default branch.
They MUST treat admitted PR topology files as input data.
They MUST NOT execute PR-modified workflow or lifecycle code with Kubernetes credentials.
Build and test provenance MUST identify the exact commit and input digest.

#### Scenario: PR modifies the lifecycle tool

- WHEN an approved PR includes changes to Drydock or its workflow definition
- THEN the credentialed lifecycle job still uses the trusted pinned workflow and tool
- AND those PR changes cannot redefine its credential scope or approval condition

#### Scenario: PR receives another commit

- WHEN a new commit reaches the PR after a pre-deployment request
- THEN the existing run continues to identify its originally selected commit
- AND lint and unit tests run for the new commit without custom actor authorization
- AND GKE testing of the new commit requires a new explicit request and environment approval

### Requirement: Private self-hosted runner

Approved lab jobs MUST use a dedicated self-hosted runner with private access to the Kubernetes API and switch management endpoints.
The workflow MUST isolate Ansible build and test execution from credentialed lifecycle execution.
Ansible jobs MUST NOT receive Kubernetes credentials or cloud token issuance permissions.
Unapproved PR code MUST NOT execute on the private runner.
Private lab jobs MUST NOT execute fork code.

#### Scenario: Standard playbooks use private endpoints

- WHEN an authorized run receives a ready lab inventory
- THEN its runner can reach every returned private management endpoint
- AND no public switch management endpoint is required

#### Scenario: Ansible execution is isolated

- WHEN an authorized pipeline builds the lab input and runs ANTA
- THEN the Ansible processes and temporary state cannot access credentials issued to the separate lifecycle execution
- AND ANTA receives only the required lab management credentials and connection inventory

### Requirement: Temporary provider authentication

The workflow MUST use temporary, limited Kubernetes access from operator-configured authentication.
GKE integration MUST use trusted GitHub OIDC identity through Workload Identity Federation.
Personal cloud credentials, service-account key files, and reusable administrative kubeconfigs MUST NOT be stored in GitHub.
Provider-specific token exchange MUST remain outside the lifecycle core.

#### Scenario: Authorized GKE run obtains access

- WHEN an environment-approved run's repository, environment, and trusted workflow identity satisfy the configured trust
- THEN the provider issues temporary access for the authorized lab operations
- AND the job does not receive personal Google credentials or a service-account key

#### Scenario: Workflow access expires

- WHEN temporary workflow access expires or the runner disappears
- THEN the job cannot obtain broader or unauthorized access
- AND the independent cleaner retains its own authorized Kubernetes cleanup identity

### Requirement: Enforced lab permissions

The workflow identity MUST remain limited to the operator-authorized lab boundary through Kubernetes permissions and admission policy.
It MUST NOT administer IAM, worker capacity, RBAC, or unrelated resources.
Ownership labels alone MUST NOT establish authorization.
Credentials MUST remain absent from logs, caches, lifecycle output, and uploaded artifacts.

#### Scenario: Run attempts an unrelated operation

- WHEN a workflow identity attempts to read an unrelated Secret, change permissions, or allocate cloud workers
- THEN the authorization boundary denies the operation
- AND the job cannot grant itself additional permissions

#### Scenario: Unsafe topology bypasses the CLI

- WHEN the workflow identity sends an unsafe Topology directly to Kubernetes
- THEN the operator-installed admission webhook rejects execution hooks, unsupported devices, unsafe mounts, unapproved images, and external payloads
- AND the workflow cannot create Pods directly or read unrelated workloads and Secrets

#### Scenario: Admission is unavailable

- WHEN the admission service is unavailable or its certificate fails verification
- THEN restricted mutations fail closed without bypassing the lab policy
- AND the operator must restore admission before workflow allocation and cleaner deletion resume

### Requirement: Standard playbooks own network acceptance

The pipeline MUST build with standard AVD playbooks, request and wait for a Drydock lab, and run `arista.avd.anta_runner` independently.
It MUST apply returned connection details without discarding existing inventory groups or test variables.
The switches MUST boot with the complete proposed configuration without a required eAPI deployment stage.

#### Scenario: Build fails

- WHEN AVD cannot build the selected commit
- THEN the workflow fails before it requests a lab
- AND it retains safe build diagnostics

#### Scenario: Lab is ready

- WHEN Drydock returns authenticated management readiness for the admitted input
- THEN the pipeline runs its standard ANTA playbook with the returned connection details
- AND it determines network acceptance without asking Drydock to interpret ANTA results

### Requirement: Matching models and applicable coverage

The example pipeline MUST establish that its AVD models match the submitted startup files and contain required coverage before allocation.
The six-switch example MUST cover routing, EVPN, VXLAN, switch links, and both MLAG pairs.
Missing, skipped, errored, duplicate, or failed required results MUST prevent acceptance.
Other topologies MUST use their applicable pipeline test policy.

#### Scenario: Required coverage disappears

- WHEN the example catalog omits a required switch link or MLAG test, or its model differs from the startup configuration
- THEN the pipeline rejects the run before lab allocation
- AND Drydock does not need AVD structured configurations to enforce its lifecycle contract

#### Scenario: MLAG does not converge

- WHEN either example MLAG pair remains inactive or a required MLAG result is skipped
- THEN the workflow fails network acceptance
- AND it retains safe available diagnostics before requesting deletion

### Requirement: Reports retain provenance

The pipeline MUST retain safe ANTA JSON and JUnit reports, catalogs, available diagnostics, and lifecycle provenance under a finite retention policy.
Artifacts MUST identify the exact commit, workflow attempt, runtime versions, input digest, and lab.
Uploads MUST exclude credentials, startup files, Secret contents, and credential-bearing structured data.

#### Scenario: ANTA fails

- WHEN ANTA reports failure or an execution error
- THEN the pipeline attempts to retain available safe reports and diagnostics
- AND report collection does not convert the failed test result into success
- AND deletion does not depend on upload success

### Requirement: Cleanup is part of completion

The pipeline MUST request deletion after any lab allocation attempt, including success, failure, timeout, or cancellation.
Overall success MUST require passing required tests, retained reports, and complete lab deletion.
Test and cleanup failures MUST remain separate.
Independent expiry MUST cover runner loss that prevents immediate deletion.

#### Scenario: Tests pass but deletion fails

- WHEN all required network tests pass but lab deletion remains incomplete
- THEN the workflow does not report overall success
- AND it identifies the cleanup failure without changing the test result

#### Scenario: Cancellation interrupts deletion

- WHEN cancellation prevents the runner from completing deletion
- THEN the independent cleaner remains responsible for the expired lab
- AND the canceled run is not recorded as successful network acceptance

### Requirement: Concurrent ephemeral runs

Each owner-authorized workflow attempt MUST receive its own ephemeral lab.
Runs MUST NOT reuse another attempt's lab or cancel it merely because their PR, commit, or switch names match.
The workflow MUST fit startup and ANTA deadlines within the remaining 30-minute default or requested lifetime, up to 60 minutes.

#### Scenario: Several approved PR runs overlap

- WHEN several owner-authorized runs execute concurrently
- THEN each run tests its own admitted startup files through its own connection inventory
- AND completion or expiry of one run does not remove another run's lab
- AND waiting for capacity does not extend any run's accepted expiry
