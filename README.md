# Drydock

Drydock creates temporary switch labs on an existing Kubernetes cluster with clabernetes.
Its lifecycle CLI creates labs, waits for authenticated readiness, reports private connections, and deletes lab resources.
The cluster operator supplies capacity, image access, permissions, and private routing.
The pipeline supplies configurations, network tests, and reports.

## Use the lifecycle CLI

Use Python 3.13 and `kubectl` on a machine with private access to the cluster and switch Pods.
Install the lifecycle dependency:

```sh
make lifecycle-deps
```

Copy `examples/lifecycle.yml` to an ignored path.
Set its environment name, kubeconfig path, and Kubernetes context.
Follow [the lifecycle instructions](docs/lifecycle.md) for cluster prerequisites, input files, and commands.

```sh
.venv/bin/python -m drydock --environment artifacts/lifecycle.yml lab create --help
.venv/bin/python -m drydock --environment artifacts/lifecycle.yml lab wait "$DRYDOCK_LAB_ID"
.venv/bin/python -m drydock --environment artifacts/lifecycle.yml lab status "$DRYDOCK_LAB_ID"
.venv/bin/python -m drydock --environment artifacts/lifecycle.yml lab inventory "$DRYDOCK_LAB_ID"
.venv/bin/python -m drydock --environment artifacts/lifecycle.yml lab delete "$DRYDOCK_LAB_ID"
```

Lifecycle operations use Kubernetes without cloud administration commands, AVD, or ANTA.
They do not create workers or run network tests.
The CLI requires topology and startup files without AVD structured configurations.
Readiness does not establish routing convergence or network acceptance.

## Run the optional demo

[The demo instructions](docs/demo-flow.md) describe separate GKE setup and six-switch ANTA orchestration.
These commands live under `examples.demo`:

```sh
.venv/bin/python -m examples.demo --environment artifacts/environment.yml infra deploy
.venv/bin/python -m examples.demo --environment artifacts/lifecycle.yml test --help
.venv/bin/python -m examples.demo --environment artifacts/environment.yml infra destroy
```

Use `make example-deps` to install the separate AVD and ANTA dependencies.
[The example instructions](examples/evpn-symmetric-irb/README.md) describe the anonymized fabric and offline build.
The example contains two spines and two MLAG leaf pairs.
Labs contain switches only. CloudVision and host containers remain excluded.

## Implementation limits

Task 6.1 separates the lifecycle core from cloud setup and network acceptance.
Task 6.2 preserves the admitted topology and delegates network semantics to clabernetes.
The lifecycle core reads switch identities, the link count, and safe file references without interpreting EOS startup or interface mapping contents.
Admission accepts supported cEOS topology shapes within the documented input limits and distributes startup data across bounded Kubernetes Secrets.
Task 6.3 protects creation ownership, competing state updates, and namespace deletion with controlled race tests.
Repeated creation requests receive separate lab identities. Live concurrent network isolation remains unqualified.
The cEOS image accepts any registry and must use a SHA-256 digest.
The operator supplies image access through the cluster. The lifecycle CLI does not obtain registry tokens.
Offline CLI tests cover other registries. A private, authenticated non-Google registry passed the six-switch [live acceptance](docs/live-gke-validation.md#november-12-registry-independent-images).
Labs still default to 120 minutes with a 240-minute maximum.
Task 7.1 adds capacity waiting and a startup deadline that starts at acceptance and cannot exceed expiry.
Creation accepts `--startup-timeout` in seconds, with a default of 1200 seconds.
`lab wait` requests cleanup after timeout or cancellation and reports scheduling capacity separately from switch startup and management failure.
Task 7.2 adds authenticated `lab inventory` output under every submitted switch name.
Readiness re-reads Kubernetes state after authentication and rejects endpoints that change during that observation.
The [runtime inventory instructions](docs/lifecycle.md#use-runtime-connections) describe private routing, returned fields, and use with an existing Ansible inventory.
The planned 30-minute default, 60-minute maximum, and live scale qualification remain open.

The November 11 demo passed 54 live ANTA results and both MLAG pairs on the recorded private runtime.
[That historical evidence](docs/live-gke-validation.md) does not qualify this refactor, the published clabernetes release, scale, or concurrent isolation.
The private demo retains its switch TLS certificate exception with password authentication and hostname comparison.
Kubernetes certificate verification remains enabled.

## Develop

Install the Git hooks in the lifecycle virtual environment:

```sh
.venv/bin/python -m pip install pre-commit
.venv/bin/pre-commit install
.venv/bin/pre-commit run --all-files
```

Ruff fixes lint issues, sorts imports, and formats Python source and tests.
Mypy checks function bodies in the lifecycle code, demo code, and bundle builder.
The hooks install pinned tools in isolated environments without AVD or ANTA.

With lifecycle dependencies installed, run `make lifecycle-test`.
After the documented example build, run `make test` and `make spec-check`.
The lifecycle tests use controlled Kubernetes and eAPI responses without cloud resources or switches.
The example tests also exercise actual AVD catalog generation offline.

Use OpenSpec 1.16.0 and [the active change](openspec/changes/add-digital-twin-pipeline/proposal.md).
Keep the change active until implementation and live acceptance are complete.
