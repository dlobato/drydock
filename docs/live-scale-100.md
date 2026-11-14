# Single 100-switch qualification attempt

The November 14 attempt stopped before worker allocation because Google rejected the requested capacity.
The project-wide `CPUS_ALL_REGIONS` quota permits 32 vCPUs, with two in use and 30 available.
The four approved `n2-standard-32` workers require 128 vCPUs, which exceeds the available quota by 98.
Regional `N2_CPUS` quota permits 200 vCPUs, but that separate limit does not override the project-wide limit.
An independent quota read confirmed the project-wide limit after the rejection.

No scale worker, lab, switch, private runner, or GitHub scale workflow started.
The attempt produced no live network results or workflow artifact.
Task 9.1 remains unchecked at 40/44 tasks complete.
The earlier offline preparation remains valid, but it does not qualify live scale.

## Approved attempt

The user approved one attempt with four private `n2-standard-32` workers and one disposable runner.
[PR #29](https://github.com/dlobato/drydock/pull/29) merged as trusted revision `43eb6a4b0916a6e4903486555f385a65d19ee8d8` before preparation began.
[PR #30](https://github.com/dlobato/drydock/pull/30) records this attempt.
No manual scale workflow was dispatched because worker preparation failed.

The selected fabric contains two spines, 98 leaves, 49 MLAG pairs, and 294 links.
The offline preparation produced 1,088 required ANTA entries.
The approved boundary retained the 900-second startup limit and the 30-minute default lab lifetime.
It required removal to start within 90 minutes of the first temporary worker allocation.
The rejected pool request allocated no workers.
The operator made no retry, capacity increase, quota change, or expiry extension.

## Cleanup

The operator stopped image publication after the capacity rejection and deleted the temporary private image repository.
The runtime, admission webhook, independent cleaner, lab permissions, firewall rules, and disposable runner were never installed.
Federation remained disabled, and cleanup restored its original trust condition and the saved protected variables.
The operator removed the temporary local registry credential file.

Independent API inspection found only the original system pool, node VM, and disk.
The original node remained running and Ready.
Namespaces, firewall rules, CRDs, cluster roles, bindings, and validating webhooks matched their saved baselines.
No temporary image repository, GitHub runner registration, runner scale set, or temporary token-minting grant remained.
The provider remained disabled with its original trust condition, and protected variables matched the saved baseline.
Local inspection found no temporary registry credential file, runner keys, TLS private key, or local registry.
The shared cluster and network remain available.

## Qualification limit

This attempt does not establish authenticated switch readiness, network acceptance, startup timing, resource pressure, or deletion of a live scale lab.
A future attempt requires sufficient project-wide quota and fresh approval for its resource boundary.
At this baseline, the plan requires at least 132 project-wide vCPUs: two existing, 128 for workers, and two for the runner.
It must repeat the complete acceptance and cleanup requirements in the [qualification plan](scale-qualification.md).
Tasks 9.2 through 9.4 retain concurrency, failure-path, and provider qualification.
