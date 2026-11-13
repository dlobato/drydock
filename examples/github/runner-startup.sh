#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl python3
useradd --create-home --shell /bin/bash drydock-runner
install -d -m 0755 /opt/actions-runner
curl --fail --location --silent --show-error \
  https://github.com/actions/runner/releases/download/v2.338.2/actions-runner-linux-x64-2.338.2.tar.gz \
  -o /tmp/actions-runner.tar.gz
echo 'baebf204307bac6193480852732f0aba2ae97b6c5597c244f4d5558390147c40  /tmp/actions-runner.tar.gz' | sha256sum --check
tar -xzf /tmp/actions-runner.tar.gz -C /opt/actions-runner
rm /tmp/actions-runner.tar.gz
/opt/actions-runner/bin/installdependencies.sh
curl --fail --location --silent --show-error \
  https://dl.k8s.io/release/v1.36.4/bin/linux/amd64/kubectl -o /tmp/kubectl
echo '8b8f088da2dab964f853b38464033b1be15ede2839eca751482357c45abdd05a  /tmp/kubectl' | sha256sum --check
install -m 0755 /tmp/kubectl /usr/local/bin/kubectl
rm /tmp/kubectl
chown -R drydock-runner:drydock-runner /opt/actions-runner
cat > /opt/drydock-launch.py <<'PY'
import json
import os
import subprocess
import sys
from pathlib import Path

payload = sys.stdin.read(1024 * 1024)
if not payload or sys.stdin.read(1):
    raise SystemExit(1)
data = json.loads(payload)
configuration = data["configuration"]
expected = {
    "GITHUB_REPOSITORY": "dlobato/drydock",
    "GITHUB_RUN_ID": str(configuration["run_id"]),
    "GITHUB_RUN_ATTEMPT": str(configuration["run_attempt"]),
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_WORKFLOW_REF": "dlobato/drydock/.github/workflows/pre-deployment.yml@refs/heads/main",
    "GITHUB_WORKFLOW_SHA": configuration["workflow_sha"],
    "GITHUB_JOB": "gke-access",
}
Path("/opt/drydock-expected.json").write_text(json.dumps(expected))
environment = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/home/drydock-runner",
    "USER": "drydock-runner",
    "LANG": "C.UTF-8",
    "ACTIONS_RUNNER_INPUT_JITCONFIG": data["jit"],
    "ACTIONS_RUNNER_HOOK_JOB_STARTED": "/opt/drydock-guard.sh",
}
result = subprocess.run(
    ["/opt/actions-runner/run.sh"],
    cwd="/opt/actions-runner",
    user="drydock-runner",
    group="drydock-runner",
    env=environment,
    start_new_session=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    timeout=600,
)
raise SystemExit(result.returncode)
PY
cat > /opt/drydock-guard.sh <<'SH'
#!/bin/sh
exec /usr/bin/python3 -I /opt/drydock-guard.py
SH
cat > /opt/drydock-guard.py <<'PY'
import json
import os
import signal
from pathlib import Path

try:
    expected = json.loads(Path("/opt/drydock-expected.json").read_text())
    allowed = all(os.environ.get(key) == value for key, value in expected.items())
    allowed = allowed and os.environ.get("GITHUB_EVENT_NAME") in {"workflow_dispatch", "pull_request_target"}
except Exception:
    allowed = False
if not allowed:
    # Stop the whole runner, including steps with an always() condition.
    print("Operator guard refused the unexpected job before workflow steps.", flush=True)
    os.killpg(os.getpgrp(), signal.SIGKILL)
    raise SystemExit(1)
print("Operator guard accepted the exact approved workflow attempt.")
PY
chmod 0755 /opt/drydock-launch.py
chmod 0755 /opt/drydock-guard.sh
chmod 0644 /opt/drydock-guard.py
touch /opt/drydock-ready
