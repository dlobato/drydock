"""Hosted PR checks and the separate opt-in environment boundary."""

import re
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).resolve().parents[1]


def workflow(name):
    return yaml.load(
        (ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader
    )


class WorkflowTests(unittest.TestCase):
    def test_every_pr_including_forks_runs_hosted_lint_and_tests(self):
        checks = workflow("example-build.yml")
        self.assertEqual(set(checks["on"]), {"pull_request"})
        self.assertEqual(
            checks["on"]["pull_request"],
            {"types": ["opened", "reopened", "synchronize"]},
        )
        self.assertEqual(set(checks["jobs"]), {"lint", "test"})
        self.assertEqual(checks["permissions"], {"contents": "read"})
        for job in checks["jobs"].values():
            # No author, fork, path, branch, or environment gate on hosted checks.
            for field in ("if", "environment", "secrets", "permissions", "needs"):
                self.assertNotIn(field, job)
            self.assertEqual(job["runs-on"], "ubuntu-24.04")
        lint = checks["jobs"]["lint"]["steps"]
        self.assertIn("pre-commit run --all-files", [step.get("run") for step in lint])
        test = checks["jobs"]["test"]["steps"]
        self.assertIn("make test workflow-test", [step.get("run") for step in test])

    def test_only_explicit_requests_reach_gke_approval(self):
        manual = workflow("pre-deployment.yml")
        self.assertEqual(
            set(manual["on"]), {"workflow_dispatch", "pull_request_target"}
        )
        self.assertEqual(
            manual["on"]["pull_request_target"],
            {"types": ["opened", "reopened", "synchronize"], "branches": ["main"]},
        )
        self.assertNotIn("pull_request", manual["on"])
        self.assertEqual(
            set(manual["on"]["workflow_dispatch"]["inputs"]), {"pull_request"}
        )
        self.assertEqual(set(manual["jobs"]), {"select", "gke-access"})
        selection = manual["jobs"]["select"]
        self.assertNotIn("environment", selection)
        self.assertEqual(selection["runs-on"], "ubuntu-24.04")
        access = manual["jobs"]["gke-access"]
        self.assertEqual(access["needs"], "select")
        self.assertEqual(
            access["if"], "${{ needs.select.outputs.requested == 'true' }}"
        )
        self.assertEqual(
            selection["outputs"]["requested"], "${{ steps.select.outputs.requested }}"
        )
        self.assertEqual(access["environment"]["name"], "gke")
        self.assertEqual(
            access["permissions"], {"contents": "read", "id-token": "write"}
        )
        self.assertEqual(
            access["runs-on"], ["self-hosted", "linux", "x64", "drydock-gke"]
        )
        self.assertEqual(len(access["steps"]), 3)
        checkout, authentication, step = access["steps"]
        self.assertEqual(checkout["with"]["ref"], "${{ github.workflow_sha }}")
        self.assertEqual(authentication["with"]["access_token_lifetime"], "900s")
        self.assertEqual(
            {
                scope.strip()
                for scope in authentication["with"]["access_token_scopes"].split(",")
            },
            {
                "https://www.googleapis.com/auth/cloud-platform",
                "https://www.googleapis.com/auth/userinfo.email",
            },
        )
        self.assertEqual(authentication["with"]["create_credentials_file"], "false")
        self.assertEqual(
            authentication["with"]["export_environment_variables"], "false"
        )
        self.assertIn("probe-gke-access.py", step["run"])
        self.assertIn("No lab was created. No network tests ran.", step["run"])
        self.assertNotIn("uses", step)
        self.assertEqual(step["env"]["PR_COMMIT"], "${{ needs.select.outputs.commit }}")
        self.assertIn(
            "${{ needs.select.outputs.commit }}", access["environment"]["url"]
        )

    def test_selection_uses_the_trusted_workflow_revision(self):
        selection = workflow("pre-deployment.yml")["jobs"]["select"]
        trusted = {
            "repository": "dlobato/drydock",
            "ref": "refs/heads/main",
            "workflow_ref": "dlobato/drydock/.github/workflows/"
            "pre-deployment.yml@refs/heads/main",
        }
        expression = "(" + selection["if"].strip()[3:-2].replace("&&", "and") + ")"
        for field in (None, *trusted):
            with self.subTest(untrusted=field):
                values = trusted if field is None else {**trusted, field: "untrusted"}
                self.assertEqual(
                    eval(
                        expression,
                        {"__builtins__": {}, "github": SimpleNamespace(**values)},
                    ),
                    field is None,
                )
        checkout, script = selection["steps"]
        self.assertEqual(checkout["with"]["ref"], "${{ github.workflow_sha }}")
        self.assertEqual(checkout["with"]["path"], "trusted")
        self.assertIn(
            "core.setOutput('requested', Boolean(provenance))", script["with"]["script"]
        )
        self.assertIn(
            "require('./trusted/.github/scripts/select-pr.cjs')",
            script["with"]["script"],
        )
        self.assertEqual(
            selection["outputs"]["commit"], "${{ steps.select.outputs.commit }}"
        )

    def test_no_cloud_permissions_or_actor_allowlist_and_actions_are_pinned(self):
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            definition = workflow(path.name)
            self.assertNotIn("id-token", definition["permissions"])
            self.assertNotIn("github.actor", path.read_text())
            self.assertNotIn("github.triggering_actor", path.read_text())
            for name, job in definition["jobs"].items():
                self.assertNotIn("secrets", job)
                if name == "gke-access":
                    self.assertEqual(job["environment"]["name"], "gke")
                    self.assertEqual(job["permissions"]["id-token"], "write")
                else:
                    self.assertNotIn("id-token", job.get("permissions", {}))
                for step in job["steps"]:
                    if "uses" in step:
                        self.assertRegex(step["uses"], re.compile(r"@[0-9a-f]{40}$"))
                    if step.get("uses", "").startswith("actions/checkout@"):
                        self.assertEqual(step["with"]["persist-credentials"], "false")


if __name__ == "__main__":
    unittest.main()
