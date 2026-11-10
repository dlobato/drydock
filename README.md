# Drydock

Drydock creates temporary switch labs for automated tests before network deployment.
The CLI deploys demo infrastructure, starts the six-switch example, runs AVD-managed ANTA tests, retains reports, and deletes the lab.
You destroy the shared infrastructure after the demo.
The implementation passed offline tests. Live runtime acceptance remains open.

## Run a demo

Follow [the operator instructions](docs/demo-flow.md) for prerequisites, deployment, testing, reports, and teardown.
The main commands are:

```sh
.venv/bin/python -m drydock --environment artifacts/environment.yml infra deploy
.venv/bin/python -m drydock --environment artifacts/environment.yml test --help
.venv/bin/python -m drydock --environment artifacts/environment.yml infra destroy
```

The flow uses an existing Google Cloud project, GKE Standard, clabernetes, and temporary workers for each lab.
Switches boot with rendered startup configurations.
The operator machine stays outside GKE and reaches eAPI through internal Kubernetes tunnels.
The `arista.avd.anta_runner` role generates catalogs from the bundled AVD structured configurations and runs the tests.
No service framework, database, or direct switch connection command is required.

Labs expire after two hours by default, with a four-hour maximum.
An independent cleaner runs every five minutes and retries incomplete deletion indefinitely.
The target is complete deletion within thirty minutes after expiry while provider APIs are available.
Live timing evidence is still required.
Shared infrastructure has no automatic expiry. You own its teardown.

## Build and test offline

See [the example instructions](examples/evpn-symmetric-irb/README.md) for build dependencies, credentials, and output paths.
The example uses `pyavd[ansible]==6.5.0` and contains two spines and two MLAG leaf pairs.
It uses generic names, synthetic addresses, and runtime lab credentials.
The bundle contains the topology, interface mapping, startup configurations, and matching structured configurations.
Keep the bundle private because it contains authentication material.

After the documented example build, run:

```sh
make test
make spec-check
```

The offline GitHub workflow builds the example and runs these gates.
It generates ANTA catalogs in dry-run mode without contacting switches or cloud APIs.
GitHub Actions orchestration for live labs remains follow-up work.
Labs contain switches only. CloudVision and host containers remain excluded.

## Acceptance

The milestone requires passing routing, EVPN, VXLAN, switch-link, and MLAG tests on both pairs.
It also requires saved reports and evidence of complete cleanup across success and failure paths.
Missing, skipped, errored, or failed required results prevent acceptance.
A passing offline test or OpenSpec result does not prove working MLAG or a supported runtime.

The separate MLAG investigation remains open.
Drydock includes no experimental firewall workaround and makes no claim about its suspected cause.
See [the reference notes](docs/references.md) for the source material and prior limitations.

## Work with OpenSpec

Use OpenSpec 1.16.0 and [the active change](openspec/changes/add-digital-twin-pipeline/proposal.md).
Run `make spec-status` to see its state.
Keep proposals under `openspec/changes/` until implementation and live acceptance are complete.
Do not archive this change based on offline evidence alone.
