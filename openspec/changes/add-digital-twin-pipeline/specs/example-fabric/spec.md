# Example fabric

## Purpose

Provide a small anonymized AVD acceptance fabric without constraining the names, counts, or shapes accepted by the reusable lifecycle tool.

## ADDED Requirements

### Requirement: Six-switch reference topology

The example MUST contain two spines and four leaves arranged as two MLAG pairs.
It MUST preserve the selected reference behavior for EVPN symmetric IRB, routing, VXLAN, and MLAG.
The example MUST NOT define fixed identities or a device-count limit for Drydock lifecycle operations.

#### Scenario: Build the example

- WHEN a contributor builds the supplied inventory with the documented AVD version
- THEN the build produces intended configurations for exactly six example switches
- AND the topology preserves two MLAG pairs and all leaf-to-spine connections

#### Scenario: Build anonymized MLAG peer VLANs

- WHEN a contributor builds the example with reference VRF VNIs 1001 and 1002
- THEN all four leaves use peer VLANs 4000 and 4001 for VRF_A and VRF_B
- AND generated VLAN IDs and VLAN interface numbers stay within 1 through 4094
- AND the primary MLAG interface Vlan4094 stays in the default VRF

### Requirement: Anonymous source data

The example MUST use generic device and tenant names, synthetic addresses and identifiers, and credentials supplied at runtime.
It MUST build without the source repository and MUST leave that repository unchanged.

#### Scenario: Use a clean checkout

- WHEN a contributor builds a clean Drydock checkout with documented dependencies and lab credentials
- THEN no customer data, source credentials, or absolute workspace paths are required
- AND generated configurations use only the synthetic example identity

### Requirement: Switch-only lab topology

The example lab MUST deploy switches only.
Endpoint definitions used by AVD MUST NOT create host containers.
The topology MUST NOT include CloudVision.
The complete rendered startup files MUST enable private HTTPS eAPI for authenticated readiness and ANTA execution.

#### Scenario: Prepare the lab input

- WHEN the workflow prepares a Containerlab topology and startup files from the example
- THEN every deployed device is a supported cEOS switch
- AND no CloudVision or host container is requested
- AND no separate configuration deployment stage is required after boot

### Requirement: Separate lifecycle and AVD test inputs

The example MUST produce topology and startup files suitable for the lifecycle CLI.
Matching AVD structured configurations MUST remain available to the pipeline for catalog generation and ANTA execution.
The pipeline MUST establish model and startup consistency before allocation.
Lifecycle admission MUST NOT require AVD models.

#### Scenario: Prepare example artifacts

- WHEN the pipeline builds and packages the example
- THEN the admitted input digest identifies its topology, startup files, and supported auxiliary files
- AND the pipeline can generate catalogs from the matching AVD models without passing them to the lifecycle CLI
- AND uploaded reports exclude bundled authentication material

### Requirement: Example acceptance remains explicit

The example workflow MUST require routing, EVPN, VXLAN, switch-link, and both MLAG-pair coverage through the standard ANTA playbook.
It MUST distinguish offline consistency from live network acceptance.
The 100-switch scale target MUST use additional evidence beyond this six-switch example.

#### Scenario: Offline build passes

- WHEN the example builds and generates catalogs without contacting switches
- THEN the result establishes only offline consistency
- AND it does not establish live MLAG, 100-switch capacity, concurrent isolation, or provider compatibility

#### Scenario: Live example passes

- WHEN all required example tests pass and owned lab resources are deleted
- THEN the evidence identifies the exact runtime, input, and workflow attempt
- AND it preserves both MLAG-pair results without an experimental EOS firewall workaround
