# Switch lab lifecycle

## Purpose

Supply temporary switch labs with observable infrastructure status, private management access, and bounded resource lifetime.

## ADDED Requirements

### Requirement: Complete identified lab input

Drydock MUST accept a complete Containerlab topology, rendered startup configurations, and matching AVD structured configurations for every requested switch.
Each lab MUST identify its repository, tested commit, workflow run, attempt, and expiry.
Unsupported device kinds or missing configurations MUST fail before lab allocation.

#### Scenario: Reject incomplete input

- WHEN a request omits a switch configuration or requests an unsupported device
- THEN Drydock reports the input error without allocating lab resources

#### Scenario: Separate concurrent runs

- WHEN two workflow attempts request the same fabric
- THEN each lab receives a distinct identity and resource ownership
- AND both retain the exact tested commit

### Requirement: Infrastructure readiness and management access

Drydock MUST report ready only when all requested switches and links exist and the runner can reach every management API.
It MUST preserve original switch identities in the returned connection inventory.
Infrastructure readiness MUST NOT imply routing convergence or ANTA success.
The operator MUST run outside GKE.
Management access MUST NOT require interactive switch access.

#### Scenario: Management API unavailable

- WHEN any requested switch management API remains unreachable
- THEN Drydock does not report the lab ready
- AND it exposes the failed readiness condition for diagnostics

#### Scenario: Lab ready for network tests

- WHEN all requested switches and links exist and all management APIs are reachable from the runner
- THEN Drydock returns a connection inventory for every original switch name
- AND the pipeline remains responsible for protocol convergence and network acceptance

### Requirement: Private Pod-IP transport

Management access MUST use private Pod-IP HTTPS from the external runner.
The CLI MUST discover current endpoints through authenticated Kubernetes access and retain original switch names and Pod identities.
The demo MUST authenticate with the runtime password and compare reported EOS hostnames with expected switch names.
The demo skips TLS certificate verification by user agreement and MUST NOT claim certificate-based identity.

#### Scenario: A switch Pod changes during readiness

- WHEN a switch Pod is replaced before authenticated readiness completes
- THEN the next readiness attempt discovers its current Pod IP and identity
- AND missing or duplicate switch Pods prevent readiness
- AND an unexpected EOS hostname prevents readiness

### Requirement: Private switch-only resources

Drydock MUST allocate switch-only labs and private management access for authorized runners.
It MUST keep temporary lab resources separately owned from shared infrastructure and other labs.

#### Scenario: Delete one of two labs

- WHEN two labs share the control plane and one lab is deleted
- THEN the other lab and shared infrastructure remain available
- AND the deleted lab does not expose a public management endpoint

### Requirement: Cleanup independent of runner survival

Drydock MUST delete temporary lab resources after success, failure, cancellation, or timeout.
An expiry mechanism independent of the workflow runner MUST also reclaim abandoned labs.
Deletion MUST be repeatable and report incomplete cleanup as a failure.

#### Scenario: Runner disappears

- WHEN a workflow runner disappears after partial or complete lab allocation
- THEN the independent expiry mechanism deletes the owned temporary resources within the documented cleanup bound
- AND the cleanup record identifies the lab and deletion outcome

#### Scenario: Repeat deletion

- WHEN deletion runs again for an already deleted lab
- THEN it succeeds without deleting resources owned by another lab or shared infrastructure

#### Scenario: Provider deletion fails

- WHEN a provider cannot delete an owned resource
- THEN Drydock reports cleanup incomplete and retains the ownership record for retry
- AND it does not report the lab fully deleted

### Requirement: On-demand demo infrastructure

Drydock MUST deploy shared GKE Standard infrastructure through scripted `gcloud` commands in an existing dedicated demo project.
The operator MUST destroy that infrastructure manually after the session.
Infrastructure destruction MUST preserve the existing project and unrelated resources.
The CLI MUST retain ownership before allocation and MUST report unknown or remaining resources as incomplete teardown.
There MUST be no automatic expiry service for shared infrastructure.

#### Scenario: Complete a demo session

- WHEN the operator destroys an owned demo environment
- THEN Drydock waits for cluster deletion before removing owned network and identity prerequisites
- AND it reports final inventory results without deleting the project

#### Scenario: Deployment stops partway

- WHEN deployment stops after a partial allocation
- THEN the local ownership record remains available for repeatable destruction
- AND Drydock refuses to adopt preexisting resources

### Requirement: Numeric lab expiry

Lab lifetime MUST default to 120 minutes and MUST NOT exceed 240 minutes from request acceptance.
Kubernetes MUST retain ownership before the first provider allocation.
An independent cleaner MUST run every five minutes and retry incomplete deletion indefinitely.
Stale state updates MUST NOT overwrite newer cleanup state.

#### Scenario: Allocation completes late

- WHEN an asynchronous allocation becomes visible after an initial deletion attempt
- THEN the cleaner discovers it from the retained lab identity and removes only owned resources
- AND the delay does not extend the accepted expiry

#### Scenario: Cleanup exceeds its target

- WHEN cleanup remains incomplete more than thirty minutes after expiry
- THEN its ownership record identifies overdue cleanup
- AND the deletion target remains thirty minutes after expiry while cloud and Kubernetes APIs are available
- AND incomplete deletion retries every five minutes
- AND the cleaner continues retrying without a retry limit
