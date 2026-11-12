# Manage a lab

The lifecycle CLI uses a supplied Kubernetes context on an existing clabernetes cluster.
It does not require AVD, ANTA, Google Cloud CLI, or cloud administration permissions.
Kubernetes authentication can use an operator-configured provider plugin without cloud administration access.
Run commands from the repository root.

## Prepare the cluster

The cluster operator installs clabernetes and supplies worker capacity, private routing, and access to the digest-pinned cEOS image.
Image access must work for switch workloads in newly created lab namespaces.
The CLI does not create image pull credentials or select worker pools.
The operator supplies scheduling policy through the cluster and clabernetes configuration.

Private image access must cover both kubelet pulls and clabernetes controller metadata reads.
A pull Secret stores registry credentials in Kubernetes.
The tested private runtime uses global `imagePull.pullSecrets` references to operator-supplied Secrets in each lab namespace.
The operator supplies and refreshes those credentials outside the lifecycle CLI.
Worker identity alone does not supply credentials for the tested controller's metadata reads.

The operator creates the `<name>-system` namespace for ownership records and installs an independent cleaner.
The optional GKE demo setup supplies these resources through separate operator tooling.
The cleaner uses a mounted Kubernetes service-account token and CA certificate.
It runs `python -m drydock --environment /environment/environment.yml reap` every five minutes.
Its environment file selects the mounted kubeconfig and its explicit `cleaner` context.
The cleaner does not require cloud credentials.

The caller needs permission to manage ownership ConfigMaps, owned lab namespaces, startup Secrets, and clabernetes topologies.
Readiness also needs access to clabernetes nodes, links, Pods, and Services.
The current CLI lists namespaces to inspect ownership.
The operator must enforce the authorized lab boundary through Kubernetes permissions and admission policy.
The pipeline permission policy remains task 8.2.

The runner needs private routes to the Kubernetes API and switch Pod addresses on TCP port 443.
The private demo skips switch TLS certificate verification by agreement.
Password authentication and EOS hostname comparison remain required.
This exception does not apply to Kubernetes TLS verification.

## Install and select access

Use Python 3.13 and `kubectl` on the runner.
Install the lifecycle dependency:

```sh
make lifecycle-deps
mkdir -p artifacts
cp examples/lifecycle.yml artifacts/lifecycle.yml
```

Edit `artifacts/lifecycle.yml`:

```yaml
name: drydock-demo
kubeconfig: /absolute/path/to/kubeconfig
context: your-lab-context
```

The environment name determines the ownership namespace and lab namespace prefix.
Every Kubernetes command passes the kubeconfig and context explicitly.
The CLI does not change the global Kubernetes context or cloud account.
Relative kubeconfig paths resolve from the command's working directory.

## Supply the lab input

Supply an uncompressed tar archive with these files:

- `FABRIC-topology.clab.yml` contains the supported six-switch topology.
- `interface_mapping.json` supplies the supported interface mapping.
- `intended/configs/<name>.cfg` supplies each switch's complete startup configuration.

AVD structured configurations do not belong in the archive.
The archive digest identifies all submitted files together.
Keep the archive private because startup configurations contain authentication material.

The current input limits remain 10 MiB per archive and 1 MiB per member.
Startup and mapping data together must fit within 512 KiB.
Admission rejects duplicate members, unsafe paths, unsupported attributes, and missing files before allocation.
The six device names, addresses, links, and mapping still follow the example.
The cEOS image still requires a digest in regional Google Artifact Registry.
Tasks 6.2 and 6.4 remove these remaining example and registry restrictions.

## Create and inspect

Set `DRYDOCK_REPOSITORY` to the repository identity for the request.
Create a lab from the startup-only bundle:

```sh
.venv/bin/python -m drydock --environment artifacts/lifecycle.yml lab create \
  artifacts/example/containerlab/bundle.tar \
  --repository "$DRYDOCK_REPOSITORY" --commit "$(git rev-parse HEAD)" \
  --run local-demo --attempt 1
```

The command records ownership before workload allocation.
It creates a separate lab namespace, startup Secret, and clabernetes topology.
It does not allocate cloud workers or wait for authenticated readiness.
A creation failure requests cleanup and returns a nonzero exit code with the lab identity and cleanup outcome.
Creation and deletion retain their Kubernetes records without startup credentials.

Set `DRYDOCK_LAB_ID` to the returned `id`.
Supply the startup configuration's `labadmin` password through `DRYDOCK_LAB_PASSWORD`.
Request authenticated status:

```sh
.venv/bin/python -m drydock --environment artifacts/lifecycle.yml lab status "$DRYDOCK_LAB_ID"
```

Status returns one JSON result and a nonzero exit code when the lab is not ready.
It requires current topology and node plans, accepted links, ready Pods, and private eAPI Services.
It discovers current Pod addresses and authenticates to every switch with hostname comparison.
Its connection inventory preserves switch names, Pod names, and Pod UIDs.
Network tests and convergence remain the caller's responsibility.

## Delete and expire

Request deletion after every allocation attempt:

```sh
.venv/bin/python -m drydock --environment artifacts/lifecycle.yml lab delete "$DRYDOCK_LAB_ID"
```

Repeated deletion is safe.
The command refuses a namespace with different ownership and reports incomplete deletion as failure.
It waits up to 30 minutes for immediate cleanup.
It deletes the lab namespace and its resources without deleting cluster workers or shared infrastructure.
Worker retention and cloud cost remain the operator's responsibility.

Before replacing an earlier demo deployment, delete its labs with the earlier tool.
Keep the earlier cleaner active until cleanup completes.
The revised lifecycle does not remove worker pools from earlier deployments.
Deploy the rebuilt cleaner only after those labs are removed.

The current lifetime defaults to 120 minutes and accepts one through 240 minutes through `--lifetime`.
Task 7.3 changes these limits to the planned 30-minute default and 60-minute maximum.
The cleaner retries expired or deleting labs every five minutes indefinitely and revisits deleted records for late resources.
It records overdue cleanup after 30 minutes beyond expiry.
Task 7.4 retains the remaining cleanup qualification, including interruption and late-resource tests.
Keep the cleaner and ownership records available until cleanup completes.

## Offline evidence

Run `make lifecycle-test` with only `requirements.txt` installed.
The tests exercise the CLI with controlled Kubernetes and eAPI responses.
They cover creation, authenticated status, repeated deletion, failed allocation cleanup, and expiry without AVD or ANTA.
They do not establish live startup, provider compatibility, concurrent isolation, cleanup timing, or network acceptance.
