# PR checks and optional pre-deployment approval

Every PR opening, reopening, and update starts hosted lint and unit tests.
Fork PRs use the same jobs under GitHub's native execution policies.
These jobs need no custom author approval or `gke` approval.
GitHub can still require approval for workflows from fork contributors.

A separate trusted workflow accepts `[digital-twin-test]` in the latest PR commit or a manual request.
It tests the opt-in approval path with a placeholder job.
It records approval for an exact PR commit without creating a lab or running network tests.
A successful placeholder result establishes only that the approval job completed.
Live GKE integration remains in tasks 8.2 through 8.5.

## Automatic PR checks

`PR checks` runs on GitHub-hosted Ubuntu runners with read-only repository permissions.
The lint job uses the pinned Ruff and mypy hooks through `pre-commit`.
The test job runs strict OpenSpec validation, both offline AVD builds, bundle tests, CLI tests, and workflow tests.
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

The placeholder needs no environment secrets, cloud credentials, private runner, or GKE resources.
Do not add those capabilities before tasks 8.2 and 8.3 establish their authorization and isolation controls.

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
The selector records the exact commit before the placeholder waits for `gke` approval.
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

In Actions, open `Opt-in pre-deployment approval (placeholder)` and select your run.
Read the selected commit in the `select` job summary.
The workflow resolves the PR head before approval and records the workflow commit, run, and attempt.
The approval job name and environment link identify that selected commit.
Manual requests for forks, closed PRs, other base branches, and untrusted workflow references fail selection before approval.
This restriction does not apply to automatic fork PR checks.

Before approval, make sure that the placeholder job waits for review.
Reject the request to test denial, or approve `gke` through Review deployments to test completion.
After approval, read the placeholder summary. It identifies the selected commit and states that no network tests ran.
Rejection prevents the placeholder from running. Neither outcome allocates a lab.

To test commit selection, push an unmarked commit to the PR while approval waits.
Make sure that automatic PR checks start without a second GKE request.
The waiting run keeps its selected commit. A new marker or manual request selects the new head and requests approval separately.
Reruns remain subject to GitHub's environment rules. Review the selected commit before each approval.

## Boundaries before live GKE testing

The selector loads code from the exact workflow commit on protected `main`.
The placeholder executes no PR code and has no repository token permissions.
GitHub holds its environment job until the protection rules permit execution.
Local tests establish the workflow structure and selection behavior. They do not establish live approval enforcement.

Before enabling live jobs, bind provider authentication to the repository, approved `gke` environment, and trusted workflow revision.
Restrict private runner assignment to trusted workflows and isolate Ansible from Kubernetes credentials.
Credentialed jobs must use a pinned trusted lifecycle CLI and treat PR topology files as data.
A workflow condition alone cannot protect credentials from a modified workflow that removes that condition.
Tasks 8.2 through 8.5 retain temporary access, enforced permissions, private execution, reports, cleanup, and live acceptance.

## Test locally

With Node.js 22 installed, run `make workflow-test` for PR selection tests.
With lifecycle dependencies installed, run `.venv/bin/python -m unittest discover -s tests -p test_workflows.py -v`.
These tests use controlled GitHub responses and inspect both workflows without requesting a lab or credentials.
