"""Gate mode enforces readiness without changing the consumer's model or observations."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml
from test_action import ROOT, consumer, run


def inputs(repo: Path) -> tuple[Path, Path, Path]:
    settings = repo / "gate files"
    settings.mkdir()
    policy, target, state = settings / "policy.yaml", settings / "target.json", repo / "model" / "verification.json"
    policy.write_bytes((ROOT / "tests" / "policy.yaml").read_bytes())
    target.write_bytes((ROOT / "tests" / "target.json").read_bytes())
    state.write_bytes((ROOT / "tests" / "verification.json").read_bytes())
    return policy, target, state


@pytest.mark.parametrize(
    ("observation", "status", "result"),
    [("passed", 0, "satisfied"), ("failed", 1, "not_satisfied"), ("missing", 1, "unknown"), ("mismatch", 1, "unknown")],
)
def test_gate_reports_and_enforces_the_readiness_result(observation: str, status: int, result: str) -> None:
    with tempfile.TemporaryDirectory() as folder:
        temp = Path(folder)
        repo = consumer(temp)
        policy, target, state = inputs(repo)
        observed = json.loads(state.read_text())
        if observation == "failed":
            observed["records"]["REQ-001"]["assessments"][0].update(state="failed", reason="Invoice assertion failed")
        elif observation == "missing":
            observed["records"] = {}
        elif observation == "mismatch":
            selected = json.loads(target.read_text())
            selected["revision"] = "b" * 40
            target.write_text(json.dumps(selected))
        state.write_text(json.dumps(observed))
        before = {p: p.read_bytes() for p in (policy, target, state)}
        done = run(
            "Evaluate readiness",
            repo,
            temp,
            MODEL="model/*.yaml\nmodel/verification.json",
            POLICY=str(policy),
            TARGET=str(target),
        )
        assert done.returncode == status, done.stdout + done.stderr
        assert f"Result: {result}" in done.stdout
        report = (temp / "exacly-gate.txt").read_text()
        assert report == done.stdout
        summary = (temp / "summary.md").read_text()
        assert summary.startswith("### Exacly readiness gate\n") and report in summary
        assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("invalid", ["policy", "target", "missing_policy_file", "empty_model"])
def test_invalid_gate_input_fails_with_diagnostics_in_the_summary(invalid: str) -> None:
    with tempfile.TemporaryDirectory() as folder:
        temp = Path(folder)
        repo = consumer(temp)
        policy, target, _ = inputs(repo)
        if invalid == "policy":
            policy.write_text("{}")
        elif invalid == "target":
            target.write_text("{}")
        elif invalid == "missing_policy_file":
            policy.unlink()
        else:
            # An empty explicit input must not silently select the CLI's otherwise valid default model.
            shutil.copytree(repo / "model", repo / "spec" / "exacly")
        done = run(
            "Evaluate readiness",
            repo,
            temp,
            MODEL="" if invalid == "empty_model" else "model",
            POLICY=str(policy),
            TARGET=str(target),
        )
        assert done.returncode == 2, done.stdout + done.stderr
        assert "exacly gate:" in done.stdout
        assert "exacly gate:" in (temp / "summary.md").read_text()


@pytest.mark.parametrize(("policy", "target"), [("", "target.json"), ("policy.yaml", ""), ("", "")])
def test_gate_requires_policy_and_target_before_installing(policy: str, target: str) -> None:
    with tempfile.TemporaryDirectory() as folder:
        temp = Path(folder)
        done = subprocess.run(
            ["bash", str(ROOT / "scripts" / "install.sh")],
            cwd=temp,
            env={**os.environ, "MODE": "gate", "ACTION_PATH": str(temp), "POLICY": policy, "TARGET": target},
            capture_output=True,
            text=True,
        )
        assert done.returncode == 2
        assert "gate requires policy and target" in done.stdout


@pytest.mark.parametrize("cases", [["billing::first", "billing::second"], ["billing::*"]])
@pytest.mark.parametrize(
    ("outcomes", "state_result", "exit_code", "gate_result"),
    [
        (("passed", "passed"), "passed", 0, "satisfied"),
        (("passed", "skipped"), "inconclusive", 1, "unknown"),
        (("failed", "skipped"), "failed", 1, "not_satisfied"),
        (("skipped", "skipped"), "not_checked", 1, "unknown"),
    ],
)
def test_refreshed_case_outcomes_reach_the_action_gate(
    cases: list[str], outcomes: tuple[str, str], state_result: str, exit_code: int, gate_result: str
) -> None:
    with tempfile.TemporaryDirectory() as folder:
        temp = Path(folder)
        repo = consumer(temp)
        policy, target, state = inputs(repo)
        billing = repo / "model" / "billing.yaml"
        document = yaml.safe_load(billing.read_text())
        requirement = next(r for r in document["records"] if r["id"] == "REQ-001")
        requirement["observe"]["tests"] = {"cases": cases}
        billing.write_text(yaml.safe_dump(document))
        junit = temp / "junit.xml"
        tags = {"passed": "", "skipped": "<skipped/>", "failed": "<failure/>"}
        junit.write_text(
            '<testsuite><testcase classname="billing" name="first">'
            + tags[outcomes[0]]
            + '</testcase><testcase classname="billing" name="second">'
            + tags[outcomes[1]]
            + "</testcase></testsuite>"
        )
        revision = "a" * 40
        refreshed = subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(ROOT),
                "--no-dev",
                "--no-sync",
                "exacly",
                "refresh",
                "model",
                "--context",
                "ci",
                "--revision",
                revision,
                "--state",
                str(state),
                "--junit",
                str(junit),
            ],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        assert refreshed.returncode == 0, refreshed.stdout + refreshed.stderr
        assessment = json.loads(state.read_text())["records"]["REQ-001"]["assessments"][0]
        assert assessment["state"] == state_result
        if state_result == "inconclusive":
            assert "billing::second" in assessment["reason"]
            assert assessment["evidence"]
        before = state.read_bytes()
        done = run("Evaluate readiness", repo, temp, MODEL="model", POLICY=str(policy), TARGET=str(target))
        assert done.returncode == exit_code, done.stdout + done.stderr
        assert f"Result: {gate_result}" in done.stdout
        assert done.stdout in (temp / "summary.md").read_text()
        assert state.read_bytes() == before
