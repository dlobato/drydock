# Run an ANTA demo

The optional demo supplies GKE setup and six-switch ANTA orchestration outside the lifecycle core.
The setup command needs cloud administration access. The lifecycle and test commands use supplied Kubernetes access.
The demo installs shared infrastructure that the operator must destroy after the session.
The existing Google Cloud project and registry survive teardown.

The November 11 CLI run passed 54 ANTA results, both MLAG pairs, and complete lab deletion on a corrected private runtime.
See [the historical validation record](live-gke-validation.md) for the exact runtime and evidence.
Those results do not qualify this refactor or the published clabernetes release.

## Prepare the operator machine

Use Python 3.13, Google Cloud CLI, `gke-gcloud-auth-plugin`, `kubectl`, Helm 3, Docker, and OpenSpec 1.16.0.
Run commands from the repository root.
The setup machine needs access to Google Cloud, the GKE API, and image registries.
The runner also needs private routes to switch Pod addresses on TCP port 443.

The private demo skips switch TLS certificate verification by agreement.
Password authentication and hostname comparison remain required.
The runner sends credentials without certificate-based proof of switch identity.
Kubernetes certificate verification remains enabled.

Use an existing dedicated demo project with billing and sufficient GKE and Compute Engine quotas.
Enable the Container, Compute Engine, IAM, and Artifact Registry APIs.
Authenticate the setup operator with permission to manage the demo cluster, network, service account, and required IAM bindings.
The operator also needs permission to act as the worker service account and administer Kubernetes resources.
The lifecycle runner does not need these administration permissions.

Upload your licensed cEOS image to an existing regional Artifact Registry repository in that project.
Record its SHA-256 digest.
The demo gives the worker service account access to that project's registry.
Switch workloads use operator-supplied image access without lifecycle registry token commands.

Install the example dependencies:

```sh
make example-deps
```

The demo uses the standard `arista.avd.anta_runner` playbook with AVD 6.5.0 and ANTA 1.10.0.
The lifecycle-only dependency remains separate in `requirements.txt`.
If the runner uses a read-only container, supply writable Ansible temporary directories, private input storage, and report storage.

## Prepare the cleaner image

The cleaner runs inside Kubernetes independently of the runner.
The current demo image uses a Google Cloud CLI slim base for its existing package repositories.
The cleaner itself requires only Python, `kubectl`, and the lifecycle dependency.
It does not use Google Cloud CLI or cloud credentials.

Set `DRYDOCK_GCLOUD_IMAGE` to a digest-pinned Google Cloud CLI slim image with Debian package support.
Set `DRYDOCK_CLEANER_TAG` to the destination image tag.
Build and publish the cleaner:

```sh
docker build -f Dockerfile.cleaner \
  --build-arg GCLOUD_IMAGE="$DRYDOCK_GCLOUD_IMAGE" \
  -t "$DRYDOCK_CLEANER_TAG" .
docker push "$DRYDOCK_CLEANER_TAG"
```

Record the published digest in the environment file.
Rebuild the image when lifecycle code changes.
The build context excludes bundles, credentials, generated files, and Git metadata.
The image contains only the `drydock` package and its dependency.

## Deploy the environment

Copy the GKE environment template:

```sh
mkdir -p artifacts
cp examples/environment.yml artifacts/environment.yml
```

Replace every placeholder in `artifacts/environment.yml`.
Select exact GKE and clabernetes versions and a digest-pinned cleaner image.
These values record a selection without establishing compatibility.
Deploy the optional infrastructure:

```sh
.venv/bin/python -m examples.demo --environment artifacts/environment.yml infra deploy
```

The command creates a network, subnet, worker service account, and GKE Standard cluster.
The system pool contains one `e2-standard-2` worker.
The command waits up to 30 minutes for GKE and five minutes for Helm.
It installs clabernetes and the independent cleaner.
The cleaner uses Kubernetes permissions without Google IAM grants.
The demo permission manifests do not establish the restricted pipeline policy planned in task 8.2.

The setup writes ownership before cloud allocation under `artifacts/environments/<name>/`.
It writes an isolated kubeconfig and `lifecycle.yml` in that directory.
It preserves the global kubeconfig and active Google Cloud project.
Keep the directory until teardown completes.
If deployment stops partway, use the demo `infra destroy` command before another deployment.

The operator must supply switch worker capacity separately.
For the template's `drydock-demo` name and `europe-west1-b` zone, use this example capacity command.
First, set `DRYDOCK_PROJECT` to the project from `artifacts/environment.yml`.

```sh
gcloud container node-pools create demo-switches \
  --project="$DRYDOCK_PROJECT" --cluster=drydock-demo --zone=europe-west1-b \
  --num-nodes=2 --machine-type=e2-standard-4 --disk-type=pd-standard --disk-size=30 \
  --image-type=UBUNTU_CONTAINERD --scopes=cloud-platform \
  --service-account="drydock-demo-node@$DRYDOCK_PROJECT.iam.gserviceaccount.com"
```

Adapt the explicit cluster and zone arguments if the environment differs.
The operator owns scheduling policy and capacity measurements.
This example does not qualify startup duration or concurrent capacity.
Lab deletion leaves these shared workers for the operator or cluster autoscaler.
Infrastructure teardown deletes the owned cluster and its worker pools.

## Build and run the example

Follow [the example instructions](../examples/evpn-symmetric-irb/README.md) to supply lab credentials.
Set `DRYDOCK_CEOS_IMAGE` to the licensed cEOS image digest in the regional registry.
Build the startup bundle:

```sh
make example-bundle-test
```

The archive contains topology, interface mapping, and startup configurations.
Matching AVD models stay outside the archive under `artifacts/example/containerlab/intended/structured_configs/`.
Keep both outputs private because they contain authentication material.

Set `DRYDOCK_REPOSITORY` to the repository identity.
Keep `DRYDOCK_LAB_PASSWORD` set to the startup configuration's `labadmin` password.
Run the example with the generated lifecycle environment file:

```sh
.venv/bin/python -m examples.demo \
  --environment artifacts/environments/drydock-demo/lifecycle.yml test \
  artifacts/example/containerlab/bundle.tar \
  --structured-configs artifacts/example/containerlab/intended/structured_configs \
  --repository "$DRYDOCK_REPOSITORY" --commit "$(git rev-parse HEAD)" \
  --run local-demo --attempt 1 --output reports
```

The example first compares each AVD model with its startup file and generates required catalogs.
Missing or inconsistent models fail before allocation.
It then creates a lab through the lifecycle API and waits for authenticated readiness.
It runs the standard ANTA playbook and requires routing, EVPN, VXLAN, switch-link, and both MLAG-pair coverage.
Missing, skipped, errored, duplicate, or failed required results prevent network acceptance.

The default readiness deadline is 1,200 seconds and the ANTA deadline is 600 seconds.
The readiness budget starts at lab acceptance and includes allocation and capacity waiting.
The recorded startup deadline cannot exceed lab expiry.
The example requires both deadlines to fit inside the selected lab lifetime.
The lifecycle implementation still defaults to 120 minutes with a 240-minute maximum pending task 7.3.

The command retains reports below `reports/<lab-id>/` and always requests deletion after allocation.
Its JSON result separates test and cleanup outcomes.
Overall success requires passing required tests, retained reports, and complete lab deletion.
Cancellation uses the same cleanup path. The independent cleaner covers runner loss.

## Inspect output and cleanup

The example retains safe JSON and JUnit reports, generated catalogs, endpoint identities, lifecycle outcomes, and available diagnostics.
The recorded runtime includes AVD, ANTA, observed EOS versions, and the submitted cEOS image digest.
The input digest and workflow identity remain in lifecycle provenance.
Do not upload bundles, structured configurations, Kubernetes credentials, Secret contents, or arbitrary container logs.
Artifact retention and GitHub integration remain later tasks.

Use [the lifecycle instructions](lifecycle.md) for standalone creation, status, repeated deletion, and expiry.
For demo-created clusters, pass `artifacts/environments/<name>/lifecycle.yml` to those commands.
The independent cleaner runs every five minutes and retries incomplete deletion indefinitely.
It revisits deleted records for late namespaces and records overdue cleanup.
It does not refresh registry tokens or delete workers.

The deletion target remains 30 minutes after expiry while Kubernetes and backend APIs are available.
Historical timing does not qualify the revised cleaner path.
Preserve the system pool, cleaner, and ownership records until lab cleanup completes.

## Destroy the infrastructure

After all lab cleanup completes, destroy the optional demo infrastructure:

```sh
.venv/bin/python -m examples.demo --environment artifacts/environment.yml infra destroy
```

The command deletes the owned cluster before networking, service accounts, and its IAM bindings.
It retains prerequisites if cluster deletion fails and permits another deletion attempt.
It also retains inventory handling for resources owned by earlier demo deployments.
It never deletes the project or registry.

The final inventory covers the cluster, network dependencies, identities, pending GKE operations, and IAM bindings.
It reports remaining resources in `artifacts/environments/<name>/cleanup.json`.
An inventory failure prevents successful teardown.
Shared infrastructure has no automatic expiry. The operator owns its teardown and cloud cost.

## Offline evidence

After the example build, run `make test` and `make spec-check`.
Run `make lifecycle-test` with only lifecycle dependencies to exercise the independent CLI boundary.
These tests use controlled Kubernetes and eAPI responses and actual offline AVD catalog generation.
They do not qualify this refactor on a live cluster.
Keep the remaining topology, capacity, cleanup, workflow, and scale tasks open.
