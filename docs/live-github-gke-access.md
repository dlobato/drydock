# GitHub-to-GKE access acceptance

This record covers task 8.2 access acceptance. It does not establish network acceptance.

## Trusted revision

PR #20 merged into protected `main` as `44e6caa176108eb5be62252bf1363678086680e0` on November 13, 2026.
The Google federation provider trusts that exact workflow revision and retains every other identity restriction.
The provider remains disabled.

The `gke` environment requires owner review, disables administrator bypass, and restricts deployments to `main`.
The project contains no GKE cluster or compute instance. The repository contains no registered private runner.
These observations describe the inspected state, not a deployment guarantee.

## Approval boundary

The marked head of PR #21 requested the merged trusted workflow for exact input `9af7cffc0e218e130da0bb377824ef5985b6f88d`.
[Run 43429024041](https://github.com/dlobato/drydock/actions/runs/43429024041) reached the native `gke` approval gate.
The hosted selector completed before the access job waited for approval.

API inspection recorded the access job with no runner, no runner name, and no executed steps while approval was absent.
The operator then rejected the deployment through GitHub's native review endpoint.
The run and access job ended with the expected failure result.
Final API inspection recorded no assigned runner and no executed steps after rejection.
The authentication action never started. These observations required no private capacity or enabled federation.

The run identifies the PR input separately from the trusted workflow revision on `main`.
No PR code executed in the credentialed job.

## Remaining acceptance

The repository belongs to a personal GitHub account.
An organization runner group with workflow restrictions is not available inside this repository.
Runner labels do not restrict which workflow can request private execution.
The operator must supply an enforced execution boundary before registering private capacity.

## Proposed runner boundary

This proposal is not an accepted design or an installed component.
Use an operator-controlled dispatcher with GitHub's runner scale-set interface.
A scale set groups disposable runners and exposes queued job identities before acquisition.
The [official SDK](https://github.com/actions/scaleset) exposes workflow references, events, run identifiers, and explicit job acquisition.

The dispatcher must enforce these steps outside workflow YAML:

1. Inspect GitHub's queued job identity and the corresponding environment review for the exact run attempt.
2. Accept only the reviewed repository's trusted workflow on protected `main` after `gke` approval.
3. Acquire only an accepted job, then create one disposable runner with private routes and no administrative credentials.
4. Keep GitHub registration and cloud administration credentials in the operator process, outside the runner.
5. Destroy the runner after completion, cancellation, provisioning failure, or a fixed timeout.

The provider must retain its separate exact workflow SHA restriction.
The dispatcher must deny PR-controlled workflows even when they request identical runner labels.
Missing identity data, failed review lookup, or an unavailable GitHub API must prevent acquisition.
Tests must demonstrate those denials before federation is enabled.

This adds an operator component. Its implementation and dependency choice require an accepted design.
No dispatcher, runner registration, or cloud capacity was created for this proposal.

## Remaining target tests

The remaining tests require a private GKE target, admission installation, and a controlled disposable runner.
They must prove temporary identity exchange, GKE identity mapping, allowed lifecycle operations, and the specified Kubernetes and Google denials.
Task 8.2 remains unchecked until these tests pass.
See [the operator procedure](github-gke-access.md) for the deployment requirements and denial cases.
