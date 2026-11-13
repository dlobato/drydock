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

Live approval tests remain pending. They require no GKE cluster or private runner.
The access job must receive neither a runner nor credentials while approval is absent or rejected.

## Remaining acceptance

The repository belongs to a personal GitHub account.
An organization runner group with workflow restrictions is not available inside this repository.
Runner labels do not restrict which workflow can request private execution.
The operator must supply an enforced execution boundary before registering private capacity.

The remaining tests require a private GKE target, admission installation, and a controlled disposable runner.
They must prove temporary identity exchange, GKE identity mapping, allowed lifecycle operations, and the specified Kubernetes and Google denials.
Task 8.2 remains unchecked until these tests pass.
See [the operator procedure](github-gke-access.md) for the deployment requirements and denial cases.
