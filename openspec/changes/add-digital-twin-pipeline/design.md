# Design

## Context

See [the proposal](proposal.md) for the milestone and [the reference notes](../../../docs/references.md) for observed source behavior.
The first PR implements only the anonymized example and an offline build workflow.
The broader milestone remains active.
The reference deploys configurations through eAPI after ACT starts the lab.
The earlier Drydock direction starts switches with the proposed configurations.

This document proposes a minimal baseline for review.
The choices below are proposals, not additional user agreements.
No cloud resources are provisioned during bootstrap.

## Goals / Non-Goals

The design connects one six-switch example to an observable lab lifecycle.
It keeps infrastructure readiness separate from network acceptance.
It also supports deletion without a surviving GitHub runner.

This milestone does not require an HTTP service, database, user interface, or runner controller.
It does not establish capacity for large labs.
It does not migrate the Vantage project or change the source fabric.

## Decisions

### Build the example offline first

The authorized first PR uses `pyavd[ansible]==6.5.0` and the matching `arista.avd` collection.
It renders two spines and two MLAG leaf pairs without the reference repository or live credentials.
Runtime lab credentials enter through environment variables. The build workflow supplies synthetic values.
Generated files stay ignored and are not uploaded by this workflow.
AVD validates its input models. Generated configurations require no separate assertion tests.
The first PR records manual inspection of six configurations, both MLAG pairs, all spine links, and the routing and overlay configuration.

GKE, lifecycle commands, cleanup, live ANTA, and runtime versions remain deferred.
The separate MLAG investigation does not block offline generation.
An offline build does not prove working MLAG or a functioning digital twin.
See [the example instructions](../../../examples/evpn-symmetric-irb/README.md) for commands and output locations.

### Build the offline Containerlab bundle

Task 2.4 reuses the Containerlab generator in the pinned AVD 6.5.0 dependency.
A separate digital twin build preserves the existing offline build and keeps its output apart from the bundle.
AVD derives the switch nodes, links, management addresses, and interface mapping from the same fabric input.
This avoids a second topology template that can diverge from the configurations.
The generated topology contains six `arista_ceos` switches, eight spine links, and four MLAG peer links.
Endpoint definitions remain in the configurations but create no containers or lab links.
An empty Containerlab prefix preserves the original device names.

Use the startup configuration paths and interface mapping that AVD generates.
Digital twin mode removes BGP `update wait-install` and the spine `update wait-for-convergence` commands from the EOS output.
Offline comparison found no other EOS changes when both builds used the same credentials.
This is a rendering choice only. Startup delivery still requires live acceptance under task 1.1.
The lifecycle command interface remains a proposal.

Require `DRYDOCK_CEOS_IMAGE` when packaging instead of retaining the generator's implicit `arista/ceos:latest` image.
The offline workflow uses `ceos:offline-placeholder` and never pulls or runs that image.
An explicit image value records the requested image. It does not establish runtime support.
The AVD preview generator uses one fixed management network and subnet, so this bundle does not establish concurrent lab isolation.
The lifecycle implementation must resolve that boundary before live use.

Package only the topology, interface mapping, and six referenced EOS configurations in a portable tar archive.
Keep all paths relative and normalize archive order, timestamps, ownership, and permissions.
Record the SHA-256 digest beside the archive in a format that `sha256sum -c` accepts.
Identical inputs produce identical archive bytes. Changed credentials or image values change the digest.
The archive contains lab authentication material, so keep it ignored and do not upload it from the offline workflow.
Tests compare the archived identities, management addresses, and links with AVD output and require both MLAG pairs.
Tests also cover missing input files, digest changes, and reproducible packaging.
These tests establish offline bundle consistency, not switch startup, routing, MLAG convergence, or cleanup.

### Propose startup configuration delivery

Supply each rendered configuration as the initial configuration for its switch.
This follows the earlier Drydock direction and keeps AVD outside the lab lifecycle implementation.
The input contains one complete Containerlab topology and the matching configuration files.
Record a digest for the submitted bundle and preserve the original device names.

The alternative is an eAPI deployment step after startup, as the Vantage reference uses.
That alternative requires bootstrap credentials and another configuration transition.
Acceptance must prove that the selected runtime applies the supplied startup configuration.
If runtime evidence requires a different delivery path, revise this design before implementation.

### Propose a command interface for the first integration

Start with create, status, and delete commands that return structured results for GitHub Actions.
Use the existing GKE and clabernetes control surfaces behind those commands.
Create validates the complete request before allocation.
Status returns infrastructure conditions and the connection inventory.
Delete removes only resources owned by the identified lab.

The alternative is an HTTP service with persistent application storage.
The first workflow does not require that additional service boundary.
A framework and database remain unselected.
The eventual service can preserve the same lifecycle behavior if it becomes necessary.

### Propose explicit ownership and independent expiry

Use a shared GKE Standard control plane and system workers, with dedicated temporary workers for each lab.
Assign the lab identity before allocation and attach ownership metadata to every temporary resource.
Store enough durable lifecycle information outside the runner to discover partial allocations and retry deletion.
Use existing Kubernetes storage for initial lifecycle records unless runtime evidence requires another store.

A scheduled cleanup job runs on shared infrastructure and reclaims expired labs independently of GitHub Actions.
The caller supplies a finite expiry. No numeric default is selected by this proposal.
Document the expiry interval, cleanup cadence, retry policy, and resulting deletion bound before live use.
The cleaner must discover provider resources even when allocation stops before a lifecycle record update.

A workflow step with `always()` provides immediate cleanup but cannot cover runner loss by itself.
Do not use workflow cleanup as the only deletion mechanism.

### Propose explicit shared infrastructure ownership

Treat the control plane, system workers, private runner access, and registry as operator-managed development prerequisites.
Lab deletion removes lab workers and temporary lab resources.
It does not remove shared development infrastructure.
Document creation and teardown separately before any provisioning request.

Creating a fresh control plane per workflow is the alternative.
It adds startup and teardown work beyond the chosen shared infrastructure direction.
The shared development environment lifetime requires operator approval before provisioning.

### Keep test ownership in GitHub Actions

Build the anonymized example with AVD 6.5.0 as the offline baseline.
Run ANTA through the returned private management inventory after infrastructure readiness.
Keep convergence waits bounded and record runtime versions with the submitted bundle digest.
Pin the supported runtime only after the separate MLAG investigation provides evidence.

Retain JSON and JUnit results, the executed catalog, logs, and available diagnostics.
Required switch links and MLAG tests cannot inherit the reference skip list without justification.
Distinguish unused endpoint interfaces from required switch links.
Record both network acceptance and cleanup outcomes without hiding the original failure.

## Risks / Trade-offs

The supported cEOS and clabernetes combination remains unproven for this example.
Require a cold-start run with both MLAG pairs active and no experimental firewall rule before milestone acceptance.
Record the separate investigation outcome and the exact supported image digests.

A runner can disappear after resource allocation but before it records the result.
Require ownership-based discovery and demonstrate independent expiry after partial allocation.

Shared infrastructure can outlive all labs and continue to cost money.
Require an explicit development environment lifetime and a separate teardown procedure before provisioning.

Switch-only tests do not prove application traffic between attached hosts.
State the traffic coverage that the selected ANTA catalog actually provides.
Do not describe control-plane tests as end-to-end tenant traffic evidence.

Reports and generated configurations can contain authentication material.
Use runtime lab credentials and exclude secrets from retained artifacts.

## Migration Plan

There is no existing Drydock deployment to migrate.
Review the proposed baseline before implementation.
Build the example locally before adding live infrastructure integration.
Run one explicitly authorized development lab before enabling automatic pull request triggers.

To roll back, disable workflow triggers and stop new lab requests.
Keep the independent cleaner active until all temporary resources are deleted.
Delete shared development infrastructure only through its separate teardown procedure.

## Open Questions

The cloud project, region, worker size, and supported image digests require environment-specific values before live execution.
Artifact retention needs a repository policy value.
Neither choice changes the lifecycle or test ownership described above.
