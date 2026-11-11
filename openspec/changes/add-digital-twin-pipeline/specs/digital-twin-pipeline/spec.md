# Digital twin pipeline

## Purpose

Test proposed network changes through a temporary lab and retain results that identify the exact workflow attempt and commit.

## ADDED Requirements

### Requirement: Trusted private workflow

The delivery MUST provide the CLI demo before GitHub Actions integration.
The eventual workflow MUST support trusted contributors in private GitHub repositories.
It MUST build with AVD, request a lab, wait for infrastructure readiness, run ANTA, retain available results, and request deletion.
Lab access MUST use an authorized private runner.

#### Scenario: Build fails

- WHEN AVD cannot build the proposed fabric
- THEN the workflow fails before it requests a lab
- AND it retains the available build diagnostics

#### Scenario: Trusted change completes

- WHEN an authorized workflow runs against a valid example
- THEN it tests configurations from the identified commit and workflow attempt
- AND it uses the returned connection inventory for ANTA

### Requirement: Explicit network acceptance

The workflow MUST test routing, EVPN, VXLAN, and both MLAG pairs against expected results.
Required tests that fail, error, or do not run MUST prevent a passing result.
Unavailable endpoint links MUST NOT justify excluding required switch links or MLAG coverage.

#### Scenario: MLAG does not converge

- WHEN either MLAG pair remains inactive or a required MLAG test is skipped
- THEN the workflow fails network acceptance
- AND it retains available MLAG diagnostics before deletion

### Requirement: Reports retain provenance

The workflow MUST retain ANTA reports in JSON and JUnit, the test catalog, logs, and available failure diagnostics.
Artifacts MUST identify the tested commit, workflow attempt, runtime versions, and lab.
Artifact collection MUST exclude credentials and authentication material.

#### Scenario: ANTA fails

- WHEN ANTA reports a failed test or execution error
- THEN the workflow attempts to save available reports and diagnostics
- AND report collection does not convert the failed test result into success
- AND lab deletion does not depend on report upload success

### Requirement: Cleanup is part of completion

The workflow MUST request cleanup after any lab allocation attempt.
A successful run MUST require passing network tests and evidence of completed resource deletion.
The workflow MUST preserve test failures and report cleanup failures separately.
Independent lab expiry MUST cover cancellation or runner loss that prevents workflow cleanup.

#### Scenario: Tests pass but deletion fails

- WHEN all network tests pass but temporary resource deletion remains incomplete
- THEN the workflow does not report overall success
- AND it identifies the remaining cleanup failure

#### Scenario: Workflow is canceled

- WHEN cancellation prevents the runner from completing deletion
- THEN the independent lab expiry mechanism remains responsible for resource deletion
- AND the canceled run is not recorded as a successful network acceptance run


### Requirement: AVD-managed ANTA catalogs

The test command MUST use `arista.avd.anta_runner` to generate catalogs from bundled AVD structured configurations and execute ANTA.
It MUST reject missing mandatory coverage before allocation and retain generated catalogs and expected result counts.
Dry-run reports MUST NOT establish network acceptance.

#### Scenario: Required coverage disappears

- WHEN a generated catalog omits a required switch link or MLAG test
- THEN the CLI rejects the request before lab allocation
- AND interface tests must include every switch link and leaf VXLAN interface
- AND unused endpoint exclusions must preserve required switch coverage

#### Scenario: The CLI test completes

- WHEN a valid bundle passes bounded AVD-managed ANTA tests
- THEN the CLI retains available reports and deletes the lab
- AND overall success requires complete deletion and successful report collection
