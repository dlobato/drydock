"""Optional demo commands. Run from the repository root."""

import argparse
import json
import logging
import os
from pathlib import Path
import sys

from drydock.core import Bundle, Environment, UserError


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--environment", required=True, type=Path)
    commands = root.add_subparsers(dest="command", required=True)
    infra = commands.add_parser("infra").add_subparsers(dest="action", required=True)
    infra.add_parser("deploy")
    infra.add_parser("destroy")
    test = commands.add_parser("test")
    test.add_argument("bundle", type=Path)
    test.add_argument("--structured-configs", required=True, type=Path)
    test.add_argument("--output", type=Path, default=Path("reports"))
    test.add_argument("--ready-timeout", type=int, default=1200, help="Seconds, including authenticated eAPI readiness")
    test.add_argument("--test-timeout", type=int, default=600, help="Seconds for ANTA convergence")
    test.add_argument("--lifetime", type=int, default=120, help="Minutes, 1 to 240")
    for field in ("repository", "commit", "run", "attempt"):
        test.add_argument("--" + field, required=True)
    return root


def dispatch(args):
    if args.command == "infra":
        from .gke import GKEEnvironment, deploy_infrastructure, destroy_infrastructure

        env = GKEEnvironment.load(args.environment)
        if args.action == "deploy":
            return deploy_infrastructure(env), True
        result = destroy_infrastructure(env)
        return result, result["deleted"]
    from .flow import test_flow

    env = Environment.load(args.environment)
    bundle = Bundle.load(args.bundle)
    provenance = {field: getattr(args, field) for field in ("repository", "commit", "run", "attempt")}
    result = test_flow(env, bundle, args.structured_configs, provenance, os.environ.get("DRYDOCK_LAB_PASSWORD", ""),
                       args.output, args.lifetime, args.ready_timeout, args.test_timeout)
    return result, result["passed"]


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
