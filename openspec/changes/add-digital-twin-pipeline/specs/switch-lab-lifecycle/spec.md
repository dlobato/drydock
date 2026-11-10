# Switch lab lifecycle

## Purpose

Supply temporary switch labs with observable infrastructure status, private management access, and bounded resource lifetime.

## ADDED Requirements

### Requirement: Complete identified lab input

Drydock MUST accept a complete Containerlab topology and rendered configurations for all requested switches.
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

#### Scenario: Management API unavailable

- WHEN any requested switch management API remains unreachable
- THEN Drydock does not report the lab ready
- AND it exposes the failed readiness condition for diagnostics

#### Scenario: Lab ready for network tests

- WHEN all requested switches and links exist and all management APIs are reachable from the runner
- THEN Drydock returns a connection inventory for every original switch name
- AND the pipeline remains responsible for protocol convergence and network acceptance

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
