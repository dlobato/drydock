"""Trusted coordinator for disposable build, lifecycle, and ANTA containers."""

import argparse
import json
import logging
import os
import re
import runpy
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from collections import Counter
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

from drydock.core import Bundle, require_digest, save
from drydock.flow import cancellation

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = "examples/evpn-symmetric-irb"


def command(args, *, timeout=300, **kwargs):
    result = subprocess.run(
        args, capture_output=True, text=True, timeout=timeout, **kwargs
    )
    if result.returncode:
        raise RuntimeError("Pipeline command failed: " + Path(args[0]).name)
    return result.stdout


def snapshot(source, target):
    """Copy bounded regular files after the producing container stops."""
    total = 0
    for path in source.rglob("*"):
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode) or path.stat().st_nlink != 1:
            raise ValueError("Pipeline output must contain regular files only.")
        total += path.stat().st_size
        if total > 128 * 1024 * 1024:
            raise ValueError("Pipeline output exceeds 128 MiB.")
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copyfile(path, destination)
        destination.chmod(0o600)


def container(state, stage, mounts, *, credentialed=False, timeout=300):
    name = "drydock-" + uuid4().hex
    args = [
        "docker",
        "run",
        "--name",
        name,
        "--rm",
        "--init",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=512",
        "--cpus=2",
        "--memory=3g",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=1g,mode=1777",
        "--workdir",
        "/trusted",
        "--entrypoint",
        "/opt/venv/bin/python",
        "--env",
        "HOME=/tmp",
        "--env",
        "USER=drydock",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "ANSIBLE_COLLECTIONS_PATH=/opt/collections",
        "--env",
        "ANSIBLE_LOCAL_TEMP=/tmp/ansible",
        "--env",
        "ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote",
        "--env",
        "CLOUDSDK_CONFIG=/tmp/gcloud",
        "--env-file",
        str(state / "lab.env"),
        "--env",
        "DRYDOCK_PIPELINE_FABRIC="
        + json.loads((state / "state.json").read_text()).get("fabric", "example"),
        "--mount",
        f"type=bind,src={ROOT},dst=/trusted,readonly",
    ]
    if stage in {"build", "preflight"}:
        args += ["--network=none"]
    for source, target, readonly in mounts:
        args += [
            "--mount",
            f"type=bind,src={source},dst={target}" + (",readonly" if readonly else ""),
        ]
    if credentialed:
        args += [
            "--mount",
            f"type=bind,src={state / 'google.json'},dst=/credentials/google.json,readonly",
            "--env",
            "CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE=/credentials/google.json",
        ]
    try:
        return command(
            args
            + [
                json.loads((state / "state.json").read_text())["image"],
                "-m",
                "examples.github.pipeline",
                "stage",
                stage,
            ],
            timeout=timeout,
        )
    finally:
        # docker run can lose its client without stopping the container.
        subprocess.run(
            ["docker", "rm", "--force", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )


def prepare(proposed, image, ceos_image, parent, *, fabric="example"):
    if fabric not in {"example", "scale-100"}:
        raise ValueError("Select example or scale-100 as the pipeline fabric.")
    require_digest(image)
    require_digest(ceos_image)
    state = Path(tempfile.mkdtemp(prefix="drydock-pipeline-", dir=parent))
    password = secrets.token_urlsafe(32)
    password_hash = command(
        ["openssl", "passwd", "-6", "-stdin"], input=password
    ).strip()
    (state / "lab.env").write_text(
        f"DRYDOCK_LAB_PASSWORD={password}\nDRYDOCK_LAB_PASSWORD_HASH={password_hash}\n"
        f"DRYDOCK_CEOS_IMAGE={ceos_image}\n"
    )
    save(
        state / "state.json",
        {
            "image": image,
            "ceos_image": ceos_image,
            "fabric": fabric,
            "trusted_commit": os.environ["GITHUB_WORKFLOW_SHA"],
            "provenance": {
                "repository": os.environ["GITHUB_REPOSITORY"],
                "commit": os.environ["PR_COMMIT"],
                "run": os.environ["GITHUB_RUN_ID"],
                "attempt": os.environ["GITHUB_RUN_ATTEMPT"],
            },
        },
    )
    for name in (
        "raw",
        "input",
        "preview",
        "validated",
        "lifecycle",
        "test-output",
        "reports",
    ):
        (state / name).mkdir(mode=0o700)
    with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
        stream.write(f"state={state}\n")
    data = json.loads((state / "state.json").read_text())
    try:
        with cancellation():
            data["stage"] = "build"
            save(state / "state.json", data)
            container(
                state,
                "build",
                [(proposed, "/proposal", True), (state / "raw", "/output", False)],
            )
            snapshot(state / "raw", state / "input")
            data.update(
                stage="preflight",
                bundle_digest=Bundle.load(state / "input/bundle.tar").digest,
            )
            save(state / "state.json", data)
            try:
                container(
                    state,
                    "preflight",
                    [
                        (state / "input", "/input", True),
                        (state / "preview", "/output", False),
                    ],
                )
            finally:
                snapshot(state / "preview", state / "validated")
    except (Exception, KeyboardInterrupt) as error:
        data["prepare_error"] = type(error).__name__
        save(state / "state.json", data)
        raise
    shutil.rmtree(state / "raw")
    shutil.rmtree(state / "preview")
    data["stage"] = "prepared"
    save(state / "state.json", data)
    return state


def execute(state, credentials, cluster, environment):
    if not re.fullmatch(
        r"projects/[a-z][a-z0-9-]+/locations/[a-z0-9-]+/clusters/[a-z][a-z0-9-]+",
        cluster,
    ):
        raise ValueError("Invalid cluster resource.")
    # The official action creates this refreshable external-account configuration.
    if credentials.resolve().is_relative_to(ROOT):
        raise ValueError("Keep federated credentials outside the trusted source mount.")
    credential = json.loads(credentials.read_text())
    if (
        credential.get("type") != "external_account"
        or "service_account_impersonation_url" not in credential
    ):
        raise ValueError("Use the official federated service-account credentials.")
    credential["service_account_impersonation"] = {"token_lifetime_seconds": 900}
    save(state / "google.json", credential)
    data = json.loads((state / "state.json").read_text())
    data.update(cluster=cluster, environment=environment)
    save(state / "state.json", data)
    result = {
        "lab": None,
        "provenance": data["provenance"],
        "tests": {"passed": False},
        "passed": False,
        "bundle_digest": data.get("bundle_digest"),
    }
    lifecycle_mounts = [
        (state / "input", "/input", True),
        (state / "lifecycle", "/output", False),
        (state / "state.json", "/request.json", True),
    ]
    with cancellation():
        try:
            result["stage"] = "create"
            container(state, "create", lifecycle_mounts, credentialed=True, timeout=300)
            result["lab"] = json.loads(
                (state / "lifecycle/allocation.json").read_text()
            )["lab"]
            result["stage"] = "wait"
            container(state, "wait", lifecycle_mounts, credentialed=True, timeout=960)
            ready = json.loads((state / "lifecycle/inventory.json").read_text())
            remaining = min(600, ready["record"]["expires_at"] - time.time() - 30)
            if remaining <= 0:
                raise TimeoutError("No test time remains before expiry.")
            save(state / "test.json", {"timeout": remaining})
            result["stage"] = "test"
            try:
                container(
                    state,
                    "test",
                    [
                        (state / "input", "/input", True),
                        (state / "validated", "/preview", True),
                        (state / "lifecycle/inventory.json", "/inventory.json", True),
                        (state / "test.json", "/test.json", True),
                        (state / "test-output", "/output", False),
                    ],
                    timeout=remaining + 30,
                )
            finally:
                snapshot(state / "test-output", state / "reports")
            result["tests"] = json.loads((state / "reports/tests.json").read_text())
            result["bundle_digest"] = ready["record"]["bundle_digest"]
        except (Exception, KeyboardInterrupt) as error:
            result["error"] = type(error).__name__
            if (state / "reports/tests.json").is_file():
                result["tests"] = json.loads((state / "reports/tests.json").read_text())
        finally:
            handlers = {
                s: signal.signal(s, signal.SIG_IGN)
                for s in (signal.SIGINT, signal.SIGTERM)
            }
            try:
                result["cleanup"] = cleanup(state)
                result["lab"] = result["lab"] or result["cleanup"].get("lab")
            finally:
                for signum, handler in handlers.items():
                    signal.signal(signum, handler)
    result["passed"] = (
        result["tests"].get("passed") is True
        and result["cleanup"].get("deleted") is True
        and "error" not in result
    )
    save(state / "reports/run.json", result)
    return result


def cleanup(state):
    if not (state / "lifecycle/allocation.json").exists():
        result: dict = {"deleted": True, "allocation_attempted": False}
        save(state / "cleanup-result.json", result)
        return result
    try:
        container(
            state,
            "delete",
            [
                (state / "state.json", "/request.json", True),
                (state / "lifecycle", "/output", False),
            ],
            credentialed=True,
            timeout=1860,
        )
        result = json.loads((state / "lifecycle/cleanup.json").read_text())
    except (Exception, KeyboardInterrupt) as error:
        result = {"deleted": False, "error": type(error).__name__}
    save(state / "cleanup-result.json", result)
    return result


def lifecycle(stage):
    from .gke_credentials import configure

    data = json.loads(Path("/request.json").read_text())
    environment = configure(data["cluster"], data["environment"])
    args = [sys.executable, "-m", "drydock", "--environment", str(environment), "lab"]
    if stage == "create":
        args += [
            "create",
            "/input/bundle.tar",
            "--identity-file",
            "/output/allocation.json",
            "--startup-timeout",
            "900",
        ]
        for field, value in data["provenance"].items():
            args += ["--" + field, value]
        destination = "create.json"
    else:
        identity = json.loads(Path("/output/allocation.json").read_text())
        args += [stage, identity["lab"]]
        if stage == "delete":
            args += ["--allocation-id", identity["allocation_id"]]
        destination = "cleanup.json" if stage == "delete" else "inventory.json"
    process = subprocess.run(
        args, capture_output=True, text=True, timeout=1830 if stage == "delete" else 930
    )
    save(Path("/output") / destination, json.loads(process.stdout))
    if process.returncode:
        raise RuntimeError("Lifecycle stage failed: " + stage)


def stage(action):
    from examples.demo import anta
    from examples.demo.flow import acceptance, reports

    if action in {"create", "wait", "delete"}:
        lifecycle(action)
        return
    output = Path("/output")
    if action == "build":
        source = Path("/tmp/source")
        shutil.copytree(
            "/proposal",
            source,
            ignore=shutil.ignore_patterns(
                ".git", ".venv", ".collections", "artifacts", ".ansible", "__pycache__"
            ),
            symlinks=True,
        )
        if os.environ.get("DRYDOCK_PIPELINE_FABRIC") == "scale-100":
            from examples.scale import expand

            expand(source / EXAMPLE)
        env = {**os.environ, "ANSIBLE_CONFIG": str(source / "ansible.cfg")}
        command(
            [
                "ansible-playbook",
                str(source / EXAMPLE / "build.yml"),
                "-i",
                str(source / EXAMPLE / "inventory.yml"),
                "-e",
                "@" + str(source / EXAMPLE / "containerlab.yml"),
                "-e",
                json.dumps({"root_dir": str(output)}),
            ],
            env=env,
            cwd=source,
        )
        build_bundle = runpy.run_path(str(ROOT / EXAMPLE / "bundle.py"))["build_bundle"]
        build_bundle(output, os.environ["DRYDOCK_CEOS_IMAGE"])
        shutil.copytree(source / EXAMPLE, output / "inventory", symlinks=True)
        return
    bundle = Bundle.load(Path("/input/bundle.tar"))
    inventory = Path("/input/inventory/inventory.yml")
    structured = Path("/input/intended/structured_configs")
    if action == "preflight":
        save(
            output / "runtime.json",
            {
                "python": sys.version.split()[0],
                "pyavd": version("pyavd"),
                "anta": version("anta"),
            },
        )
        anta.prepare(
            bundle,
            structured,
            "/tmp",
            output,
            inventory=inventory,
            scale=os.environ.get("DRYDOCK_PIPELINE_FABRIC") == "scale-100",
        )
        return
    expected = Counter(
        {
            (r["name"], r["test"], r["description"]): r["count"]
            for r in json.loads(Path("/preview/expected.json").read_text())
        }
    )
    hosts = json.loads(Path("/inventory.json").read_text())["inventory"]
    rows: list[dict] = []
    try:
        anta.converge(
            hosts,
            structured,
            output,
            expected,
            json.loads(Path("/test.json").read_text())["timeout"],
            rows,
            inventory=inventory,
        )
    finally:
        save(output / "tests.json", acceptance(rows, expected))
        reports(output, rows, expected)


def main():
    os.umask(0o077)
    logging.disable(logging.CRITICAL)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["prepare", "execute", "cleanup", "collect", "stage"]
    )
    parser.add_argument("value", nargs="?")
    args = parser.parse_args()
    try:
        if args.action == "stage":
            stage(args.value)
        elif args.action == "prepare":
            prepare(
                Path(os.environ["PROPOSED_ROOT"]).resolve(),
                os.environ["PIPELINE_IMAGE"],
                os.environ["DRYDOCK_CEOS_IMAGE"],
                Path(os.environ["RUNNER_TEMP"]),
                fabric=os.environ.get("PIPELINE_FABRIC", "example"),
            )
        elif args.action == "collect":
            from .reports import collect

            path = collect(Path(args.value))
            with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
                stream.write(f"path={path}\n")
        elif args.action == "execute":
            result = execute(
                Path(args.value),
                Path(os.environ["GOOGLE_CREDENTIALS"]),
                os.environ["GKE_CLUSTER_RESOURCE"],
                os.environ["DRYDOCK_ENVIRONMENT"],
            )
            print(
                json.dumps(
                    {
                        "lab": result["lab"],
                        "passed": result["passed"],
                        "tests_passed": result["tests"].get("passed", False),
                        "cleanup_deleted": result["cleanup"].get("deleted", False),
                    }
                )
            )
            return 0 if result["passed"] else 1
        else:
            result = cleanup(Path(args.value))
            print(json.dumps(result))
            return 0 if result["deleted"] else 1
    except (Exception, KeyboardInterrupt) as error:
        print(json.dumps({"error": type(error).__name__}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
