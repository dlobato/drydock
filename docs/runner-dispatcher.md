# Disposable GKE runner

The operator runs this dispatcher outside GitHub jobs.
It supplies one disposable GCE VM for one approved access probe.
A scale set groups runners and exposes routed jobs.
GitHub labels route jobs. They do not authorize private execution.

The dispatcher uses the official `github.com/actions/scaleset` SDK at `v0.5.0`.
This SDK is in public preview. Its Go module pins the required toolchain and dependencies.
The dispatcher accepts only the protected `main` workflow in `dlobato/drydock` after native `gke` approval.
It compares the exact run attempt, repository identities, workflow reference, queued job, and reviewed `main` revision.
Missing evidence or an unavailable GitHub API prevents runner registration and VM creation.

GitHub can route `JobAssigned` messages to an empty scale set without a runner.
The dispatcher accepts that routing message only after authorization.
For `JobAvailable`, it also acquires the exact request through the SDK.
It refuses multiple reservations, existing runners, and an existing scale set.
There is no warm capacity or concurrent execution.

A root-owned start guard compares the actual job with the approved attempt and workflow SHA.
An unexpected job causes the guard to kill the whole runner process group before workflow steps.
This also blocks steps with `always()` and covers cancellation or reassignment while the VM starts.
The official runner supplies the hook identity from GitHub's job context.
The guard does not use workflow-provided environment variables as authorization.

## Prepare the operator host

Use a reviewed checkout of this branch on a trusted Linux operator host.
Install Go, Python 3, OpenSSH, Google Cloud CLI, and GitHub CLI.
Run commands from the repository root.
Use the operator's isolated Google profile and GitHub runner-management credential.
Keep those credentials outside GitHub and the runner VM.

Before dispatch, supply these existing resources:

- A subnet with private routes to the target GKE control plane.
- Internet egress for pinned downloads, GitHub, and Google identity exchange.
- An IAP firewall rule for TCP port 22, limited to the `drydock-dispatcher` target tag.
- Operator permission to create and delete instances, change their metadata, and use IAP SSH.
- The protected environment and disabled federation described in [the access procedure](github-gke-access.md).

The VM receives no cloud service account, cloud scopes, administrative kubeconfig, or operator GitHub token.
The operator passes its one-use registration through SSH standard input.
The pinned startup script installs the runner and kubectl with SHA256 comparisons.
The runner uses an unprivileged account without sudo access.

Build and test the operator program:

```sh
make dispatcher-test
mkdir -p artifacts/runner-dispatcher
(cd examples/github/runner-dispatcher && go build -o ../../../artifacts/runner-dispatcher/drydock-dispatcher .)
```

## Dispatch one approved attempt

Request an access probe through the trusted workflow on `main`.
Approve its deployment through the native `gke` environment review.
Record its run ID, attempt, and reviewed protected `main` SHA.
The PR input SHA remains separate from the trusted workflow SHA.

Create `artifacts/runner-dispatcher/operator.json` with those values and the operator's existing network:

```json
{
  "run_id": 123,
  "run_attempt": 1,
  "workflow_sha": "<40-character-reviewed-main-SHA>",
  "project": "drydock-513410",
  "zone": "europe-west1-b",
  "subnetwork": "drydock-access",
  "image": "projects/ubuntu-os-cloud/global/images/ubuntu-2404-noble-amd64-v20261105"
}
```

Select the isolated operator profile and credential:

```sh
export CLOUDSDK_CONFIG="$PWD/artifacts/live-gke/gcloud"
export GH_TOKEN="$(gh auth token --hostname github.com --user dlobato)"
artifacts/runner-dispatcher/drydock-dispatcher \
  --configuration artifacts/runner-dispatcher/operator.json
unset GH_TOKEN
```

The dispatcher creates a unique journal under `artifacts/runner-dispatcher/`.
Its JSON records contain identities, decisions, and deletion outcomes without credentials.
The VM has a 900-second GCE deletion deadline.
The runner process has a 600-second deadline after startup.
The operator process starts cleanup after its 20-minute execution deadline.
Cleanup has separate bounded API deadlines and allows six minutes for the VM driver to finish.
The workflow retains its separate five-minute job deadline.
These deadlines do not extend a lab lifetime.

The dispatcher removes the VM, SSH keys, runner registration, queue session, and scale set after the attempt.
A failed access job still requires successful infrastructure deletion.
Inspect both the GitHub job result and the operator journal.
A successful dispatcher exit describes runner execution and cleanup, not the probe's access or network result.

## Recover an interrupted operator

Use SIGINT or SIGTERM for normal interruption. These signals start cleanup.
A hard kill or host loss prevents the operator's cleanup handlers from running.
GCE still deletes the VM at its fixed deadline, including its boot disk.
GitHub registration and scale-set recovery require the operator credential.

Keep the original configuration and unique journal directory.
Select the same isolated operator profile and credential, then run:

```sh
artifacts/runner-dispatcher/drydock-dispatcher \
  --configuration artifacts/runner-dispatcher/operator.json \
  --recover artifacts/runner-dispatcher/drydock-runner-123-1-<12-hexadecimal-digits>
```

Recovery compares the journal's ownership with the live instance and scale set.
It preserves resources whose ownership differs.
If the API is unavailable, retain the journal and repeat recovery after service returns.
If the journal is missing, inspect both providers before deleting any resource.
Never adopt an unrelated runner or remove its scale set to clear a name conflict.

## Evidence boundary

Local tests cover authorization denials, competing reservations, credential isolation, process-group refusal, and owned-resource disposal.
Live evidence belongs in [the access acceptance record](live-github-gke-access.md).
Keep federation disabled until runner authorization, disposal, and the target Kubernetes boundary pass.
This component supplies infrastructure for the no-lab probe in task 8.2.
It does not implement the isolated build, lifecycle, ANTA, and deletion stages in task 8.3.
