"""CLI entry point. Standard output contains one JSON result."""

import argparse
import json
import os
import sys
from pathlib import Path

from .core import Bundle, Environment, UserError
from .flow import cancellation, cleanup, status, wait_ready
from .lifecycle import create_lab, reap, validate_request


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--environment", required=True, type=Path)
    commands = root.add_subparsers(dest="command", required=True)
    lab = commands.add_parser("lab").add_subparsers(dest="action", required=True)
    create = lab.add_parser("create")
    for name in ("status", "wait", "delete"):
        lab.add_parser(name).add_argument("lab")
    create.add_argument("bundle", type=Path)
    create.add_argument("--lifetime", type=int, default=120, help="Minutes, 1 to 240")
    create.add_argument(
        "--startup-timeout",
        type=int,
        default=1200,
        help="Seconds from acceptance, bounded by expiry (default: 1200)",
    )
    for field in ("repository", "commit", "run", "attempt"):
        create.add_argument("--" + field, required=True)
    commands.add_parser("reap")
    return root


def dispatch(args):
    env = Environment.load(args.environment)
    password = os.environ.get("DRYDOCK_LAB_PASSWORD", "")
    if args.command == "reap":
        result = reap(env)
        return {"cleanup": result}, all(
            r.get("deleted", True) and "error" not in r for r in result
        )
    if args.command == "lab" and args.action == "delete":
        with cancellation():
            result = cleanup(env, args.lab)
        return result, result["deleted"]
    if args.command == "lab" and args.action in {"status", "wait"}:
        if not password:
            raise UserError(
                "Set DRYDOCK_LAB_PASSWORD to probe authenticated eAPI readiness."
            )
        with cancellation():
            result = (
                wait_ready(env, args.lab, password)
                if args.action == "wait"
                else status(env, args.lab, password)
            )
        return result, result["ready"]
    bundle = Bundle.load(args.bundle)
    provenance = {
        field: getattr(args, field)
        for field in ("repository", "commit", "run", "attempt")
    }
    validate_request(bundle, provenance, args.lifetime, args.startup_timeout)
    # Standalone create uses the same cleanup guarantees on a failed allocation.
    from uuid import uuid4

    allocation_id = uuid4().hex
    lab = "lab-" + allocation_id[:12]
    with cancellation():
        try:
            result = create_lab(
                env,
                bundle,
                provenance,
                args.lifetime,
                lab,
                allocation_id=allocation_id,
                startup_timeout=args.startup_timeout,
            )
            return result, True
        except (Exception, KeyboardInterrupt) as error:
            result = {
                "lab": lab,
                "error": type(error).__name__,
                "cleanup": cleanup(env, lab, allocation_id=allocation_id),
            }
            return result, False


def main(argv=None):
    args = parser().parse_args(argv)
    os.umask(0o077)
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
