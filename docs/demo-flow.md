# Run an ANTA demo

Drydock supplies a CLI flow for the six-switch example.
You deploy infrastructure for a demo session and destroy it afterward.
The existing Google Cloud project survives teardown.
No service framework or database is required.

The actual November 11 GKE CLI run passed all 54 ANTA results, both MLAG pairs, and complete lab deletion.
Standalone create, authenticated status, invalid-password rejection, and repeated deletion also passed.
The tests used a corrected private clabernetes runtime and direct Pod-IP access.
See [the live validation record](live-gke-validation.md) for tested behavior, fixes, and limits.
The results apply only to the recorded private build. They do not qualify the official published clabernetes release.

## Prepare the operator machine

Use Python 3.13, Google Cloud CLI, `gke-gcloud-auth-plugin`, `kubectl`, Helm 3, Docker, and OpenSpec 1.16.0.
Run the commands from the repository root.
The operator machine stays outside GKE.
It needs HTTPS access to Google Cloud, the GKE API, and the image registries.

Switch management uses private Pod-IP HTTPS on TCP port 443.
The operator machine needs private routes to the GKE Pods and network rules that permit this access.
You can deploy infrastructure from a separate operator machine through the cloud APIs.
Run lab status and test commands from the machine with private Pod routes.

The same-VPC private GCE VM passed this path in both the separate experiment and the actual CLI test.
GitHub registration is necessary only when GitHub Actions schedules jobs on that machine.
The CLI discovers switch addresses through authenticated Kubernetes access.

The private demo disables TLS certificate verification by user agreement.
Password authentication and EOS hostname comparison remain required.
The runner sends credentials without certificate-based proof of the switch identity.
No public switch endpoint or interactive connection command is provided.

Use an existing, dedicated demo project with billing and sufficient GKE and Compute Engine quotas.
Enable the Container, Compute Engine, IAM, and Artifact Registry APIs before deployment.
Authenticate `gcloud` as an operator that can manage clusters, networks, service accounts, custom IAM roles, and project IAM bindings.
The operator also needs permission to act as the created service accounts and administer Kubernetes resources.
For a service-account runner, bind Kubernetes permissions to the identity reported by that runner.
GKE can report a numeric service-account ID instead of its email address.
This bootstrap uses project-wide permissions for its dedicated service accounts.
Do not deploy it into a shared production project.

Use an existing regional Artifact Registry repository in the demo project.
Upload your licensed cEOS image there and record its SHA-256 digest.
Drydock does not create or delete the registry, its images, project APIs, or the project.
The worker and cleaner service accounts receive Artifact Registry read access in that project.

Install the Python dependencies:

```sh
make example-deps
```

If the runner uses a read-only container, supply writable Ansible temporary directories.
The live runner used `ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote` with a writable `/tmp` mount.
It also supplied writable mounts for `.ansible`, the ownership directory, and reports.

## Prepare the cleaner image

The cleaner runs inside GKE and survives loss of the operator machine.
Its image contains this repository, Google Cloud CLI, `kubectl`, and PyYAML.
Build it from a digest-pinned Google Cloud CLI slim image with Debian package support.
Supply the full base image reference in `DRYDOCK_GCLOUD_IMAGE`.
Supply the destination image tag in `DRYDOCK_CLEANER_TAG`.
These values refer to your own images.

```sh
docker build -f Dockerfile.cleaner \
  --build-arg GCLOUD_IMAGE="$DRYDOCK_GCLOUD_IMAGE" \
  -t "$DRYDOCK_CLEANER_TAG" .
docker push "$DRYDOCK_CLEANER_TAG"
```

Record the pushed cleaner digest in the environment file.
Rebuild the cleaner when its lifecycle code changes.
The Docker build context excludes bundles, credentials, generated files, and Git metadata.

## Deploy the environment

Copy the environment template to an ignored location:

```sh
mkdir -p artifacts
cp examples/environment.yml artifacts/environment.yml
```

Edit every placeholder in `artifacts/environment.yml`.
Select an available, exact GKE version and clabernetes chart version.
Use a digest-pinned cleaner image.
These explicit values record your runtime selection. They do not establish compatibility.

Run the deployment:

```sh
.venv/bin/python -m drydock --environment artifacts/environment.yml infra deploy
```

The command creates a network, subnet, two service accounts, a custom IAM role, and one GKE Standard cluster.
The system pool contains one `e2-standard-2` worker.
The command waits up to thirty minutes for GKE and five minutes for the Helm installation.
It installs clabernetes and the independent cleaner before returning success.
It returns JSON and a nonzero exit code on failure.

Drydock writes ownership to `artifacts/environments/<name>/ownership.json` before cloud allocation.
It writes an isolated kubeconfig beside that file.
It preserves your default kubeconfig and active `gcloud` project.
Keep this directory until teardown completes.
If deployment stops partway, run `infra destroy` before deploying again.
The command refuses existing resources instead of adopting them.
A new session can reuse a successfully destroyed environment.
Drydock restores its owned, soft-deleted IAM role when necessary.

## Build the bundle

Supply fresh lab credentials in your shell.
Use the same password for the build and the test command.
The generated startup configuration creates the `labadmin` account.

```sh
read -r -s DRYDOCK_LAB_PASSWORD
export DRYDOCK_LAB_PASSWORD
export DRYDOCK_LAB_PASSWORD_HASH="$(printf '%s' "$DRYDOCK_LAB_PASSWORD" | openssl passwd -6 -stdin)"
export DRYDOCK_CEOS_IMAGE='REGION-docker.pkg.dev/PROJECT/REPOSITORY/ceos@sha256:REPLACE_WITH_DIGEST'
make example-bundle
```

Replace the image placeholder before the build.
The runtime accepts the generated six-switch bundle, including matching structured configurations, and a regional Artifact Registry image digest.
It rejects extra devices, unsupported attributes, missing configurations, unsafe archive members, and invalid lifetimes before allocation.
The archive contains lab credentials. Keep it private and ignored.

## Run the test flow

Set `DRYDOCK_REPOSITORY` to the repository identity for this run.
Supply the tested Git commit and a distinct run and attempt identity.
For a local demo, run:

```sh
.venv/bin/python -m drydock --environment artifacts/environment.yml test \
  artifacts/example/containerlab/bundle.tar \
  --repository "$DRYDOCK_REPOSITORY" --commit "$(git rev-parse HEAD)" \
  --run local-demo --attempt 1
```

The command creates a unique lab and two dedicated `e2-standard-4` workers.
It places all switch workloads on that lab pool.
It mounts startup configurations and the interface mapping through Kubernetes Secrets.
It exposes only ClusterIP services for eAPI on port 443.
Each lab uses its own namespace, workers, record, and management network name.
Overlapping synthetic management addresses remain inside the lab runtime.
Concurrent lab isolation still requires live evidence.

The command waits for current topology and switch conditions, all twelve switch links, and ready switch pods without restarts.
It discovers the current private Pod addresses and authenticates to every eAPI endpoint.
Each readiness attempt refreshes those addresses and Pod identities.
It also compares each reported hostname with the bundle identity.
Infrastructure readiness does not establish protocol convergence.

The default readiness deadline is 1,200 seconds.
The default ANTA convergence deadline is 600 seconds.
Use `--ready-timeout` and `--test-timeout` to change those deadlines.
Both deadlines must fit within the lab lifetime.
The command retries the complete ANTA catalog every ten seconds until all required results pass or time expires.
It never uses a previous ANTA command cache.

The `arista.avd.anta_runner` role generates catalogs from the bundled structured configurations.
The role enables privileged mode for generated ping tests.
Drydock does not build its own catalogs.
The offline example produces 54 required results with the pinned versions.
The generated catalogs cover:

- Generated BGP peer sessions for the routed fabric and EVPN overlay.
- All eight leaf-to-spine links and all four MLAG peer links.
- MLAG status and configuration consistency on all four leaves.
- VXLAN interface status and configuration consistency on all four leaves.
- Generated underlay reachability and route presence across the fabric.

Missing, duplicate, skipped, errored, or failed required results prevent acceptance.
The catalogs establish switch state, protocol state, and generated switch-to-switch reachability.
They do not prove tenant application traffic between hosts.
Labs contain no host containers or CloudVision.

The command attempts deletion after success, failure, timeout, SIGINT, or SIGTERM.
It waits up to thirty minutes for immediate cleanup.
An exit code of zero requires passing ANTA results, saved reports, and completed lab deletion.
Test and cleanup outcomes remain separate in the final JSON result.
If the machine disappears or receives SIGKILL, the independent cleaner retains responsibility.

## Read the reports

The command writes a private directory at `reports/<lab-id>/`.
It retains the submitted bundle digest, repository, commit, run, attempt, requested versions, and observed EOS versions.
The environment ownership file records the observed GKE version at deployment.

The report files are:

- `run.json`: provenance, runtime, separate test and cleanup outcomes, and overall status.
- `anta.json` and `anta.xml`: ANTA JSON and JUnit results, including missing required results in JUnit.
- `expected.json` and `inventory.json`: expected result counts, original switch names, private Pod addresses, and Pod identities.
- `anta/avd_catalogs/` and `anta/reports/`: AVD-generated catalogs and JSON, CSV, and Markdown reports.
- `diagnostics.json` and `network.json`: available resource status and read-only protocol diagnostics.
- `events.json`: final test and cleanup events.

Pod addresses can change when Kubernetes replaces a Pod and disappear when the lab is deleted.
Treat the inventory as a record of that run.
Drydock keeps bundled structured configurations in a private temporary directory outside the reports.
It retains no startup files, Kubernetes Secrets, arbitrary container logs, or authentication material in the reports.
Failure diagnostics remain best effort.
A report write failure still triggers deletion and prevents overall success.
This CLI does not upload reports or enforce their local retention period.
GitHub Actions execution and artifact upload are follow-up work.

## Inspect or delete a lab

Standalone lab creation returns its identity and expiry.
It does not wait for protocol convergence.
Use the same bundle and provenance arguments as `test`:

```sh
.venv/bin/python -m drydock --environment artifacts/environment.yml lab create \
  artifacts/example/containerlab/bundle.tar \
  --repository "$DRYDOCK_REPOSITORY" --commit "$(git rev-parse HEAD)" \
  --run local-demo --attempt 2
```

Set `DRYDOCK_LAB_ID` to the returned lab identity.
Keep `DRYDOCK_LAB_PASSWORD` set for authenticated status:

```sh
.venv/bin/python -m drydock --environment artifacts/environment.yml lab status "$DRYDOCK_LAB_ID"
.venv/bin/python -m drydock --environment artifacts/environment.yml lab delete "$DRYDOCK_LAB_ID"
```

Status returns current readiness, private Pod addresses, and Pod identities.
It authenticates directly to each discovered eAPI endpoint.
Deletion preserves other labs, the system pool, and shared infrastructure.
Repeated deletion is safe.
Ownership mismatches cause refusal and require operator investigation.

## Expiry and cleanup failures

The default lab lifetime is two hours from request acceptance.
Use `--lifetime` to supply a duration from one through 240 minutes.
Four hours is the maximum.
A delayed allocation does not extend that expiry.

Kubernetes ConfigMaps retain ownership before the first allocation.
Updates use resource versions so a stale update cannot overwrite newer cleanup state.
The independent cleaner runs every five minutes on the system pool through Workload Identity.
It removes expired namespaces and worker pools and retries incomplete deletion every five minutes indefinitely.
It revisits deleted records to catch late asynchronous allocations.
It also refreshes registry tokens for running labs every five minutes because Google access tokens expire before the maximum lab lifetime.

The deletion target is thirty minutes after expiry while cloud and Kubernetes APIs are available.
A runner-loss test observed complete deletion 6 minutes 16 seconds after expiry.
That single observation does not establish timing during outages or concurrent switch isolation.
Records retain cleanup errors and an `overdue` flag after that boundary.
The cleaner exits nonzero if any deletion or token refresh fails.
The cleaner does not forcibly remove finalizers or delete resources with different ownership.
Provider failures and API outages can exceed the target.

To inspect the records and recent cleaner jobs, run:

```sh
kubectl --kubeconfig artifacts/environments/drydock-demo/kubeconfig \
  -n drydock-demo-system get configmaps,jobs
```

Replace `drydock-demo` if you selected another environment name.
Preserve the system pool and cleaner until lab cleanup completes.
Do not remove records to hide incomplete deletion.

## Destroy the demo infrastructure

After the demo, run:

```sh
.venv/bin/python -m drydock --environment artifacts/environment.yml infra destroy
```

The command deletes the owned cluster, then networking, service accounts, custom role, and the IAM bindings that deployment added.
It waits up to thirty minutes for cluster deletion.
It retains identity and network prerequisites if cluster deletion fails.
It reports incomplete teardown and permits another destruction attempt.
It never deletes the project.

The final inventory covers clusters, networks, subnets, accounts, custom roles, instances, disks, firewall rules, routes, addresses, forwarding rules, instance groups, templates, pending GKE operations, and IAM bindings.
It associates dependent resources through network references and the GKE name prefix.
It reports remaining resources instead of deleting unknown leftovers.
Drydock saves the inventory counts and errors in `artifacts/environments/<name>/cleanup.json`.
A failed inventory query cannot produce a successful teardown result.

Infrastructure has no automatic expiry.
You own session teardown even when no labs remain.
The existing project, registry, uploaded images, and enabled APIs remain operator-managed prerequisites.

## Offline development evidence

Run the local gates:

```sh
make test
make example-bundle-test
make spec-check
```

Supply the documented example credentials and an explicit image value before the bundle test.
The existing offline GitHub workflow runs these gates.
It does not deploy infrastructure or run a live lab.
Keep the remaining lifecycle and GitHub tasks open until their evidence exists.

The implementation passes 38 offline CLI tests on Linux with Python 3.13.
The actual AVD role generated 54 dry-run results from the six-switch build.
The example build, strict OpenSpec validation, and dependency consistency gate also passed.
These offline results do not establish runtime support.
