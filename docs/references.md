# Reference material

These paths identify local source material for contributors with access to the original workspace.
They are documentation references, not dependencies for a Drydock build.
No source files or credentials were copied during bootstrap.

## Workflow reference

The reference is the digital twin portion of the Vantage pre-deployment pipeline:

```text
/home/dlobato/workspace/vantage/vantage-gardener/templates/partner-avd-project-cookiecutter/{{cookiecutter.project_basename}}/.gitlab/pre-deployment-pipeline.yml
```

Its sequence builds configurations, creates an ACT lab, deploys through eAPI, runs ANTA, and retains reports.
Drydock will use GKE and clabernetes for lab creation.
Drydock requires automatic cleanup after success, failure, cancellation, and timeout.
The reference includes optional CloudVision paths, which Drydock excludes.

## Fabric reference

The selected source fabric is:

```text
/home/dlobato/workspace/ps/skus/ps-sku-l3ls/EVPN-symmetric-IRB
```

It pins `pyavd[ansible]==6.4.0` and contains two spines and two MLAG leaf pairs.
Its server definitions describe attached endpoints. Drydock must not deploy host containers.
The new example must replace names, addresses, identifiers, and credentials while preserving the topology and network behavior.

The reference ANTA playbook skips interface, port-channel, and MLAG-interface tests.
Those exclusions cannot establish MLAG acceptance for Drydock.
The implementation must distinguish absent endpoint links from switch links that must work.

## MLAG investigation

The earlier experiment is separate from this repository:

```text
/home/dlobato/workspace/dlobato/clabernetes-gke-l3ls-poc
```

That experiment used a larger fabric with 12 switches, clabernetes v0.10.1, and cEOS 4.36.1F.
Peer links and ping worked, but the MLAG TCP handshake stalled.
A narrow firewall rule restored MLAG without a restart.
A mismatch between connection-tracking zones is an unconfirmed lead.
Neither that rule nor that diagnosis is an accepted implementation.

The six-switch example still requires its own runtime evidence.
The bootstrap did not rerun the experiment or inspect newer investigation results.
