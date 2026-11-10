# Offline AVD example

This example builds configurations for `spine1`, `spine2`, and `leaf1` through `leaf4` with AVD 6.5.0.
It does not create a lab or contact a switch.
MLAG lets two switches act as one logical pair.
The leaf pairs are `leaf1` with `leaf2` and `leaf3` with `leaf4`.

## Prerequisites

Use Linux with Python 3.13, its `venv` module, pip, GNU Make, and OpenSSL.
Use Node.js 22 and OpenSpec 1.16.0 for specification validation.
Install OpenSpec with `npm install --global @fission-ai/openspec@1.16.0`.
Dependency installation needs access to PyPI and Ansible Galaxy.
After installation, the build needs no network access, cloud account, device image, reference repository, or live credentials.

Run all commands from the Drydock repository root.
Install the pinned `pyavd[ansible]==6.5.0` dependency and matching `arista.avd` collection:

```sh
make example-deps
```

The target creates `.venv/` and `.collections/` inside the checkout.
AVD declares the remaining Python and collection dependencies.
The Makefile selects the local collection directory and Ansible temporary directory.

## Build

Supply credentials through environment variables at build time.
`DRYDOCK_LAB_PASSWORD` supplies BGP authentication.
`DRYDOCK_LAB_PASSWORD_HASH` supplies the SHA-512 password hash for the synthetic `labadmin` account.
These synthetic values are sufficient for offline rendering:

```sh
export DRYDOCK_LAB_PASSWORD=offline-example-only
export DRYDOCK_LAB_PASSWORD_HASH="$(printf '%s' "$DRYDOCK_LAB_PASSWORD" | openssl passwd -6 -stdin)"
make example-build
make spec-check
git diff --check
```

The playbook rejects missing credentials before AVD runs.
Use these public synthetic values only for offline rendering.
Do not deploy them to a reachable device.
Generated files contain password hashes and reversible BGP authentication values.
Keep them private if you replace the synthetic values with real lab credentials.

## Output

The build writes ignored files below `artifacts/example/`:

- `intended/configs/` contains exactly six EOS `.cfg` files.
- `intended/structured_configs/` contains six structured YAML configurations.
- `documentation/` contains fabric and device documentation, plus topology and link CSV files.

AVD performs its normal input validation during the build.
Endpoint definitions describe four attached devices for AVD. They do not create host containers.
CloudVision is permanently excluded from labs.

The GitHub Actions workflow runs strict OpenSpec validation and the same build with synthetic credentials.
It uses a hosted Linux runner and read-only repository permissions.
It does not upload generated configurations or request a lab.

## Reference behavior

The example derives from the read-only PS `EVPN-symmetric-IRB` reference in [the reference notes](../../docs/references.md).
All device names, tenant names, addresses, and example identifiers use generic or synthetic values.
The inventory uses explicit node identifiers so allocation does not depend on generated reference files.
Source comments, credentials, and management integrations are omitted.

Each leaf connects to both spines on Ethernet1 and Ethernet2.
Each pair uses Ethernet6 and Ethernet7 for its MLAG peer link.

BGP exchanges routing information between switches.
The example preserves eBGP routing and EVPN signaling with route-target membership.
VXLAN carries tenant networks across the routed fabric.
A VRF is a separate routing table.
Symmetric IRB routes tenant traffic through a VRF on each leaf.
The example retains two routed tenant VRFs with four virtual gateways, diagnostic loopbacks, and a native VLAN without VXLAN.

LACP combines physical links into one logical link.
The example retains BGP authentication, peer filtering, multipath routing, MLAG routing peers, dual-primary detection, and endpoint trunks with LACP.
The physical platform profile remains `7050X3` for configuration generation. This does not select a supported runtime image.

## Validation limits

A passing build proves that AVD can render this inventory.
It does not prove routing convergence, packet forwarding, working MLAG, runtime compatibility, or a functioning digital twin.
The four endpoint definitions do not establish host traffic coverage.
No Containerlab integration, GKE resources, lifecycle commands, independent cleanup, or live ANTA execution exists in this PR.
The separate MLAG investigation remains unresolved and does not block offline generation.
No experimental firewall workaround is included.

The broader OpenSpec milestone remains active.
Its acceptance still requires runtime evidence for both MLAG pairs and resource cleanup across failure paths.

## Recorded offline evidence

On November 10, 2026, the documented dependency installation and build passed from a clean export on Linux with Python 3.13.9.
The build used `pyavd==6.5.0`, `arista.avd==6.5.0`, and `ansible-core==2.21.6`.
Strict OpenSpec validation passed with the npm package `@fission-ai/openspec@1.16.0`.
Both missing-credential cases failed before rendering.

Manual inspection found exactly six switch configurations and eight leaf-to-spine links.
It found MLAG domains `PAIR1` and `PAIR2`, peer links on Ethernet6 and Ethernet7, and shared VXLAN addresses within each pair.
It also found BGP routing, EVPN and route-target membership, VXLAN mappings, both tenant VRFs, and all four virtual gateways.
Inspection found no reference identities or inspected source authentication values in the output.
This evidence does not establish runtime MLAG or network acceptance.
