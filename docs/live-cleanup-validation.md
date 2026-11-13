# Live cleanup validation

On November 13, 2026, executable source `3f5588d43445f61b9eec7de3110abd1797045263` passed focused cleanup tests on Kubernetes 1.36.4.
The test used a temporary one-node kind 0.33.0 cluster because no reusable GKE cluster existed and the configured remote context was unreachable.
It provisioned no cloud resources.

The cleaner used the image built for that source, with Python 3.13 and kubectl 1.36.0.
The live Pod's source hashes matched the checkout.
Namespace fixtures contained ConfigMaps and Secrets with synthetic data.
The test exercised cleanup independently of clabernetes, switch startup, and network acceptance.
No product source changes were required.

A finalizer delays deletion until its owner releases it.
A test-owned ConfigMap finalizer held one namespace in deletion across both scheduled sweeps.
Other fixtures represented expired, active, interrupted, and mismatched-ownership records.
The overdue fixtures used past expiry timestamps to exercise that condition without a 30-minute wait.

| Case | Live result |
|---|---|
| Scheduled retries | The native CronJob scheduled Jobs at 09:20:00 and 09:25:00 UTC, exactly 300 seconds apart. |
| Expiry | The observer recorded the expired namespace absent within 133 seconds after its fixture expiry. |
| Interrupted deletion | An abrupt process exit before the namespace deletion request left a durable `deleting` record. The scheduled cleaner recovered it before expiry. |
| Ownership preservation | The active namespace and its Secret retained their identities and data. The cleaner refused the namespace with a different allocation label. |
| Late resources | A matching namespace created after its record reached `deleted` disappeared after the next scheduled sweep. |
| Blocked cleanup | Both sweeps retained the test finalizer and reported incomplete, overdue cleanup. |
| Recovery | The test controller released only its own finalizer. Successful cleanup cleared the overdue flag, and repeated deletion passed. |
| Timestamps | Cleanup retained its first attempt time. Later observations updated without changing acceptance or expiry. |

The scheduled Jobs returned failure while the blocked and mismatched-ownership fixtures remained incomplete.
Those failures were expected test outcomes. They did not prevent cleanup of the other eligible fixtures.
After recovery, all five fixture records reported `deleted`, their overdue flags were false, and their namespaces were absent.

The live cleaner authenticated as its Kubernetes service account through the mounted token file.
Its kubeconfig retained CA verification, and access to an unrelated Secret was denied.
The image contained no Google Cloud CLI, AWS CLI, Ansible, AVD, or ANTA installation.
These observations do not qualify the admission policy planned in task 8.2.

An independent observer retained 57 snapshots and identified both instances of the late namespace.
Baseline Kubernetes namespaces retained their object identities before teardown.
The temporary cluster and kubeconfig were removed. The default Kubernetes and gcloud configuration files remained unchanged.
Private evidence retains Job definitions, outcomes, Pod identities, source hashes, observations, and teardown assertions.

These results cover Kubernetes cleanup fixtures only.
Clabernetes deletion, real switch workloads, GKE, scale, and cloud worker behavior remain outside this test.
The broader live acceptance tasks remain open.
