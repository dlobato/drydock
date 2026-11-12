# Digital twin pipeline

## Purpose

Test owner-approved PR commits through ephemeral labs while keeping Ansible execution, network acceptance, and reports under pipeline control.

## ADDED Requirements

### Requirement: Owner-authorized manual workflows

All GitHub workflows, including offline builds, MUST start only through an owner-authorized manual launch.
Push and pull-request events MUST NOT start jobs or allocate labs.
Manual launches and reruns by another actor MUST NOT receive the private runner or credentials.
Each run MUST identify the authorized commit.

#### Scenario: PR changes without a manual launch

- WHEN a PR opens or receives a new commit without owner authorization
- THEN no workflow job starts and no lab is allocated

#### Scenario: Owner launches a run

- WHEN the owner manually launches the trusted workflow for an identified PR commit
- THEN the run can execute against that exact commit
- AND it receives a distinct workflow-attempt identity

#### Scenario: Another actor launches or reruns

- WHEN another actor attempts a manual launch or rerun
- THEN the trusted workflow rejects that actor before private runner assignment or credential issuance
- AND permission to dispatch a GitHub workflow alone does not authorize a lab

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

- WHEN a new commit reaches the PR after a manual launch
- THEN the existing run continues to identify its originally selected commit
- AND testing the new commit requires a new owner-authorized launch

### Requirement: Private self-hosted runner

The workflow MUST use a dedicated self-hosted runner with private access to the Kubernetes API and switch management endpoints.
It MUST isolate Ansible build and test execution from credentialed lifecycle execution.
Ansible jobs MUST NOT receive Kubernetes credentials or cloud token issuance permissions.
Unapproved PR code MUST NOT execute on the private runner.
Fork execution MUST remain outside the initial trusted workflow.

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

- WHEN the owner launches the trusted workflow and its repository, actor, and workflow identity satisfy the configured trust
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
