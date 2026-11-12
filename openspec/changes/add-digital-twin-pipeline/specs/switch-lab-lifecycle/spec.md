# Switch lab lifecycle

## Purpose

Supply temporary cEOS switch labs through an existing clabernetes cluster with private management access, bounded waiting, and independent cleanup.

## ADDED Requirements

### Requirement: Lifecycle-only CLI

Drydock MUST provide CLI operations for lab creation, readiness, connection inventory, status, and deletion.
It MUST return machine-readable JSON and use a supplied Kubernetes context.
Lifecycle operations MUST NOT require AVD structured configurations, execute ANTA, or determine network acceptance.

#### Scenario: Producer does not use AVD

- WHEN a caller submits valid topology and startup files without AVD structured configurations
- THEN Drydock can manage the lab lifecycle
- AND the caller remains responsible for network tests and reports

### Requirement: Arbitrary supported topology

Drydock MUST derive switch names, counts, links, management addresses, and referenced startup files from the submitted Containerlab topology.
It MUST accept arbitrary cEOS topology shapes within documented limits.
It MUST reject unsupported devices, unsafe file references, and unsupported execution features before workload allocation.

#### Scenario: Topology differs from the example

- WHEN a supported topology uses different names, counts, links, addresses, or interface mappings from the six-switch example
- THEN Drydock admits the request without requiring the example's identities or link pattern
- AND it preserves the submitted switch identities

#### Scenario: Input is incomplete or unsafe

- WHEN a request omits a required file or includes a host container, execution hook, or unsupported host mount
- THEN Drydock reports the input error before creating switch workloads
- AND it does not copy files outside the admitted input

### Requirement: Complete startup delivery

Drydock MUST boot each switch with its submitted complete startup configuration.
It MUST record a digest that identifies the admitted topology and startup files together.
It MUST NOT require a separate configuration deployment step to reproduce the submitted configuration.

#### Scenario: Switch boots with the proposed configuration

- WHEN a caller supplies a topology and complete startup files
- THEN each switch boots with its corresponding submitted configuration
- AND lifecycle output identifies the admitted input digest

### Requirement: Identified workflow attempts

Each request MUST receive a unique lab identity and durable ownership before workload allocation.
The record MUST identify repository, exact commit, workflow run, attempt, input digest, acceptance time, expiry, and requested runtime.
Retries MUST NOT extend expiry or overwrite a newer deletion state.

#### Scenario: Two attempts use the same commit

- WHEN separate workflow attempts submit the same topology and commit
- THEN they receive distinct lab identities and ownership records
- AND deleting one does not delete the other

#### Scenario: Creation races with deletion

- WHEN deletion starts before a pending creation update completes
- THEN the late update cannot restore an active lab state or extend expiry
- AND cleanup continues to inspect the lab's owned resources

### Requirement: Cluster-managed capacity

Drydock MUST use operator-managed worker capacity and optional cluster autoscaling.
It MUST NOT provision or delete cloud workers, worker pools, networks, or IAM resources.
It MUST wait for capacity within a finite startup deadline and expose the waiting condition.
The deadline MUST NOT exceed the accepted lab expiry.

#### Scenario: Capacity arrives before the deadline

- WHEN some switches wait for capacity and the cluster supplies that capacity before the effective deadline
- THEN Drydock continues startup without a new lab request or expiry extension
- AND it reports ready only after every requested switch meets readiness conditions

#### Scenario: Capacity never arrives

- WHEN the startup deadline or lab expiry arrives before readiness
- THEN Drydock reports startup failure and requests deletion of its partial lab
- AND it does not delete or preempt another lab
- AND independent cleanup remains responsible if the caller disappears

### Requirement: Infrastructure readiness and connection inventory

Drydock MUST report ready only when all requested switches and links exist and the runner can authenticate to every management API.
It MUST return connection details under the original switch names.
Readiness MUST NOT imply routing convergence or ANTA success.

#### Scenario: Lab is ready for network tests

- WHEN all requested switches and links exist and every management API accepts authentication with the expected device identity
- THEN Drydock reports ready and returns connection inventory for every switch
- AND the caller can apply that inventory to its existing Ansible inventory
- AND the pipeline remains responsible for convergence and network acceptance

#### Scenario: Management API fails

- WHEN a switch management API is unreachable, rejects authentication, or reports an unexpected hostname
- THEN Drydock does not report the lab ready
- AND status identifies the failed readiness condition without exposing credentials

### Requirement: Private endpoint discovery

Management access MUST use private Pod-IP HTTPS from an authorized external runner.
Drydock MUST discover current endpoints through authenticated Kubernetes access and retain switch names and Pod identities.
It MUST reject missing, duplicate, or invalid endpoints.
The private demo's switch TLS exception MUST NOT disable Kubernetes or cloud endpoint verification.

#### Scenario: Switch Pod changes during readiness

- WHEN a switch Pod is replaced before readiness completes
- THEN the next readiness attempt discovers its current address and identity
- AND missing or duplicate endpoints prevent readiness
- AND returned inventory identifies the current Pod name and UID

### Requirement: Concurrent switch-only isolation

Drydock MUST support several simultaneous ephemeral cEOS labs, including labs with identical switch names and management addresses.
It MUST keep their workloads, startup files, ownership, and connections separate.
Labs MUST NOT introduce CloudVision or host containers.

#### Scenario: Delete one of several labs

- WHEN several labs share cluster capacity and one lab is deleted
- THEN the other labs remain reachable with their original identities
- AND their links and network acceptance remain unaffected
- AND the deleted lab does not expose a public management endpoint

### Requirement: Thirty-minute default lifetime

Lab lifetime MUST default to 30 minutes and MUST NOT exceed 60 minutes from request acceptance.
Nonpositive lifetimes and values above 60 minutes MUST fail before allocation.
Capacity waiting, startup, and tests MUST consume that same lifetime without renewal by retry.

#### Scenario: Lifetime is omitted

- WHEN a caller requests a lab without a lifetime value
- THEN its recorded expiry is 30 minutes after acceptance
- AND waiting for capacity does not move the recorded expiry

#### Scenario: Maximum is exceeded

- WHEN a caller requests a nonpositive lifetime or more than 60 minutes
- THEN Drydock rejects the request before workload allocation

### Requirement: Repeatable ownership-based deletion

Drydock MUST support deletion after any allocation attempt and report incomplete deletion as a failure.
Complete deletion MUST require removal of owned lab resources and prevention of further allocation.
It MUST preserve unrelated resources, shared capacity, and credential-free outcome records.

#### Scenario: Repeat deletion

- WHEN deletion runs again for an already deleted lab
- THEN it succeeds without changing another lab or shared cluster resources

#### Scenario: Backend deletion fails

- WHEN Kubernetes or clabernetes cannot remove an owned lab resource
- THEN Drydock reports incomplete cleanup and retains the ownership record for retry
- AND it does not report the lab fully deleted or force-remove finalizers

#### Scenario: Shared workers remain

- WHEN all owned lab resources are deleted but cluster-managed workers remain
- THEN those workers do not prevent a successful lab deletion result
- AND the cluster operator retains responsibility for worker scale-down and cost

### Requirement: Cleanup independent of runner survival

An independent cluster-side cleaner MUST reclaim expired and deleting labs every five minutes and retry incomplete deletion indefinitely.
The deletion target MUST remain 30 minutes after expiry while Kubernetes and backend APIs are available.
Overdue cleanup MUST remain visible.
The cleaner MUST NOT require personal or cloud administration credentials.

#### Scenario: Runner disappears

- WHEN the runner disappears after partial or complete allocation
- THEN the cleaner discovers the expired lab independently of GitHub
- AND it removes only that lab's owned resources within the documented target
- AND the record identifies deletion timing and outcome

#### Scenario: Allocation appears late

- WHEN an owned workload becomes visible after an initial deletion attempt
- THEN the cleaner discovers it through the retained lab identity and removes it
- AND the accepted expiry does not change

#### Scenario: Cleanup is overdue

- WHEN cleanup remains incomplete more than 30 minutes after expiry
- THEN the ownership record identifies overdue cleanup
- AND deletion continues to retry every five minutes without a retry limit

### Requirement: Provider-independent authorization boundary

Drydock MUST consume supplied Kubernetes access without requiring cloud-specific lifecycle arguments or registry token commands.
It MUST remain within the operator-authorized lab boundary and exclude credentials from retained output.
Its operations MUST NOT require cloud administration or cluster-admin access.

#### Scenario: Cluster provider changes

- WHEN an operator supplies another conforming Kubernetes cluster with clabernetes, private routing, registry access, and scoped credentials
- THEN the same lifecycle interface accepts the lab without Google project, zone, or registry assumptions
- AND provider-specific authentication and capacity setup remain outside Drydock

#### Scenario: Credentials are insufficient

- WHEN supplied access does not authorize a required lab operation
- THEN Drydock reports the denied operation without seeking broader credentials or changing authorization policy
- AND any partial allocation retains an ownership record for authorized cleanup

### Requirement: Measured scale acceptance

The first scale acceptance MUST demonstrate one 100-switch lab through creation, private management readiness, pipeline-run ANTA, and complete deletion.
Separate concurrent tests MUST demonstrate lab isolation.
Evidence MUST state runtime versions, startup duration, resource requirements, cleanup timing, and qualified aggregate capacity.

#### Scenario: Scale milestone is assessed

- WHEN acceptance results are published for the revised lifecycle tool
- THEN they identify the tested switch count and simultaneous lab count
- AND a six-switch result or successful topology submission alone does not establish the 100-switch target
- AND no untested provider or runtime combination is described as qualified
