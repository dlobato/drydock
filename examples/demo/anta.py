"""AVD catalog generation and required coverage for the six-switch example."""

import json
import os
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import yaml

from drydock.core import UserError, save

ROOT = Path(__file__).resolve().parents[2]
PLAYBOOK = ROOT / "playbooks/anta.yml"
NODES = {"spine1", "spine2", "leaf1", "leaf2", "leaf3", "leaf4"}


def invoke(directory, hosts, structured_dir, dry_run, timeout):
    directory = Path(directory).resolve()
    inventory = {
        "all": {
            "vars": {
                "ansible_connection": "local",
                "ansible_python_interpreter": sys.executable,
            },
            "children": {
                "FABRIC": {
                    "hosts": {
                        host["name"]: {
                            "ansible_host": host["host"],
                            "anta_port": host["port"],
                        }
                        for host in hosts
                    }
                }
            },
        }
    }
    save(directory / "ansible-inventory.json", inventory)
    variables = {
        "root_dir": str(directory),
        "structured_dir": str(structured_dir),
        "anta_runner_dry_run": dry_run,
    }
    save(directory / "variables.json", variables)
    report = directory / "anta/reports/anta_report.json"
    report.unlink(missing_ok=True)
    environment = {
        **os.environ,
        "ANSIBLE_CONFIG": str(ROOT / "ansible.cfg"),
        "ANSIBLE_COLLECTIONS_PATH": str(ROOT / ".collections"),
        "ANSIBLE_LOCAL_TEMP": str(ROOT / ".ansible/tmp"),
        "ANSIBLE_LOG_PATH": "/dev/null",
        "ANSIBLE_NOCOLOR": "1",
    }
    process = subprocess.Popen(
        [
            str(Path(sys.executable).with_name("ansible-playbook")),
            str(PLAYBOOK),
            "-i",
            str(directory / "ansible-inventory.json"),
            "-e",
            "@" + str(directory / "variables.json"),
        ],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        process.wait(timeout=timeout)
    finally:
        if process.poll() is None:
            # Stop Ansible and its worker processes before removing temporary inputs.
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
    rows = json.loads(report.read_text()) if report.exists() else []
    return process.returncode, rows


def coverage(directory, bundle):
    from anta.catalog import AntaCatalog

    expected: Counter[tuple[str, str, str]] = Counter()
    definition = bundle.topology["topology"]
    for name in sorted(NODES):
        node = definition["nodes"][name]
        binds = node.get("binds") or definition["kinds"]["arista_ceos"].get("binds", [])
        mapping = (
            json.loads(bundle.files[binds[0].split(":")[0]])["EthernetIntf"]
            if binds
            else None
        )
        linked = set()
        for link in definition.get("links", []):
            for endpoint in link["endpoints"]:
                switch, port = endpoint.split(":")
                if switch == name:
                    linked.add(
                        mapping[port] if mapping is not None else "Ethernet" + port[3:]
                    )
        catalog = AntaCatalog.parse(
            Path(directory) / "anta/avd_catalogs" / f"{name}.json", file_format="json"
        )
        tests = {item.test.__name__: item for item in catalog.tests}
        required = {
            "VerifyBGPPeerSession",
            "VerifyInterfacesStatus",
            "VerifyLLDPNeighbors",
            "VerifyReachability",
        }
        if name.startswith("leaf"):
            required |= {
                "VerifyMlagStatus",
                "VerifyMlagConfigSanity",
                "VerifyVxlanConfigSanity",
                "VerifyIPv4RoutePresencePerVRF",
                "VerifyPortChannels",
            }
        if not required <= tests.keys():
            raise UserError(f"AVD catalog lacks required coverage for {name}.")
        interfaces = tests["VerifyInterfacesStatus"].inputs.model_dump(mode="json")[
            "interfaces"
        ]
        active = {item["name"] for item in interfaces if item["status"] == "up"}
        if not linked <= active or (name.startswith("leaf") and "Vxlan1" not in active):
            raise UserError(
                f"AVD catalog excludes required switch interfaces for {name}."
            )
        for item in catalog.tests:
            description = (
                item.inputs.result_overwrite.description or item.test.description
            )
            expected[(name, item.test.__name__, description)] += 1
    return expected


def prepare(bundle, source, private, directory):
    from pyavd import get_device_config

    structured = Path(private) / "structured_configs"
    structured.mkdir(mode=0o700)
    for name in sorted(NODES):
        text = (Path(source) / f"{name}.yml").read_text()
        model = yaml.safe_load(text)
        if (
            model.get("hostname") != name
            or not model.get("management_api_http", {}).get("enable_https")
            or get_device_config(model).strip()
            != bundle.files[f"intended/configs/{name}.cfg"].strip()
        ):
            raise UserError(
                "Structured configuration must match the startup configuration and enable HTTPS eAPI."
            )
        (structured / f"{name}.yml").write_text(text)
    hosts = [
        {"name": name, "host": "127.0.0.1", "port": 10000 + index}
        for index, name in enumerate(sorted(NODES))
    ]
    code, rows = invoke(directory, hosts, structured, True, 120)
    if code:
        raise UserError("AVD anta_runner failed to generate the required catalogs.")
    expected = coverage(directory, bundle)
    save(
        Path(directory) / "expected.json",
        [
            {"name": name, "test": test, "description": description, "count": count}
            for (name, test, description), count in sorted(expected.items())
        ],
    )
    return structured, expected


def converge(hosts, structured, directory, expected, timeout, results):
    from .flow import acceptance

    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("ANTA convergence timed out.")
        code, rows = invoke(directory, hosts, structured, False, remaining)
        results[:] = rows
        outcome = acceptance(results, expected)
        if not code and outcome["passed"]:
            return outcome
        time.sleep(min(10, max(0, deadline - time.monotonic())))
