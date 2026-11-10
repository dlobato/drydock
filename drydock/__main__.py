"""CLI entry point. Standard output contains one JSON result."""

import argparse
from dataclasses import asdict
import json
import logging
import os
from pathlib import Path
import sys

from .cloud import create_lab, deploy_infrastructure, destroy_infrastructure, reap, validate_request
from .core import Bundle, Environment, UserError
from .flow import cancellation, cleanup, status, test_flow


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--environment", required=True, type=Path)
    commands = root.add_subparsers(dest="command", required=True)
    infra = commands.add_parser("infra").add_subparsers(dest="action", required=True)
    infra.add_parser("deploy")
    infra.add_parser("destroy")
    lab = commands.add_parser("lab").add_subparsers(dest="action", required=True)
    create = lab.add_parser("create")
    for name in ("status", "delete"):
        lab.add_parser(name).add_argument("lab")
    test = commands.add_parser("test")
    test.add_argument("--output", type=Path, default=Path("reports"))
    test.add_argument("--ready-timeout", type=int, default=1200, help="Seconds, including authenticated eAPI readiness")
    test.add_argument("--test-timeout", type=int, default=600, help="Seconds for ANTA convergence")
    for command in (create, test):
        command.add_argument("bundle", type=Path)
        command.add_argument("--lifetime", type=int, default=120, help="Minutes, 1 to 240")
        for field in ("repository", "commit", "run", "attempt"):
            command.add_argument("--" + field, required=True)
    commands.add_parser("reap")
    return root


def dispatch(args):
    env = Environment.load(args.environment)
    password = os.environ.get("DRYDOCK_LAB_PASSWORD", "")
    if args.command == "infra":
        if args.action == "deploy":
            return deploy_infrastructure(env), True
        result = destroy_infrastructure(env)
        return result, result["deleted"]
    if args.command == "reap":
        result = reap(env)
        return {"cleanup": result}, all(r.get("deleted", True) and "error" not in r for r in result)
    if args.command == "lab" and args.action == "delete":
        with cancellation():
            result = cleanup(env, args.lab)
        return result, result["deleted"]
    if args.command == "lab" and args.action == "status":
        if not password:
            raise UserError("Set DRYDOCK_LAB_PASSWORD to probe authenticated eAPI readiness.")
        result = status(env, args.lab, password)
        return result, result["ready"]
    # A local journal prevents starting work against a partly installed environment.
    journal = json.loads((env.directory / "ownership.json").read_text())
    if journal["environment"] != asdict(env) or journal["state"] != "ready":
        raise UserError("Deploy the matching environment before requesting a lab.")
    bundle = Bundle.load(args.bundle)
    provenance = {field: getattr(args, field) for field in ("repository", "commit", "run", "attempt")}
    validate_request(bundle, provenance, args.lifetime)
    if args.command == "test":
        result = test_flow(env, bundle, provenance, password, args.output, args.lifetime, args.ready_timeout, args.test_timeout)
        return result, result["passed"]
    # Standalone create uses the same cleanup guarantees on a failed allocation.
    from uuid import uuid4
    lab = "lab-" + uuid4().hex[:12]
    with cancellation():
        try:
            result = create_lab(env, bundle, provenance, args.lifetime, lab)
            return result, True
        except (Exception, KeyboardInterrupt) as error:
            result = {"lab": lab, "error": type(error).__name__, "cleanup": cleanup(env, lab)}
            return result, False


def main(argv=None):
    args = parser().parse_args(argv)
    os.umask(0o077)
    # ANTA can log device exceptions. Retain only the explicit safe reports.
    logging.disable(logging.CRITICAL)
    try:
        result, success = dispatch(args)
    except UserError as error:
        result, success = {"error": str(error)}, False
    except (Exception, KeyboardInterrupt) as error:
        result, success = {"error": type(error).__name__}, False
    print(json.dumps(result, sort_keys=True))
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
