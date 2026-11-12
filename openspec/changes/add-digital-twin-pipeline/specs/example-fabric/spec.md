# Example fabric

## Purpose

Provide a small anonymized AVD fabric that contributors can build and test without access to the source reference.

## ADDED Requirements

### Requirement: Six-switch reference topology

The example MUST contain two spines and four leaves arranged as two MLAG pairs.
It MUST preserve the selected reference behavior for EVPN symmetric IRB, routing, VXLAN, and MLAG.

#### Scenario: Build the example

- WHEN a contributor builds the supplied inventory with the documented AVD version
- THEN the build produces intended configurations for exactly six switches
- AND the topology preserves two MLAG pairs and all leaf-to-spine connections

#### Scenario: Build anonymized MLAG peer VLANs

- WHEN a contributor builds the example with the reference VRF VNIs 1001 and 1002
- THEN all four leaves use peer VLANs 4000 and 4001 for VRF_A and VRF_B
- AND generated VLAN IDs and VLAN interface numbers stay within 1 through 4094
- AND the primary MLAG interface Vlan4094 stays in the default VRF

### Requirement: Anonymous source data

The example MUST use generic device and tenant names, synthetic addresses and identifiers, and credentials supplied at runtime.
It MUST build without the source repository and MUST leave that repository unchanged.

#### Scenario: Use a clean checkout

- WHEN a contributor builds a clean Drydock checkout with the documented dependencies and lab credentials
- THEN no customer data, source credentials, or absolute workspace paths are required
- AND generated configurations use only the synthetic example identity

### Requirement: Switch-only lab topology

The example lab MUST deploy switches only.
Endpoint definitions used by AVD MUST NOT create host containers.
The topology MUST NOT include CloudVision.

#### Scenario: Prepare the lab input

- WHEN the workflow creates a Containerlab topology from the example
- THEN every deployed device is a supported switch
- AND no CloudVision or host container is requested


### Requirement: Portable AVD test inputs

The bundle MUST include the structured configurations that correspond to all six rendered startup configurations.
The digital twin build MUST enable HTTPS eAPI for ANTA.
The CLI MUST reject mismatches between rendered and structured configurations before allocation.
The offline workflow MUST NOT upload bundled authentication material.

#### Scenario: Rebuild a lab bundle

- WHEN the operator packages the digital twin build
- THEN the bundle digest identifies the topology, mapping, startup configurations, and structured configurations together
- AND `anta_runner` can generate per-device catalogs without the reference repository
