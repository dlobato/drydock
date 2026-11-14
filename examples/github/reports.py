"""Publish an explicit, credential-free view of private pipeline output."""

import hashlib
import ipaddress
import json
import re
import shutil
import stat
import tempfile
from collections import Counter
from pathlib import Path

from drydock.core import save
from examples.demo.anta import NODES
from examples.demo.flow import reports

TESTS = {
    "VerifyBGPPeerSession",
    "VerifyInterfacesStatus",
    "VerifyLLDPNeighbors",
    "VerifyReachability",
    "VerifyMlagStatus",
    "VerifyMlagConfigSanity",
    "VerifyVxlanConfigSanity",
    "VerifyIPv4RoutePresencePerVRF",
    "VerifyPortChannels",
}
STATUSES = {"success", "failure", "error", "skipped", "unset", "missing"}
CATALOG_KEYS = {
    "anta.tests.connectivity",
    "anta.tests.interfaces",
    "anta.tests.mlag",
    "anta.tests.routing.bgp",
    "anta.tests.routing.generic",
    "anta.tests.vxlan",
    *TESTS,
    "neighbors",
    "port",
    "neighbor_device",
    "neighbor_port",
    "require_fqdn",
    "hosts",
    "destination",
    "source",
    "vrf",
    "repeat",
    "interfaces",
    "name",
    "status",
    "ignored_interfaces",
    "bgp_peers",
    "peer_address",
    "route_entries",
    "prefix",
}


def read(path, default=None):
    if not path.exists() and not path.is_symlink():
        return default
    if (
        path.resolve() != path.absolute()
        or not stat.S_ISREG(path.lstat().st_mode)
        or path.stat().st_nlink != 1
        or path.stat().st_size > 4 * 1024 * 1024
    ):
        raise ValueError("Report input must be a bounded regular file.")
    return json.loads(path.read_text())


def catalog(value):
    """Keep network parameters, excluding source descriptions and custom data."""
    if isinstance(value, dict):
        return {k: catalog(v) for k, v in value.items() if k in CATALOG_KEYS}
    if isinstance(value, list):
        return [catalog(v) for v in value]
    if isinstance(value, str):
        if value in NODES | {"default", "VRF_A", "VRF_B", "up", "down"} or re.fullmatch(
            r"(?:Ethernet|Loopback|Port-Channel|Vlan|Vxlan)[0-9]+(?:/[0-9]+)*", value
        ):
            return value
        try:
            ipaddress.ip_interface(value)
            return value
        except ValueError:
            return "[redacted]"
    return value


def collect(state):
    destination = state / "public"
    # Never leave a previously collected directory eligible after a failed retry.
    shutil.rmtree(destination, ignore_errors=True)
    with tempfile.TemporaryDirectory(prefix="safe-reports-", dir=state) as temporary:
        output = Path(temporary)
        data = read(state / "state.json")
        run = read(state / "reports/run.json", {})
        ready = read(state / "lifecycle/inventory.json", {})
        identity = read(state / "lifecycle/allocation.json", {})
        cleanup = read(state / "cleanup-result.json", {})
        rows = read(state / "reports/anta.json")
        if rows is None:
            rows = read(state / "reports/anta/reports/anta_report.json", [])
        expected = read(state / "validated/expected.json", [])
        counts: Counter = Counter()
        safe_rows = []
        for row in expected:
            if row["name"] not in NODES or row["test"] not in TESTS:
                raise ValueError("Unknown example catalog identity.")
            if type(row["count"]) is not int or not 1 <= row["count"] <= 1000:
                raise ValueError("Invalid required test count.")
            description = hashlib.sha256(row["description"].encode()).hexdigest()
            counts[(row["name"], row["test"], description)] += row["count"]
        for row in rows:
            if (
                row["name"] not in NODES
                or row["test"] not in TESTS
                or row["result"] not in STATUSES
            ):
                raise ValueError("Unknown ANTA result identity or status.")
            safe_rows.append(
                {
                    **{k: row[k] for k in ("name", "test", "result")},
                    "description": hashlib.sha256(
                        row.get("description", "").encode()
                    ).hexdigest(),
                }
            )
        # Acceptance still uses the private descriptions and detects each missing result.
        outcome = reports(output, safe_rows, counts)
        tests = read(state / "reports/tests.json", {"passed": False})
        outcome["passed"] = outcome["passed"] and tests.get("passed") is True
        runtime = read(state / "validated/runtime.json", {})
        versions = {k: runtime[k] for k in ("python", "pyavd", "anta") if k in runtime}
        eos = {k: v for k, v in ready.get("eos_versions", {}).items() if k in NODES}
        for value in [*versions.values(), *eos.values()]:
            if not isinstance(value, str) or not re.fullmatch(
                r"[0-9][A-Za-z0-9.()+_ -]{0,99}", value
            ):
                raise ValueError("Invalid runtime version.")
        summary = {
            "provenance": data["provenance"],
            "trusted_commit": data["trusted_commit"],
            "bundle_digest": data.get("bundle_digest"),
            "lab": identity.get("lab"),
            "runtime": {
                **versions,
                "pipeline_image": data["image"],
                "ceos_image": data["ceos_image"],
                "eos": eos,
            },
            "tests": outcome,
            "cleanup": {
                k: cleanup[k] is True
                for k in ("deleted", "allocation_attempted")
                if k in cleanup
            },
            "passed": run.get("passed") is True
            and outcome["passed"]
            and cleanup.get("deleted") is True,
            "stage": run.get("stage", data.get("stage")),
        }
        if "error" in cleanup:
            summary["cleanup"]["error"] = "CleanupFailed"
        for key in ("error", "prepare_error"):
            if key in run or key in data:
                summary[key] = run.get(key, data.get(key))
        save(output / "run.json", summary)
        save(
            output / "diagnostics.json",
            {
                "stage": summary["stage"],
                "ready": ready.get("ready") is True,
                "observed_at": ready.get("observed_at"),
                "accepted_at": ready.get("record", {}).get("accepted_at"),
                "expires_at": ready.get("record", {}).get("expires_at"),
                "initial_cleanup_deleted": run.get("cleanup", {}).get("deleted")
                is True,
                "cleanup_deleted": cleanup.get("deleted") is True,
            },
        )
        for name in sorted(NODES):
            source = state / f"validated/anta/avd_catalogs/{name}.json"
            value = read(source)
            if value is not None:
                save(output / f"catalogs/{name}.json", catalog(value))
        manifest = {
            str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(output.rglob("*"))
            if path.is_file()
        }
        # Inspect the actual bytes that the artifact action will upload.
        secrets = [
            line.split("=", 1)[1]
            for line in (state / "lab.env").read_text().splitlines()
            if line.startswith(("DRYDOCK_LAB_PASSWORD=", "DRYDOCK_LAB_PASSWORD_HASH="))
        ]
        for path in output.rglob("*"):
            if path.is_file():
                text = path.read_text()
                if any(secret and secret in text for secret in secrets) or re.search(
                    r"(?i)(-----BEGIN .*PRIVATE KEY|\$6\$|authorization|credential_source|client_secret|access_token|username .*secret|management api http-commands)",
                    text,
                ):
                    raise ValueError("Sensitive data in collected reports.")
        save(output / "manifest.json", manifest)
        output.rename(destination)
    return destination
