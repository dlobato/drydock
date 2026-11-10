# Drydock

Drydock will create temporary switch labs for tests before network deployment.
A digital twin is an emulated copy of a network.

This repository contains an anonymized AVD example, an offline build workflow, and an active OpenSpec proposal.
It does not contain a lab service or a working digital twin workflow.

## Build the example

See [the offline example instructions](examples/evpn-symmetric-irb/README.md) for prerequisites, commands, outputs, and validation limits.
The example uses `pyavd[ansible]==6.5.0` and builds exactly six switch configurations.
The build-only GitHub Actions workflow needs no cloud account, device image, or live credentials.
An offline build does not establish working MLAG or a functioning digital twin.

## First milestone

A GitHub Actions workflow will build an example with AVD, create a lab, run ANTA, save results, and delete the lab.
The workflow targets trusted contributors in private GitHub repositories.
Labs contain switches only, starting with cEOS. CloudVision is permanently excluded.

The example contains two spines and four leaves arranged as two MLAG pairs.
MLAG lets two switches act as one logical pair.
The example preserves the reference configuration behavior with generic names, synthetic addresses, and lab credentials supplied at runtime.

GKE Standard and clabernetes are the infrastructure direction.
GitHub Actions owns AVD, ANTA, and test reports.
Drydock owns lab creation, readiness, private management access, and cleanup.
The framework, database, runner deployment, and provisioning tools remain undecided.

## Work with OpenSpec

Use OpenSpec 1.16.0. The bootstrap used the standalone CLI.
Run these commands from this repository:

```sh
make spec-check
make spec-status
```

OpenSpec generated the Codex skills in `.agents/skills/`.
Use `$openspec-propose` to plan a change and `$openspec-apply-change` to implement an authorized change.
Use `$openspec-archive-change` after implementation and validation.

The first proposal is [add-digital-twin-pipeline](openspec/changes/add-digital-twin-pipeline/proposal.md).
Proposed requirements stay under `openspec/changes/` until implementation and archive.
Current implemented requirements belong under `openspec/specs/`, which is empty at bootstrap.

## Acceptance and remaining decisions

The milestone requires working MLAG, passing network tests, saved reports, and evidence that temporary resources are deleted.
Cleanup must also cover failures, cancellation, timeout, and loss of the runner.
A passing OpenSpec result establishes document structure only.

The previous clabernetes experiment left MLAG unresolved.
Its firewall workaround and suspected connection-tracking cause are not accepted Drydock behavior.
The separate investigation must establish a supported runtime before acceptance.

The proposal records configuration delivery, the service boundary, lab expiry, and development infrastructure lifetime as decisions before implementation.
No fixed budget cap or lab timeout is agreed.
The eventual 1,000-device target is outside this milestone.

See [the reference notes](docs/references.md) for the source material and investigation context.
