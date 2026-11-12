"""Six-switch ANTA acceptance and reports outside the lifecycle core."""

import signal
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

from drydock.core import UserError, now, save, wait_for
from drydock.flow import available_probe, cancellation, cleanup, diagnostics, eapi
from drydock.lifecycle import create_lab, validate_request

from .anta import converge, prepare


def network_diagnostics(inventory, password):
    results = {}
    for host in inventory:
        commands = [
            "show ip bgp summary",
            "show bgp evpn summary",
            "show interfaces status",
        ]
        if host["name"].startswith("leaf"):
            commands += ["show mlag", "show mlag config-sanity", "show vxlan vni"]
        try:
            results[host["name"]] = dict(
                zip(commands, eapi(host, password, commands), strict=True)
            )
        except Exception:
            results[host["name"]] = {
                "error": "Read-only network diagnostics unavailable."
            }
    return results


def acceptance(results, expected):
    expected = Counter(expected)
    if not expected:
        return {
            "passed": False,
            "required": 0,
            "failures": [{"error": "No required tests."}],
        }
    observed: dict[tuple[str, str, str], list[str]] = {}
    for result in results:
        observed.setdefault(
            (result["name"], result["test"], result.get("description", "")), []
        ).append(result["result"])
    failures = [
        {
            "name": name,
            "test": test,
            "results": observed.get((name, test, description), ["missing"]),
        }
        for name, test, description in sorted(expected)
        if observed.get((name, test, description))
        != ["success"] * expected[(name, test, description)]
    ]
    failures += [
        {"name": r["name"], "test": r["test"], "results": [r["result"]]}
        for r in results
        if (r["name"], r["test"], r.get("description", "")) not in expected
        and r["result"] != "success"
    ]
    return {
        "passed": not failures,
        "required": sum(expected.values()),
        "failures": failures,
    }


def reports(directory, results, expected):
    expected = Counter(expected)
    outcome = acceptance(results, expected)
    save(directory / "anta.json", results)
    suite = ET.Element(
        "testsuite", name="Drydock ANTA", tests=str(sum(expected.values()))
    )
    failures = 0
    for (name, test, description), count in sorted(expected.items()):
        observed = [
            r
            for r in results
            if (r["name"], r["test"], r.get("description", ""))
            == (name, test, description)
        ]
        for index in range(count):
            case = ET.SubElement(
                suite, "testcase", classname=name, name=f"{test}[{index + 1}]"
            )
            result: dict = (
                observed[index]
                if index < len(observed)
                else {"result": "missing", "messages": []}
            )
            if result["result"] != "success" or len(observed) != count:
                failure = ET.SubElement(
                    case,
                    "failure",
                    message=result["result"] if len(observed) <= count else "duplicate",
                )
                failure.text = "\n".join(result.get("messages", []))
                failures += 1
    suite.set("failures", str(failures))
    (directory / "anta.xml").write_bytes(
        ET.tostring(suite, encoding="utf-8", xml_declaration=True)
    )
    return outcome


def test_flow(
    env,
    bundle,
    structured_dir,
    provenance,
    password,
    output,
    lifetime=120,
    ready_timeout=1200,
    test_timeout=600,
):
    validate_request(bundle, provenance, lifetime, ready_timeout)
    if not password:
        raise UserError("Set DRYDOCK_LAB_PASSWORD to the bundle labadmin password.")
    if (
        ready_timeout < 1
        or test_timeout < 1
        or ready_timeout + test_timeout >= lifetime * 60
    ):
        raise UserError(
            "Readiness and test deadlines must fit inside the lab lifetime."
        )
    allocation_id = uuid4().hex
    lab = "lab-" + allocation_id[:12]
    directory = Path(output) / lab
    directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    result = {
        "lab": lab,
        "bundle_digest": bundle.digest,
        "provenance": provenance,
        "reports": str(directory),
        "passed": False,
        "tests": {"passed": False},
        "runtime": {
            "anta": version("anta"),
            "pyavd": version("pyavd"),
            "ceos_image": bundle.topology["topology"]["kinds"]["arista_ceos"]["image"],
        },
    }
    save(directory / "run.json", result)
    rows: list[dict] = []
    # Ownership and this local identity exist even when create does not return.
    with tempfile.TemporaryDirectory() as private, cancellation():
        structured, expected = prepare(bundle, structured_dir, private, directory)
        try:
            record = create_lab(
                env,
                bundle,
                provenance,
                lifetime,
                lab,
                allocation_id=allocation_id,
                startup_timeout=ready_timeout,
            )
            hosts, result["runtime"]["eos"] = wait_for(
                lambda: available_probe(env, lab, password),
                max(0, record["startup_deadline"] - now()),
            )
            save(directory / "inventory.json", {"anta_inventory": {"hosts": hosts}})
            try:
                result["tests"] = converge(
                    hosts, structured, directory, expected, test_timeout, rows
                )
            finally:
                result["tests"] = acceptance(rows, expected)
                save(directory / "network.json", network_diagnostics(hosts, password))
        except (Exception, KeyboardInterrupt) as error:
            result["error"] = type(error).__name__
        finally:
            # Ignore repeated interrupts only while immediate cleanup runs; expiry survives SIGKILL.
            handlers = {
                s: signal.signal(s, signal.SIG_IGN)
                for s in (signal.SIGINT, signal.SIGTERM)
            }
            try:
                for name, action in (
                    ("report_error", lambda: reports(directory, rows, expected)),
                    (
                        "diagnostic_error",
                        lambda: save(
                            directory / "diagnostics.json", diagnostics(env, lab)
                        ),
                    ),
                ):
                    try:
                        action()
                    except Exception as error:
                        result[name] = type(error).__name__
                result["cleanup"] = cleanup(env, lab, allocation_id=allocation_id)
            finally:
                for signum, handler in handlers.items():
                    signal.signal(signum, handler)
    result["passed"] = (
        result["tests"]["passed"]
        and result["cleanup"].get("deleted", False)
        and not any(key.endswith("error") for key in result)
    )
    save(directory / "run.json", result)
    save(
        directory / "events.json",
        [{"event": key, "outcome": result[key]} for key in ("tests", "cleanup")],
    )
    return result
