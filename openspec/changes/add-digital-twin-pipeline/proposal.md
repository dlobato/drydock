# Proposal

## Why

Network changes need a temporary digital twin before deployment.
Drydock needs one small workflow that proves lab creation, network tests, report collection, and cleanup together.

## What Changes

The agreed first milestone will:

- Build an anonymized AVD fabric with two spines and two MLAG leaf pairs.
- Create a temporary cEOS lab from a complete topology and rendered configurations.
- Run ANTA from a private GitHub Actions runner with explicit MLAG coverage.
- Retain reports and diagnostics with the tested commit and lab identity.
- Delete temporary resources after success, failure, cancellation, timeout, and runner loss.

The infrastructure direction is GKE Standard with clabernetes and dedicated temporary workers per lab.
GitHub Actions owns AVD, ANTA, and reports. Drydock owns the lab lifecycle and management access.

Configuration delivery, the initial service boundary, expiry duration, and development infrastructure lifetime remain design decisions.
The supported runtime depends on the separate MLAG investigation.
No experimental firewall workaround is accepted.

CloudVision, host containers, fork contributions, production deployment, and 1,000-device qualification are outside this milestone.
No framework, database, or provisioning tool is selected by this proposal.

## Capabilities

### New Capabilities

- `example-fabric`: An anonymized six-switch AVD example that preserves the selected reference behavior.
- `switch-lab-lifecycle`: Temporary switch labs with private access, observable readiness, and cleanup independent of runner survival.
- `digital-twin-pipeline`: GitHub Actions orchestration with ANTA acceptance, reports, and failure visibility.

### Modified Capabilities

None. The repository contains no implemented capability specifications.

## Impact

Implementation will add the AVD example, lab lifecycle integration, GitHub Actions workflow, tests, and operator instructions.
The first offline example uses `pyavd[ansible]==6.5.0`, matching the current reference dependency.
The compatible cEOS, clabernetes, and Kubernetes versions still require evidence.

The sources are the Vantage digital twin pipeline and the PS EVPN-symmetric-IRB fabric.
See [the reference notes](../../../docs/references.md) for their local paths and observed limitations.
Source repositories remain unchanged. The bootstrap does not provision infrastructure or implement this proposal.
