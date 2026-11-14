"""Operator-only, one-job GCE runner. Credentials arrive through stdin."""

import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def command(args, *, data=None, timeout=60):
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"GH_TOKEN", "GITHUB_TOKEN", "KUBECONFIG"}
    }
    result = subprocess.run(
        args,
        input=data,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=environment,
    )
    if result.returncode:
        raise RuntimeError("The operator command failed: " + args[0])
    return result.stdout


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


class RunnerVM:
    def __init__(self, configuration, directory):
        self.configuration = configuration
        self.directory = Path(directory).resolve()
        root = Path("artifacts/runner-dispatcher").resolve()
        if self.directory.parent != root or not re.fullmatch(
            r"drydock-runner-[0-9]+-[0-9]+-[a-f0-9]{12}", self.directory.name
        ):
            raise ValueError("Invalid operator journal directory.")
        self.name = self.directory.name
        self.project = configuration["project"]
        self.zone = configuration["zone"]
        for value, pattern in [
            (self.project, r"[a-z][a-z0-9-]{4,28}[a-z0-9]"),
            (self.zone, r"[a-z]+-[a-z]+[0-9]-[a-z]"),
            (configuration["subnetwork"], r"[a-z][a-z0-9-]{0,62}"),
            (configuration["image"], r"projects/[a-z0-9-]+/global/images/[a-z0-9-]+"),
        ]:
            if not re.fullmatch(pattern, value):
                raise ValueError("Invalid operator cloud configuration.")
        self.key = self.directory / "ssh-key"
        self.record = self.directory / "vm.json"

    def gcloud(self, *args, **kwargs):
        return command(
            ["gcloud", *args, "--project=" + self.project, "--quiet", "--format=json"],
            **kwargs,
        )

    def instances(self):
        return json.loads(
            self.gcloud(
                "compute",
                "instances",
                "list",
                "--zones=" + self.zone,
                "--filter=name=" + self.name,
            )
        )

    def ssh(self, remote, *, data=None, timeout=30):
        return self.gcloud(
            "compute",
            "ssh",
            "drydock-operator@" + self.name,
            "--zone=" + self.zone,
            "--tunnel-through-iap",
            "--ssh-key-file=" + str(self.key),
            "--ssh-flag=-oStrictHostKeyChecking=accept-new",
            "--ssh-flag=-oUserKnownHostsFile=" + str(self.directory / "known-hosts"),
            "--command=" + remote,
            data=data,
            timeout=timeout,
        )

    def create(self):
        command(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(self.key)])
        public = self.key.with_suffix(".pub").read_text().strip()
        startup = Path(__file__).with_name("runner-startup.sh").resolve()
        self.gcloud(
            "compute",
            "instances",
            "create",
            self.name,
            "--zone=" + self.zone,
            "--machine-type=e2-standard-2",
            "--image=" + self.configuration["image"],
            "--subnet=" + self.configuration["subnetwork"],
            "--no-address",
            "--boot-disk-size=20GB",
            "--boot-disk-type=pd-standard",
            "--boot-disk-auto-delete",
            "--no-service-account",
            "--no-scopes",
            "--max-run-duration=4800s",
            "--instance-termination-action=DELETE",
            "--tags=drydock-dispatcher",
            "--labels=drydock-dispatcher=" + self.name,
            "--metadata=enable-oslogin=FALSE,block-project-ssh-keys=TRUE,ssh-keys=drydock-operator:"
            + public,
            "--metadata-from-file=startup-script=" + str(startup),
            timeout=180,
        )

    def dispose(self):
        deadline = time.monotonic() + 180
        while True:
            pending = json.loads(
                self.gcloud(
                    "compute",
                    "operations",
                    "list",
                    "--filter=status!=DONE AND targetLink:https://www.googleapis.com/compute/v1/projects/"
                    + self.project
                    + "/zones/"
                    + self.zone
                    + "/instances/"
                    + self.name,
                )
            )
            if not pending:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("Runner allocation or deletion is still pending.")
            time.sleep(5)
        instances = self.instances()
        for instance in instances:
            if instance.get("labels", {}).get("drydock-dispatcher") != self.name:
                raise RuntimeError(
                    "Runner ownership differs. The instance was preserved."
                )
            self.gcloud(
                "compute",
                "instances",
                "delete",
                self.name,
                "--zone=" + self.zone,
                timeout=120,
            )
        if self.instances():
            raise RuntimeError("Runner deletion is incomplete.")

    def run(self, registration):
        if self.instances():
            raise RuntimeError("A planned runner already exists. It was preserved.")
        save(
            self.record,
            {
                "configuration": self.configuration,
                "name": self.name,
                "state": "creating",
            },
        )
        try:
            self.create()
            deadline = time.monotonic() + 540
            while True:
                try:
                    self.ssh("test -f /opt/drydock-ready")
                    break
                except (RuntimeError, subprocess.TimeoutExpired):
                    if time.monotonic() >= deadline:
                        raise RuntimeError(
                            "Runner preparation exceeded its deadline."
                        ) from None
                    time.sleep(5)
            self.check_run()
            save(
                self.record,
                {
                    "configuration": self.configuration,
                    "name": self.name,
                    "state": "running",
                },
            )
            self.ssh(
                "sudo python3 -I /opt/drydock-launch.py",
                data=json.dumps(
                    {"jit": registration, "configuration": self.configuration}
                ),
                timeout=4230,
            )
        finally:
            try:
                self.dispose()
                save(
                    self.record,
                    {
                        "configuration": self.configuration,
                        "name": self.name,
                        "state": "deleted",
                    },
                )
            finally:
                for path in [
                    self.key,
                    self.key.with_suffix(".pub"),
                    self.directory / "known-hosts",
                ]:
                    path.unlink(missing_ok=True)

    def check_run(self):
        request = urllib.request.Request(
            "https://api.github.com/repos/dlobato/drydock/actions/runs/"
            + str(self.configuration["run_id"]),
            headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"]},
        )

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *_args, **_kwargs):
                raise RuntimeError("GitHub redirects are refused.")

        with urllib.request.build_opener(NoRedirect).open(
            request, timeout=20
        ) as response:
            run = json.load(response)
        if (
            run["run_attempt"] != self.configuration["run_attempt"]
            or run["status"] == "completed"
        ):
            raise RuntimeError(
                "The approved workflow attempt no longer waits for this runner."
            )


def main():
    def interrupted(_number, _frame):
        raise RuntimeError("The operator interrupted runner execution.")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    data = json.load(sys.stdin)
    runner = RunnerVM(data["configuration"], data["directory"])
    if data.get("recover") is True:
        if (
            runner.record.exists()
            and json.loads(runner.record.read_text())["configuration"]
            != runner.configuration
        ):
            raise RuntimeError(
                "Recovery configuration differs from the original VM journal."
            )
        runner.dispose()
        for path in [
            runner.key,
            runner.key.with_suffix(".pub"),
            runner.directory / "known-hosts",
        ]:
            path.unlink(missing_ok=True)
        save(
            runner.record,
            {
                "configuration": runner.configuration,
                "name": runner.name,
                "state": "deleted",
            },
        )
    else:
        runner.run(data["jit"])
    print(json.dumps({"runner": runner.name, "compute_deleted": True}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit(
            "Disposable runner failed. Inspect the credential-free operator journal."
        ) from None
