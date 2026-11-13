# Manage a lab

The lifecycle CLI uses a supplied Kubernetes context on an existing clabernetes cluster.
It does not require AVD, ANTA, Google Cloud CLI, or cloud administration permissions.
Kubernetes authentication can use an operator-configured provider plugin without cloud administration access.
Run commands from the repository root.

## Prepare the cluster

The cluster operator installs clabernetes and supplies worker capacity, private routing, and access to the digest-pinned cEOS image.
Image access must work for switch workloads in newly created lab namespaces.
The CLI does not create image pull credentials or select worker pools.
The operator supplies scheduling policy through the cluster and clabernetes configuration.

Private image access must cover both kubelet pulls and clabernetes controller metadata reads.
For a registry with a private CA, the operator supplies certificate trust to the controller and every eligible worker runtime.
Keep registry TLS verification enabled.
A pull Secret stores registry credentials in Kubernetes.
The tested private runtime uses global `imagePull.pullSecrets` references to operator-supplied Secrets in each lab namespace.
The operator supplies and refreshes those credentials outside the lifecycle CLI.
Worker identity alone does not supply credentials for the tested controller's metadata reads.

The operator must supply image access before clabernetes starts switch preparation in each new namespace.
Use an operator-managed mechanism to deliver credentials as namespaces appear.
The lifecycle CLI does not copy existing registry Secrets into new namespaces.
If late credentials leave switch preparation failed, the operator must restore access and request backend reconciliation.
This retry does not extend lab expiry.
Automatic recovery after late credentials remains unqualified.

The operator creates the `<name>-system` namespace for ownership records and installs an independent cleaner.
The optional GKE demo setup supplies these resources through separate operator tooling.
The cleaner uses a mounted Kubernetes service-account token and CA certificate.
It runs `python -m drydock --environment /environment/environment.yml reap` every five minutes.
Its environment file selects the mounted kubeconfig and its explicit `cleaner` context.
The cleaner does not require cloud credentials.

The caller needs permission to manage ownership ConfigMaps, owned lab namespaces, startup Secrets, and clabernetes topologies.
Readiness also needs access to clabernetes nodes, links, Pods, and Services.
The current CLI lists namespaces to inspect ownership.
The operator must enforce the authorized lab boundary through Kubernetes permissions and admission policy.
The pipeline permission policy remains task 8.2.

The runner needs private routes to the Kubernetes API and switch Pod addresses on TCP port 443.
The private demo skips switch TLS certificate verification by agreement.
Password authentication and EOS hostname comparison remain required.
This exception does not apply to Kubernetes TLS verification.

## Install and select access

Use Python 3.13 and `kubectl` on the runner.
Install the lifecycle dependency:

```sh
make lifecycle-deps
mkdir -p artifacts
cp examples/lifecycle.yml artifacts/lifecycle.yml
```

Edit `artifacts/lifecycle.yml`:

```yaml
name: drydock-demo
kubeconfig: /absolute/path/to/kubeconfig
context: your-lab-context
```

The environment name determines the ownership namespace and lab namespace prefix.
Every Kubernetes command passes the kubeconfig and context explicitly.
The CLI does not change the global Kubernetes context or cloud account.
Relative kubeconfig paths resolve from the command's working directory.

## Install the independent cleaner

The cluster operator installs the cleaner before accepting lab requests.
Build the image with the [cleaner image procedure](demo-flow.md#prepare-the-cleaner-image).
Set `DRYDOCK_CLEANUP_IMAGE` to its published digest reference.
Use the Kubernetes environment file from the previous procedure.
Render the manifests without contacting Kubernetes:

```sh
.venv/bin/python -m drydock.cleaner --environment artifacts/lifecycle.yml \
  --image "$DRYDOCK_CLEANUP_IMAGE" > artifacts/cleaner.json
```

The output contains a service account, permissions, a mounted kubeconfig, and a CronJob.
A CronJob starts a Kubernetes Job on a schedule.
Its kubeconfig reads the mounted service-account token and CA certificate.
The manifests contain no cloud identity, provider arguments, or worker selector.
The operator supplies scheduling policy that keeps the cleaner available after lab workers stop.
The GKE demo adds its system-node selector outside the reusable generator.

Inspect the rendered permissions against the cluster's lab boundary before installation.
The cleaner lists namespaces and deletes namespaces whose ownership matches the retained record.
It reads and updates ownership ConfigMaps only in the system namespace.
Kubernetes permissions and operator-installed admission policy must restrict access to authorized lab namespaces.
The generated ClusterRole alone does not enforce that restriction. Task 8.2 retains that policy work.

With operator-authorized access, create the ownership namespace and install the manifests.
Set `DRYDOCK_KUBECONFIG` and `DRYDOCK_CONTEXT` from `artifacts/lifecycle.yml`.
Set `DRYDOCK_SYSTEM_NAMESPACE` to the environment name plus `-system`.

```sh
kubectl --kubeconfig "$DRYDOCK_KUBECONFIG" --context "$DRYDOCK_CONTEXT" \
  create namespace "$DRYDOCK_SYSTEM_NAMESPACE" --dry-run=client -o yaml > artifacts/system-namespace.yml
kubectl --kubeconfig "$DRYDOCK_KUBECONFIG" --context "$DRYDOCK_CONTEXT" \
  apply -f artifacts/system-namespace.yml -f artifacts/cleaner.json
```

The operator must supply private registry access for the cleaner image if required.
The cleaner runs one sweep every five minutes without a limit on scheduled retries.
Each Job runs for at most 240 seconds and does not retry inside that Job.
The next scheduled Job resumes incomplete cleanup from Kubernetes records.
Overlapping Jobs are forbidden. A missed start has a 240-second deadline.
Kubernetes or backend unavailability can delay cleanup beyond the target.

## Supply the lab input

The [example AVD build](../examples/evpn-symmetric-irb/README.md) generates the Containerlab topology, interface mapping, and startup files.
Its packager sets the supplied cEOS image reference and archives those generated files.
The lifecycle CLI consumes that output without generating switch configurations or topology links.

Supply an uncompressed tar archive with these files:

- One root-level `*.clab.yml` or `*.clab.yaml` file contains the Containerlab topology.
- Each referenced startup file contains the complete configuration for its switch.
- Each referenced interface mapping file supplies a supported read-only mapping, if required.

AVD structured configurations do not belong in the archive.
The archive must contain exactly the topology and its referenced files.
The archive digest identifies all submitted files together.
Keep the archive private because startup configurations contain authentication material.

### Describe the topology

Clabernetes interprets the topology and manages switch interfaces, management addresses, and links.
Drydock reads switch identities, the link count, and file references for lifecycle operations.
It transfers startup and mapping files without interpreting their contents. The producer supplies consistent configurations.
The example interprets EOS interface mappings only for its ANTA coverage policy.
The six-switch example is one supported input.
Admission uses a field allowlist to exclude unsupported execution features.
The admitted Containerlab fields are:

- Top level: `name`, `topology`, optional empty `prefix`, and optional `mgmt`.
- `mgmt`: optional `ipv4-subnet` and `network`.
- `topology`: `nodes`, `kinds`, optional `defaults`, and optional `links`.
- `defaults`: optional `kind: arista_ceos`.
- `kinds`: one `arista_ceos` entry with `image`, optional `enforce-startup-config: true`, and optional `binds`.
- Each node: `startup-config`, optional `mgmt-ipv4`, `kind: arista_ceos`, `binds`, and `labels`.
- Each link: two `endpoints` that reference admitted switches, plus optional `mtu`. Clabernetes interprets interface names.

Define at least one switch.
Use lowercase DNS labels, up to 63 characters, for switch names.
A DNS label uses letters, digits, and internal hyphens.
The producer supplies valid management addresses or uses the backend defaults.
Supply `kind` on each node or through `defaults`.
Supply one shared digest-pinned cEOS image through `kinds.arista_ceos.image`.
Use an image reference pinned by a SHA-256 digest, such as `registry.example:5000/lab/ceos@sha256:<64-hex-digits>`.
Any registry is accepted, including hosts with a port and Docker Hub references without an explicit registry.
Drydock preserves the image reference and records `docker.io` for an implicit Docker Hub registry.

Admission does not prove image availability, registry authorization, or that the image contains cEOS.
The operator enforces the approved image policy through the cluster.
Offline CLI tests cover creation, authenticated status, and repeated deletion with non-Google image references.
The [live acceptance](live-gke-validation.md#november-12-registry-independent-images) passed with a private, authenticated non-Google registry and all six switches.
That evidence covers the recorded private runtime. Other registries and runtime combinations still require operator qualification.

The producer sets each switch hostname to its topology identity.
Drydock compares the reported hostname during authenticated readiness without parsing startup configuration syntax.
The producer supplies the `labadmin` account and HTTPS eAPI configuration for authenticated readiness.
All file references are relative to the topology at the archive root.
Paths can use letters, digits, underscores, dots, hyphens, and directory separators.
Absolute paths, `.` or `..` components, repeated separators, URLs, and symbolic links are unsupported.

This two-switch example uses the default interface mapping:

```yaml
name: small-lab
mgmt:
  ipv4-subnet: 10.80.0.0/24
topology:
  defaults:
    kind: arista_ceos
  kinds:
    arista_ceos:
      image: registry.example:5000/lab/ceos@sha256:<64-hex-digits>
  nodes:
    edge-a:
      mgmt-ipv4: 10.80.0.10
      startup-config: configs/edge-a.cfg
    edge-b:
      mgmt-ipv4: 10.80.0.11
      startup-config: configs/edge-b.cfg
  links:
    - endpoints: [edge-a:eth1, edge-b:eth1]
```

Replace the image placeholder with an accessible cEOS digest.
Save the topology as `lab.clab.yml` beside the referenced `configs` directory.
From that directory, package the files:

```sh
tar -cf bundle.tar -- lab.clab.yml configs/edge-a.cfg configs/edge-b.cfg
```

For a custom mapping, supply one bind through the kind or node:

```yaml
binds:
  - mappings/edge-a.json:/mnt/flash/EosIntfMapping.json:ro
```

A node bind overrides the shared bind at the same destination. An empty node list retains the shared bind.
Only this read-only mount destination is supported.
For cEOS, a mapping file can contain:

```json
{
  "ManagementIntf": {"eth0": "Management1"},
  "EthernetIntf": {"eth1": "Ethernet1/1", "eth2": "Ethernet1/2"}
}
```

Drydock delivers the mapping file unchanged and does not interpret its JSON keys or EOS interface names.
The producer and backend remain responsible for mapping validity.
Execution hooks, other device kinds, arbitrary host mounts, and all unlisted attributes are unsupported.

Drydock copies the admitted topology and changes only these deployment fields:

- Startup paths and bind sources point to files projected from Kubernetes Secrets.
- Startup configuration enforcement remains enabled, and each node exposes private eAPI port 443.
- The prefix remains empty, and the management network name becomes the unique lab identity.

Topology names, defaults, admitted node attributes, addresses, and links remain intact.
Clabernetes reports topology errors through its status. Successful admission alone does not establish backend validity or readiness.

### Observe file limits

The archive limit is 10 MiB, with at most 1 MiB per member.
Each startup or mapping file must fit within 512 KiB of UTF-8 data.
Combined startup and mapping data can exceed 512 KiB.
Drydock distributes those files across Secrets with at most 512 KiB of decoded data each.
Shared files appear once, and generated file keys prevent collisions between equal basenames.
Each serialized Secret and topology manifest must fit within 1 MiB.
Admission rejects missing files, duplicate members, unsafe paths, unsupported attributes, and oversized resources before Kubernetes allocation.
These limits bound accepted input. They do not establish live switch capacity.

## Create and inspect

Set `DRYDOCK_REPOSITORY` to the repository identity for the request.
Create a lab from the startup-only bundle:

```sh
.venv/bin/python -m drydock --environment artifacts/lifecycle.yml lab create \
  artifacts/example/containerlab/bundle.tar \
  --repository "$DRYDOCK_REPOSITORY" --commit "$(git rev-parse HEAD)" \
  --run local-demo --attempt 1
```

The command records ownership before workload allocation.
It creates a separate lab namespace, startup Secrets, and clabernetes topology.
It does not allocate cloud workers or wait for authenticated readiness.

The lab expires 30 minutes after acceptance by default.
Use `--lifetime` to request an integer from 1 through 60 minutes.
For example, add `--lifetime 60` to request the maximum lifetime.
Invalid values fail before ownership records or workloads are created.
Capacity waiting, startup, and tests consume the same lifetime. Retries do not renew expiry.

Use `--startup-timeout` to set the startup budget in seconds, with a default of 1200 seconds.
The recorded deadline starts at acceptance and cannot exceed lab expiry.
Allocation time and capacity waiting consume that same budget.
The default retains the earlier demo budget. It does not establish a suitable deadline for 100 switches.

A creation failure requests cleanup and returns a nonzero exit code with the lab identity and cleanup outcome.
Creation and deletion retain their Kubernetes records without startup credentials.
The ownership record includes the admitted switch names and link count for status expectations.

Set `DRYDOCK_LAB_ID` to the returned `id`.
Supply the startup configuration's `labadmin` password through `DRYDOCK_LAB_PASSWORD`.
Wait for capacity, switch startup, and authenticated readiness:

```sh
.venv/bin/python -m drydock --environment artifacts/lifecycle.yml lab wait "$DRYDOCK_LAB_ID"
```

The command polls Kubernetes without creating a separate queue or allocating cloud capacity.
Pending switch workloads wait for operator-managed capacity or autoscaling within the recorded deadline.
Retries use the original deadline and expiry. Another wait command does not renew either value.
The first successful readiness observation records `ready_at` before the startup deadline.
Later status requests still require current infrastructure and authenticated management access before lab expiry.
Readiness that completes at or after the deadline fails.
An in-flight Kubernetes or management request can finish after the deadline, but its late response cannot establish readiness.

If startup times out, `lab wait` returns a nonzero exit code and requests deletion of the partial lab.
Cancellation and observation failures also request deletion.
The result retains the startup failure and reports the separate `cleanup` outcome.
If deletion remains incomplete, the independent cleaner retries the retained deleting record.
If the caller disappears, the independent cleaner discovers expiry without extending the lifetime.

Request one authenticated status observation:

```sh
.venv/bin/python -m drydock --environment artifacts/lifecycle.yml lab status "$DRYDOCK_LAB_ID"
```

Status returns one JSON result and a nonzero exit code when the lab is not ready.
It requires current topology and node plans, accepted links, ready Pods, and private eAPI Services.
It discovers current Pod addresses and authenticates to every switch with hostname comparison.
Its connection inventory preserves switch names, Pod names, and Pod UIDs.
The Pod UID identifies one Pod instance.
Readiness re-reads Kubernetes state after authentication and requires unchanged endpoints, current infrastructure, and a running ownership record.
If a Pod changes during authentication, the observation fails and the next attempt discovers its replacement.
Network tests and convergence remain the caller's responsibility.

The JSON `phase` distinguishes these conditions:

| Phase | Meaning |
|---|---|
| `waiting_for_capacity` | A Pod reports `PodScheduled=False` with reason `Unschedulable`. |
| `starting` | The topology, nodes, links, Pods, or private Services are not ready. |
| `management_unavailable` | Infrastructure is ready, but management discovery, authentication, or hostname comparison fails. |
| `ready` | Current infrastructure and authenticated management access meet readiness requirements. |
| `startup_timeout` | Startup reaches its deadline without an earlier successful readiness observation. |
| `expired` | The accepted lab expiry passes. |
| `deleting` or `deleted` | An observed ownership record already prevents readiness. |

The `scheduling` array names unschedulable Pods without copying raw scheduler messages.
This condition can result from resource shortages or scheduling constraints. It does not prove that more workers will resolve it.
The operator inspects detailed scheduler messages in Kubernetes.
`lab status` reports timeout without requesting deletion. Use `lab wait` or `lab delete` for immediate cleanup.
Both status and wait return one final JSON object.
The optional demo diagnostics also include the safe scheduling summary.

## Use runtime connections

Use the private runner and environment file from [Create and inspect](#create-and-inspect).
Retain `DRYDOCK_LAB_ID` and `DRYDOCK_LAB_PASSWORD` from that procedure.
Request a fresh authenticated connection inventory:

```sh
.venv/bin/python -m drydock --environment artifacts/lifecycle.yml lab inventory "$DRYDOCK_LAB_ID" \
  > artifacts/runtime-inventory.json
```

The command returns the same JSON structure and readiness requirements as `lab status`.
It makes one observation without waiting or requesting deletion after failure.
Use its inventory only when the command exits successfully and `ready` is `true`.
A failed observation can retain discovered addresses without successful authentication.

The `inventory` array contains one entry for every submitted switch, sorted by its original name:

- `name` identifies the submitted switch. `tags` contains that name.
- `host` and `port` identify the current private Pod address and HTTPS port 443.
- `namespace`, `pod`, and `pod_uid` identify the observed Kubernetes workload.
- `transport` records `private Pod-IP HTTPS`.

The surrounding result retains the lab ID, ownership record, observation time, and EOS versions returned by authenticated switches.
It excludes the management password.
Missing switches or links, unaccepted links, stale plans, and missing or duplicate Pods prevent readiness.
Unreachable APIs, rejected credentials, and hostname mismatches also prevent readiness.

The runner needs private routes to every returned `host` on TCP port 443.
Use these runtime addresses instead of the topology's management addresses or Service addresses.
The private demo skips switch certificate verification and retains password authentication and hostname comparison.
Kubernetes certificate verification remains enabled.

For an existing Ansible inventory, match each entry by `name`.
Set that host's `ansible_host` to `host` and `ansible_httpapi_port` to `port`.
Preserve its existing groups and test variables.
Supply the management account and password separately through the caller's existing credential handling.
The lifecycle command does not rewrite Ansible inventory or select network tests.

The returned inventory describes one observation and does not reserve a Pod or address.
Refresh it before tests and after Pod replacement.
If endpoints change during authentication, retry `lab inventory` or use `lab wait` within the original deadline.
Neither command renews expiry.

## Ownership and failure output

Each creation request receives a new lab ID, even when its topology, commit, run, and attempt match an earlier request.
Repeating the command creates another lab. It does not resume an existing lab or renew its expiry.
Each lab uses a separate namespace with the submitted switch names and management addresses.
Live network isolation remains unqualified until the concurrent acceptance tests pass.

The ownership ConfigMap resides in `<name>-system` and uses the lab ID as its name.
Its `data.record` field contains JSON with these values:

- `id`, `environment`, and `allocation_id` identify the lab and its creation request.
- `provenance` records the repository, commit, workflow run, and attempt. `bundle_digest` identifies the complete submitted archive.
- `accepted_at` and `expires_at` record Unix timestamps in seconds. State updates preserve both values.
- `startup_deadline` records the effective startup cutoff. `ready_at` records the first successful readiness observation, when available.
- `runtime` and `registry` record the cEOS image and its registry. `switches` and `link_count` describe the expected infrastructure.
- `state` records `creating`, `running`, `deleting`, or `deleted`. `cleanup` and `overdue` record deletion outcomes when deletion runs.
- `cleanup_started_at` records the first deletion attempt. `cleanup.observed_at` records the latest deletion observation, in Unix seconds.

The allocation ID identifies one creation request. It is not a credential or an authorization policy.
The namespace label `drydock.io/allocation` must match the record before status or deletion can use that namespace.
Automatic cleanup after failed creation also requires the allocation ID from that request.
An ID collision cannot authorize cleanup of the earlier lab.

If ownership remains unconfirmed, cleanup reports failure and preserves the existing resources.
The independent cleaner handles an accepted ownership record that appears after the caller loses its response.

Kubernetes assigns a resource version to each stored object.
Ownership updates require the version that the caller read, so competing updates fail instead of overwriting newer deletion state.
Creation reads the allocation state and expiry before each resource request and before its final state update.
An already submitted request can finish after deletion starts. The cleaner revisits retained deletion records to remove those late resources.

Namespace deletion requires the observed Kubernetes object ID and resource version. A replacement namespace or changed labels prevent that pending deletion.

If creation fails after input admission, the CLI returns a nonzero exit code and one JSON object.
The object includes `lab`, the exception type in `error`, and a separate `cleanup` outcome.
For an ID collision, the cleanup outcome contains:

```json
{
  "deleted": false,
  "error": "Lab creation ownership is unconfirmed. Cleanup refused.",
  "lab": "lab-123456789abc"
}
```

Provider output and startup contents do not appear in this response.
For ownership refusals, identify the request that owns the record before issuing another deletion command.
For incomplete deletion of your own lab, retain its ID.
Retry `lab delete` after resolving the Kubernetes access problem.
Do not remove ownership records or force-remove finalizers to clear a failed result.

## Delete and expire

Request deletion after every allocation attempt:

```sh
.venv/bin/python -m drydock --environment artifacts/lifecycle.yml lab delete "$DRYDOCK_LAB_ID"
```

Repeated deletion is safe.
The command refuses a namespace with different ownership and reports incomplete deletion as failure.
It waits up to 30 minutes for immediate cleanup.
It deletes the lab namespace and its resources without deleting cluster workers or shared infrastructure.
Worker retention and cloud cost remain the operator's responsibility.

Before replacing an earlier deployment, delete its labs with the earlier tool.
Keep the earlier cleaner active until cleanup completes.
Earlier ownership records lack some required fields, including the topology expectations, allocation identity, or startup deadline.
The revised lifecycle does not remove worker pools from earlier deployments.
Deploy the rebuilt cleaner only after those labs are removed.

Lab lifetime defaults to 30 minutes and cannot exceed 60 minutes from acceptance.
Expiry starts cleanup. It does not mean that all lab resources disappear at that instant.
The cleaner retries expired or deleting labs every five minutes indefinitely and revisits deleted records for late resources.
It records overdue cleanup after 30 minutes beyond expiry.
Deletion records the first attempt before it requests namespace removal.
A successful result requires namespace disappearance and stops further allocation through the retained ownership state.
A terminating namespace still reports incomplete cleanup, including when finalizers delay removal.
The cleaner never force-removes finalizers.
If a late namespace appears after successful deletion, a later sweep applies the same ownership guards and removes it.
An overdue result remains visible until deletion succeeds.
`cleanup.observed_at` records an observation, not the exact instant when Kubernetes removed the final resource.
Worker scale-down and zero cloud cost are separate operator outcomes.
Keep the cleaner and ownership records available until cleanup completes.

The [focused live cleanup record](live-cleanup-validation.md) covers real scheduled retries and namespace recovery on local Kubernetes 1.36.4.
It does not qualify clabernetes deletion or cloud worker behavior.

The [standalone lifecycle record](live-lifecycle-validation.md) covers creation, authenticated readiness, inventory, status, and repeated deletion with two real cEOS switches.
It includes independent removal observations and a test that rejects an untrusted Kubernetes CA on the recorded private runtime.

## Offline evidence

Run `make lifecycle-test` with only `requirements.txt` installed.
The tests exercise the CLI with controlled Kubernetes and eAPI responses.
They cover creation, authenticated status, repeated deletion, failed allocation cleanup, and expiry without AVD or ANTA.
Startup tests cover capacity arrival, exhaustion, expiry, late readiness, cancellation, cleanup failure, and preservation of another lab.
Lifetime tests cover the default, both boundaries, invalid values before allocation, and retries through the original expiry.
Inventory tests cover alternate switch names, all-switch authentication, missing links, duplicate Pods, credential rejection, and hostname mismatch.
They also cover endpoint replacement, link loss, and deletion during authentication.
Cleaner tests cover five-minute retries beyond the overdue deadline, interrupted deletion, finalizers, late resources, and preservation of another lab.
Manifest tests cover the mounted Kubernetes identity, finite Job duration, and provider-independent rendering.
Admission cases include different fabrics, custom mappings, unsafe inputs, and a synthetic 100-switch input with split startup data.
They do not establish live startup, provider compatibility, concurrent isolation, cleanup timing, or network acceptance.
