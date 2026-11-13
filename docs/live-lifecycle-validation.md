# Standalone lifecycle validation

On November 13, 2026, executable source `ad434368e4693031245f345808487c569605f204` passed the standalone lifecycle commands on local Kubernetes 1.36.4.
The test used a temporary two-node kind 0.33.0 cluster because the configured remote context was unreachable.
It provisioned no cloud resources and required no product source changes.

## Runtime and input

The test used the recorded private clabernetes fork with chart version `0.0.0`.
The cached backend had Docker image ID `sha256:acdea2d4d2591bbc266adfb93dddf7370891e760ca326cc80c41455a237de347`.
Kubernetes reported imported manifest `sha256:bc4642c2b37eda5de59f2ae7acbc4e6685a7abb7cd738599823419f457617a37` for the manager and planner.
The cEOS image used registry digest `sha256:4c69251b4d15c90d0e03f4015ce06eabfcd004b95db68e61a584a35ca7b9b761`.
Both switches reported engineering EOS `4.36.1F-48405728.4361F`.
These identities limit the result to this private runtime.

The input contained two switches, `edge-a` and `edge-b`, with one link and complete synthetic startup files.
It included an interface mapping and an explicit management subnet.
The switches booted with those files without a later configuration deployment.
The test supplied fresh lab credentials at runtime.
It did not use AVD models or introduce host workloads into the lab.

A separate Docker container acted as the external runner, outside the Kubernetes Pod network.
Private routes through the cluster nodes supplied access to the switch Pod addresses.
The caller used Python 3.13.18, PyYAML, and kubectl without AVD, ANTA, Ansible, or cloud tools.
Its executable source hashes matched the checkout.
The independent cleaner was installed before lab creation.

## Command outcomes

The test exercised the [documented commands](lifecycle.md#create-and-inspect) with test-specific paths and request provenance.
Each invocation returned one JSON object and no standard error output.
A Pod UID identifies one Pod instance.

| Command or condition | Exit code | Recorded result |
|---|---|---|
| `lab create` | 0 | Unique ownership, input digest, both switch names, and one link. |
| `lab status` before startup | 1 | The lab was not ready. |
| `lab wait` | 0 | Both switches accepted authentication and reported their expected hostnames. |
| `lab status` after readiness | 0 | Current infrastructure and authenticated management access were ready. |
| `lab inventory` | 0 | Both original names, private Pod addresses, port 443, namespace, Pod names, and Pod UIDs. |
| Status and inventory with a wrong password | 1 | `management_unavailable`, with `ready` set to `false`. |
| Inventory without a password | 1 | The command required `DRYDOCK_LAB_PASSWORD`. |
| `lab delete` | 0 | The lab namespace and its resources disappeared. |
| Repeated `lab delete` | 0 | Deletion succeeded again with the namespace absent. |

The accepted lifetime was 1,800 seconds, with a 1,200-second startup budget.
Readiness, status, inventory, and deletion preserved the original acceptance time and expiry.
Status and inventory retained the same switch Pod identities as the successful wait.
Readiness took 97.9 seconds from acceptance. The deletion command took 47.5 seconds.
These measurements describe one run and do not establish capacity or timing guarantees.

Initial fixtures omitted the management subnet, so the backend rejected their addresses before switch startup.
Cancellation requested deletion, and repeated deletion succeeded for those fixtures.
The corrected input used a new lab identity.

## TLS and removal evidence

The private demo retained its exception for switch certificate verification.
Default certificate verification rejected the switch certificates, while the agreed exception allowed password authentication and EOS hostname comparison.
This result does not establish certificate-based switch identity.

A CA (certificate authority) signs trusted certificates.
Kubernetes retained CA verification through the supplied kubeconfig.
The API readiness request succeeded with its real CA and failed with an unrelated CA.
The test registry also used HTTPS with an explicitly trusted CA for image delivery and controller metadata reads.
No Kubernetes or registry verification bypass was required.

An independent observer retained 30 snapshots of resource metadata.
After deletion, independent API reads found no lab namespaces or lab workloads across the inspected resource types.
The types included clabernetes objects, Pods, Services, startup Secrets, ConfigMaps, Deployments, ReplicaSets, Jobs, and persistent volume claims.
All three ownership records, including the rejected fixtures, retained successful deletion outcomes without overdue flags.
Baseline namespaces and both cluster nodes retained their object identities before infrastructure teardown.

The temporary cluster, registry storage, runner, and test image were removed.
Temporary kubeconfigs, lab credentials, credential-bearing bundles, and the registry private key were removed.
The shared Docker network remained intact. Default Kubernetes and gcloud configuration hashes remained unchanged.
Private evidence retains command JSON, exit codes, source hashes, image identities, metadata observations, and teardown assertions.

This result completes task 7.5 for the tested local runtime.
It does not qualify the official clabernetes release, GKE, AWS, scale, concurrency, or the pipeline authorization policy.
No ANTA or MLAG acceptance ran in this lifecycle test. The earlier six-switch results retain their separate evidence and limits.
