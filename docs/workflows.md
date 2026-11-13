# PR checks and optional pre-deployment approval

Every PR opening, reopening, and update starts hosted lint and unit tests.
Fork PRs use the same jobs under GitHub's native execution policies.
These jobs need no custom author approval or `gke` approval.
GitHub can still require approval for workflows from fork contributors.

A separate trusted workflow accepts `[digital-twin-test]` in the latest PR commit or a manual request.
It requests temporary GKE access after approval through the protected `gke` environment.
It records approval for an exact PR commit without creating a lab or running network tests.
A successful probe establishes only temporary access and permission denials.
Live GKE integration remains in tasks 8.2 through 8.5.

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

Complete [the GKE access setup](github-gke-access.md) before requesting the credentialed probe.
The provider stays disabled until the target cluster's admission and private runner controls pass.
Use [the operator dispatcher](runner-dispatcher.md) for disposable private execution after native approval.
The probe receives a 15-minute token. It needs no personal key or lab password.

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
The selector records the exact commit before the access job waits for `gke` approval.
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

In Actions, open `Opt-in GKE access probe` and select your run.
Read the selected commit in the `select` job summary.
The workflow resolves the PR head before approval and records the workflow commit, run, and attempt.
The approval job name and environment link identify that selected commit.
Manual requests for forks, closed PRs, other base branches, and untrusted workflow references fail selection before approval.
This restriction does not apply to automatic fork PR checks.

Before approval, make sure that the access job waits for review.
Reject the request to test denial, or approve `gke` through Review deployments to test completion.
After approval, the operator starts the dispatcher for that exact run and attempt.
Without a dispatcher, the approved job remains queued without private capacity.
After execution, read the access summary. It identifies the selected commit and states that no network tests ran.
Rejection prevents token issuance and probe execution. Neither outcome allocates a lab.

To test commit selection, push an unmarked commit to the PR while approval waits.
Make sure that automatic PR checks start without a second GKE request.
The waiting run keeps its selected commit. A new marker or manual request selects the new head and requests approval separately.
Reruns remain subject to GitHub's environment rules. Review the selected commit before each approval.

## Boundaries before live GKE testing

The selector loads code from the exact workflow commit on protected `main`.
The access job checks out only the exact trusted workflow commit.
Only that environment-approved job receives `id-token: write` and read-only repository access.
The Google action exchanges its identity for a 900-second access token without creating a reusable credential file.
The probe keeps the temporary kubeconfig in a restricted directory and removes it after success or failure.
It receives no Ansible input or PR code.
GitHub holds its environment job until the protection rules permit execution.
Local tests establish the workflow structure and selection behavior. They do not establish live approval enforcement.

The [federation setup](github-gke-access.md) binds authentication to numeric repository identities, the approved environment, and the trusted workflow revision.
Restrict private runner assignment to trusted workflows and isolate Ansible from Kubernetes credentials.
Credentialed jobs must use a pinned trusted lifecycle CLI and treat PR topology files as data.
A workflow condition alone cannot protect credentials from a modified workflow that removes that condition.
Tasks 8.2 through 8.5 retain temporary access, enforced permissions, private execution, reports, cleanup, and live acceptance.

## Test locally

With Node.js 22 installed, run `make workflow-test` for PR selection tests.
With lifecycle dependencies installed, run `.venv/bin/python -m unittest discover -s tests -p test_workflows.py -v`.
These tests use controlled GitHub responses and inspect both workflows without requesting a lab or credentials.
