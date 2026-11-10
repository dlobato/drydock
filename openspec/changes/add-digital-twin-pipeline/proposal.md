# Proposal

## Why

Network changes need a temporary digital twin before deployment.
Drydock needs one small flow that connects lab creation, automated network tests, retained reports, and complete cleanup.

## What Changes

The agreed delivery starts with a CLI demo:

- Build the anonymized AVD fabric with two spines and two MLAG leaf pairs.
- Deploy GKE Standard and clabernetes on demand in an existing dedicated demo project through scripted `gcloud` commands.
- Start switches with rendered configurations and allocate dedicated temporary workers per lab.
- Use `arista.avd.anta_runner` to generate catalogs from AVD structured configurations and execute ANTA through internal management tunnels.
- Retain JSON, JUnit, generated catalogs, diagnostics, and provenance, then delete the lab after every allocation attempt.
- Expire abandoned labs independently through a five-minute cluster-side cleaner.
- Destroy shared infrastructure manually after the demo and preserve the existing project.

The CLI returns JSON. Kubernetes stores ownership and expiry records.
No HTTP service or database is selected.
Lab expiry defaults to two hours and cannot exceed four hours from acceptance.
Failed deletion retries every five minutes indefinitely.
The deletion target is thirty minutes after expiry while APIs are available.
Overdue cleanup remains visible.

GitHub Actions orchestration follows the CLI delivery.
The runner stays outside GKE.
Runtime support and deletion timing still require live evidence.
The separate MLAG investigation remains open. No experimental firewall workaround is accepted.
CloudVision, host containers, interactive switch access, fork contributions, production deployment, and large-scale qualification remain out of scope.

## Capabilities

### New Capabilities

- `example-fabric`: An anonymized six-switch AVD example with portable startup and structured configurations.
- `switch-lab-lifecycle`: Temporary switch labs with private ANTA transport, authenticated readiness, independent expiry, and ownership-based cleanup.
- `digital-twin-pipeline`: CLI orchestration with AVD-managed ANTA acceptance, reports, cleanup outcomes, and later GitHub Actions integration.

### Modified Capabilities

None. The change remains active and unarchived.

## Impact

Implementation adds lifecycle commands, infrastructure scripts, an AVD role playbook, offline failure-path tests, a cleaner image recipe, and operator instructions.
The dependency baseline is AVD 6.5.0 and ANTA 1.10.0.
Runtime versions and image digests are explicit operator inputs. They are not claims of compatibility.

The sources remain the Vantage digital twin pipeline and PS EVPN-symmetric-IRB fabric.
See [the reference notes](../../../docs/references.md) for provenance and observed limitations.
Reference repositories remain unchanged.
