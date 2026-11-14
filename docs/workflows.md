# PR checks and optional pre-deployment approval

Every PR opening, reopening, and update starts hosted lint and unit tests.
Fork PRs use the same jobs under GitHub's native execution policies.
These jobs need no custom author approval or `gke` approval.
GitHub can still require approval for workflows from fork contributors.

A separate trusted workflow accepts `[digital-twin-test]` in the latest PR commit or a manual request.
It requests a six-switch lab after approval through the protected `gke` environment.
It builds the selected commit, establishes model consistency and coverage, and runs standard ANTA through the lifecycle CLI.
Task 8.2 passed [scoped GitHub-to-GKE access acceptance](live-github-gke-access.md#email-scope-acceptance-request).
Task 8.3 implements lab orchestration with isolated containers and controlled failure tests.
Report uploads and complete live workflow acceptance remain in tasks 8.4 and 8.5.

## Automatic PR checks

`PR checks` runs on GitHub-hosted Ubuntu runners with read-only repository permissions.
The lint job uses the pinned Ruff and mypy hooks through `pre-commit`.
The test job runs strict OpenSpec validation, both offline AVD builds, bundle tests, CLI tests, and workflow tests.
It also tests dispatcher authorization, Go formatting, race detection, and static analysis.
The builds use synthetic credentials and a placeholder cEOS image name.
They do not pull or boot a switch image.

PR events without the marker never leave a `gke` job waiting for approval.
The automatic jobs receive no private runner, cloud credentials, or permission to request an identity token.
Checkout does not retain the GitHub token. Actions use pinned commits.
The workflows upload no generated configurations.

## Protect the environment

In repository Settings, open Environments and select `gke`.
Make sure that these rules are present before testing the approval path:

- Required reviewer: `dlobato`, the repository owner.
- Prevent self-review: disabled, so the owner can approve a request that the owner starts.
- Administrator bypass: disabled.
- Deployment branches and tags: selected branches and tags, with one branch rule for `main` and no tag rules.

The environment name in YAML does not create these protection rules.
Keep `main` protected and review workflow changes before merge.
The branch rule allows the trusted workflow to test proposed PR input before merge.
It does not require the PR branch to deploy or execute its own workflow definition.

Complete [the GKE access setup](github-gke-access.md) before requesting a lab.
The provider stays disabled until the target cluster's admission and private runner controls pass.
Use [the operator dispatcher](runner-dispatcher.md) for disposable private execution after native approval.
The official Google action supplies temporary federation after the build passes.
Only lifecycle containers receive the resulting refreshable credential file.
The coordinator generates a separate lab password for each attempt.

## Request with a commit marker

Merge the workflow definition into `main` before testing the marker trigger.
GitHub loads `pull_request_target`, a PR event with trusted base code, from `main`.
A marker commit in the PR that installs this definition cannot exercise its new trigger before merge.
After merge, create or update a same-repository PR into `main` with this marker in its latest commit message:

```sh
git commit -m "Update sample fabric [digital-twin-test]"
git push
```

The marker is case-sensitive and can appear in the commit subject or body.
Only the latest PR head counts. A marker in an earlier commit does not request approval for a later unmarked head.
Do not combine this marker with `[skip ci]`, because GitHub skips the ordinary PR checks for that commit.

The trusted selector reads metadata through GitHub's API. It never checks out or executes PR code.
It requires an open same-repository PR into `main` and an event SHA that matches the observed PR head.
Fork PRs and stale events request no approval. The separate ordinary PR checks still accept eligible fork PRs.
The selector dispatches this workflow with the exact commit through `workflow_dispatch`.
The PR event executes metadata selection only. It cannot assign a private runner or execute PR code.
The dispatch selector rejects a changed head before it requests approval.
The lab job records the exact commit before it waits for `gke` approval.
The marker requests approval. It grants no cloud access and cannot replace the required reviewer.

## Request manually

The same workflow still accepts manual dispatch from `main`.
GitHub requires that definition to exist on the default branch before dispatch.
Keep an open same-repository PR into `main` as the test input.

With GitHub CLI authenticated for this repository, request approval from your workstation:

```sh
gh workflow run pre-deployment.yml --repo dlobato/drydock --ref main \
  -f pull_request=<PR_NUMBER>
```

Users with GitHub's native dispatch permission can request a run. Only the required environment reviewer can approve it.
No custom launch or rerun actor allowlist applies.

## Test approval

In Actions, open `Opt-in digital twin` and select the dispatched run.
Read the selected commit in the `select` job summary.
The workflow resolves the PR head before approval and records the workflow commit, run, and attempt.
The approval job name and environment link identify that selected commit.
Manual requests for forks, closed PRs, other base branches, and untrusted workflow references fail selection before approval.
This restriction does not apply to automatic fork PR checks.

Before approval, make sure that the lab job waits for review.
Reject the request to test denial, or approve `gke` through Review deployments to test completion.
After approval, the operator starts the dispatcher for that exact run and attempt.
Without a dispatcher, the approved job remains queued without private capacity.
After execution, read the job summary for separate test and deletion outcomes.
Rejection prevents runner assignment, token issuance, and lab allocation.

To test commit selection, push an unmarked commit to the PR while approval waits.
Make sure that automatic PR checks start without a second GKE request.
The waiting run keeps its selected commit. A new marker or manual request selects the new head and requests approval separately.
Reruns remain subject to GitHub's environment rules. Review the selected commit before each approval.

## Isolated pipeline execution

On the operator workstation, build the toolchain from reviewed source images pinned by digest:

```sh
docker build -f examples/github/Dockerfile.pipeline \
  --build-arg PYTHON_IMAGE="$DRYDOCK_PYTHON_IMAGE" \
  --build-arg KUBECTL_IMAGE="$DRYDOCK_KUBECTL_IMAGE" \
  --build-arg GCLOUD_IMAGE="$DRYDOCK_GCLOUD_IMAGE" \
  -t "$DRYDOCK_PIPELINE_IMAGE" .
```

Use Python 3.13 slim, the kubectl image with `/bin/kubectl`, and the Google Cloud CLI slim image with `/usr/lib/google-cloud-sdk`.
Set all four image variables to the reviewed image references before this command.
Make the resulting image available to disposable runners, then set `GKE_PIPELINE_IMAGE` to its published digest.
Set `DRYDOCK_CEOS_IMAGE` to the approved switch image digest and `DRYDOCK_ENVIRONMENT` to the lifecycle environment name.
These variables belong to the protected `gke` environment.
The target cluster needs clabernetes, switch capacity, image access, admission, and the independent cleaner before a live request.

The selector loads code from the exact workflow commit on protected `main`.
The approved coordinator checks out the trusted workflow and the selected PR into separate directories.
It executes only trusted coordinator code on the runner host.
Only this job receives `id-token: write`. The coordinator never passes that permission or the GitHub token endpoint into Ansible containers.
The operator supplies one toolchain image through `GKE_PIPELINE_IMAGE`, pinned by SHA-256 digest.
The image contains Python 3.13, AVD 6.5.0, ANTA 1.10.0, the pinned collection, kubectl, and Google Cloud CLI.
The operator must make that image available without supplying registry credentials to PR containers.

Build, preflight, creation, readiness, ANTA, and deletion each use a fresh container.
Every container uses a nonroot user, a read-only root filesystem, dropped capabilities, and bounded memory and process counts.
Containers receive no host socket, host process namespace, or runner credential directory.
Build and preflight containers have no network access.
The build runs the selected PR's standard AVD playbook with a generated lab password.
After the build stops, the coordinator copies bounded regular output files into a separate input snapshot.
Symlinks, hard links, special files, and output above 128 MiB fail before allocation.
Preflight compares AVD models with startup files and requires all applicable catalogs, including both MLAG pairs.

The official action creates an external-account file after preflight succeeds.
That file exchanges the job identity for temporary Google access. It contains no personal key.
Only creation, readiness, and deletion containers mount that file.
The provider helper supplies kubectl credentials through an execution plugin, a program that returns a temporary token.
Google Cloud CLI renews access with both required scopes and a 900-second impersonation lifetime.
Kubernetes keeps its private endpoint and CA verification.
The independent cleaner retains its separate identity if renewal fails or the runner disappears.

ANTA receives the immutable input, current connection inventory, and lab password without cloud credentials or token issuance access.
Its inventory overlay changes connection addresses and ports while retaining source groups and test variables.
The standard `arista.avd.anta_runner` playbook owns network acceptance.
Startup and ANTA deadlines consume the same 30-minute lifetime without renewal.
The CLI writes a new recovery identity file before allocation, so deletion can recover after lost creation output.
Recovery deletion requires that recorded allocation ID and preserves a different creation request.
It requests deletion after every allocation attempt and repeats deletion in an unconditional workflow step.
Test and deletion failures remain separate, and either failure prevents success.

Generated startup files and models remain on the disposable runner.
The workflow uploads no artifacts in task 8.3. Its final step removes temporary input, credentials, and local reports.
Task 8.4 must add safe report retention before task 8.5 establishes complete workflow acceptance.
GitHub holds its environment job until the protection rules permit execution.
Local tests establish the workflow structure and selection behavior. They do not establish live approval enforcement.

The [federation setup](github-gke-access.md) binds authentication to numeric repository identities, the approved environment, and the trusted workflow revision.
Restrict private runner assignment to trusted workflows and isolate Ansible from Kubernetes credentials.
Credentialed jobs must use a pinned trusted lifecycle CLI and treat PR topology files as data.
A workflow condition alone cannot protect credentials from a modified workflow that removes that condition.
Task 8.2 records scoped access and disposable-runner acceptance.
Tasks 8.4 and 8.5 retain report handling and complete live workflow acceptance.

## Test locally

With Node.js 22 installed, run `make workflow-test` for PR selection tests.
With lifecycle dependencies installed, run `.venv/bin/python -m unittest discover -s tests -p test_workflows.py -v`.
These tests use controlled GitHub responses and inspect both workflows without requesting a lab or credentials.
