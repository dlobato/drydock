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

## Build the offline bundle

After the dependency installation, use the same credential variables from the Build section.
Supply an explicit cEOS image reference through `DRYDOCK_CEOS_IMAGE`.
For offline tests, use this placeholder. No command below pulls or runs an image:

```sh
export DRYDOCK_CEOS_IMAGE=ceos:offline-placeholder
make example-bundle-test
cd artifacts/example/containerlab
sha256sum -c bundle.tar.sha256
tar -tf bundle.tar
```

`make example-bundle` renders and packages the bundle without the regression tests.
`make example-bundle-test` also tests the actual generated bundle.
Both commands run from the repository root and use the existing build playbook with `containerlab.yml` overrides.
They render separate output below `artifacts/example/containerlab/` and preserve the original build output.
AVD digital twin mode adapts the configurations for cEOS.
It removes BGP `update wait-install` and the spine `update wait-for-convergence` commands.
The bundle uses the Containerlab preview generator in AVD 6.5.0.

`bundle.tar` contains exactly these files:

- `FABRIC-topology.clab.yml` defines six `arista_ceos` nodes with the supplied image reference.
- `interface_mapping.json` maps Linux interfaces to EOS names, including `eth0` to `Management1`.
- `intended/configs/<name>.cfg` supplies one startup configuration for each switch.

All startup configuration and mapping paths are relative to the topology.
An empty Containerlab prefix preserves the six AVD device names.
Management addresses match the configurations in `192.0.2.0/24`.
The twelve links include eight leaf-to-spine links and Ethernet6 and Ethernet7 within both MLAG pairs.
Endpoint definitions remain in the EOS configurations but create no host containers or lab links.

`bundle.tar.sha256` records the SHA-256 digest, a fingerprint of the archive bytes.
The archive uses a fixed file order, timestamps, ownership, and permissions.
Identical file contents and image values produce identical archive bytes, even after file timestamps change.
Different password salts, credentials, configurations, or image values change the digest.
The checksum establishes content identity. It does not establish who supplied the bundle.

Keep the bundle private. It contains password hashes and reversible BGP authentication values.
The offline workflow uses synthetic credentials and the placeholder image, and it does not upload the bundle.
It makes sure that archived device identities, management addresses, interface mappings, and links match AVD output.
It also tests both MLAG pair definitions, reproducible packaging, digest changes, and missing inputs.

For an optional parser test, use Containerlab 0.78.2 on an isolated Linux build host.
The parser also needs access to the local Docker daemon.
From the repository root, extract the archive into a private temporary directory:

```sh
bundle_dir="$(mktemp -d)"
tar -xf artifacts/example/containerlab/bundle.tar -C "$bundle_dir"
containerlab validate -t "$bundle_dir/FABRIC-topology.clab.yml"
```

This command parses the topology without deploying a lab.
The AVD generator uses the fixed management network `custom_mgmt` and preserves original device names.
It does not support concurrent labs on one host. Lifecycle isolation remains future work.
Startup delivery and the selected image still require live evidence before task 1.1 can pass.

## Validation limits

A passing build proves that AVD can render this inventory.
It does not prove routing convergence, packet forwarding, working MLAG, runtime compatibility, or a functioning digital twin.
The four endpoint definitions do not establish host traffic coverage.
The offline bundle does not establish Containerlab startup or clabernetes compatibility.
No GKE resources, lifecycle commands, independent cleanup, or live ANTA execution exists in this PR.
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

Task 2.4 also passed from a clean source export on November 10, 2026, with the existing pinned dependencies reused.
`make example-build example-bundle-test spec-check` passed, including all four bundle tests.
`sha256sum -c bundle.tar.sha256` passed for the archive from that export.
Containerlab 0.78.2 accepted its extracted topology with six nodes and twelve links without deployment.
Comparison of all six EOS configurations found only the documented BGP wait commands removed by digital twin mode.
The bundle contained exactly the topology, interface mapping, and six configurations.
This sample used synthetic credentials and `ceos:offline-placeholder`:

```text
SHA-256: bc1898c9a6c793e9e7bd1039613e65db575b18e4ee60fb67b1a3aa6020d415fa
```

The digest identifies that sample only. A new password salt produces a different bundle digest.
