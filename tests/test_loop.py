"""Tests for simanything.loop with fake build/check/render/report stages."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import simanything.builder
import simanything.check
import simanything.render
import simanything.report
from simanything.loop import LoopOutcome, loop_step
from simanything.schemas import CheckReport, CheckResult, History

SPEC_OK = "name: fake_arm\ndof: 1\njoints: [{name: j1, origin: {}}]\n# ok\n"
SPEC_BAD_REACH = "name: fake_arm\ndof: 1\njoints: [{name: j1, origin: {}}]\n# bad_reach\n"
SPEC_BROKEN = "name: fake_arm\n# broken\n"


@pytest.fixture
def fakes(monkeypatch):
    calls = {"build": 0, "check": 0, "render": 0, "report": 0}

    def build_file(spec_path, out_path):
        calls["build"] += 1
        text = Path(spec_path).read_text()
        if "broken" in text:
            raise ValueError("joints: field required")
        Path(out_path).write_text("<mujoco/>")
        return Path(out_path)

    def run_checks(model_path, spec_path=None, *, seed=0, n_reach_samples=5000):
        calls["check"] += 1
        text = Path(spec_path).read_text()
        checks = [CheckResult(id="compiles", passed=True, message="ok")]
        if "bad_reach" in text:
            checks.append(CheckResult(id="reach", passed=False, severity="error",
                                      message="max reach 0.951 m is 11.9% above rated 0.850 m",
                                      fix_hint="check joints[1].dh.a and reach.measured_to"))
        checks.append(CheckResult(id="joint_limits", passed=False, severity="warning",
                                  message="j1 has no limits", fix_hint="add joints[0].limits"))
        return CheckReport.from_checks(str(model_path), str(spec_path), checks)

    def render_views(model_path, out_dir, *, width=640, height=480, backend="auto"):
        calls["render"] += 1
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        res = {}
        for v in ("front", "side", "top"):
            (out / f"{v}.png").write_bytes(b"png")
            res[v] = out / f"{v}.png"
        res["backend"] = "fake"
        return res

    def write_report(run_dir):
        calls["report"] += 1
        run_dir = Path(run_dir)
        assert (run_dir / "history.json").exists()  # history is written before the report
        (run_dir / "report.html").write_text("<html/>")
        (run_dir / "report.md").write_text("# report")
        return run_dir / "report.html", run_dir / "report.md"

    monkeypatch.setattr(simanything.builder, "build_file", build_file, raising=False)
    monkeypatch.setattr(simanything.check, "run_checks", run_checks, raising=False)
    monkeypatch.setattr(simanything.render, "render_views", render_views, raising=False)
    monkeypatch.setattr(simanything.report, "write_report", write_report, raising=False)
    return calls


def _history(run: Path) -> History:
    return History.model_validate_json((run / "history.json").read_text())


def test_pass_first_iteration(tmp_path, fakes):
    spec = tmp_path / "spec.yaml"
    spec.write_text(SPEC_OK)
    run = tmp_path / "run"
    out = loop_step(spec, run, note="first try")
    assert isinstance(out, LoopOutcome)
    assert (out.iteration, out.status, out.passed, out.exit_code, out.n_errors) == (1, "passed", True, 0, 0)
    assert out.failed_ids == [] and out.fix_hints == []
    assert "PASSED" in out.summary and "joint_limits" in out.summary  # warning listed
    for p in ("spec.yaml", "model.xml", "check.json", "history.json", "report.html", "report.md",
              "renders/front.png", "renders/side.png", "renders/top.png",
              "iterations/iter_01/spec.yaml", "iterations/iter_01/model.xml", "iterations/iter_01/check.json"):
        assert (run / p).exists(), p
    h = _history(run)
    assert h.status == "passed" and h.robot == "fake_arm" and h.max_iter == 8
    assert h.iterations[0].iteration == 1 and h.iterations[0].note == "first try"
    assert json.loads((run / "check.json").read_text())["checks"][0]["pass"] is True
    assert fakes["render"] == 1 and fakes["report"] == 1


def test_fail_then_pass(tmp_path, fakes):
    spec = tmp_path / "spec.yaml"
    spec.write_text(SPEC_BAD_REACH)
    run = tmp_path / "run"
    out = loop_step(spec, run)
    assert (out.iteration, out.status, out.exit_code, out.n_errors) == (1, "running", 1, 1)
    assert out.failed_ids == ["reach"]
    assert out.fix_hints[0].id == "reach" and "joints[1].dh.a" in out.fix_hints[0].fix_hint
    assert "reach" in out.summary and "joints[1].dh.a" in out.summary
    assert not (run / "report.html").exists() and fakes["render"] == 0

    spec.write_text(SPEC_OK)
    out = loop_step(spec, run, note="fixed a2")
    assert (out.iteration, out.status, out.exit_code) == (2, "passed", 0)
    h = _history(run)
    assert [r.passed for r in h.iterations] == [False, True]
    assert h.iterations[0].failed_ids == ["reach"] and h.iterations[1].note == "fixed a2"
    assert (run / "iterations/iter_02/spec.yaml").read_text() == SPEC_OK
    assert (run / "iterations/iter_01/spec.yaml").read_text() == SPEC_BAD_REACH
    assert (run / "spec.yaml").read_text() == SPEC_OK
    assert (run / "report.html").exists()


def test_build_error_is_failed_compiles(tmp_path, fakes):
    spec = tmp_path / "spec.yaml"
    spec.write_text(SPEC_BROKEN)
    run = tmp_path / "run"
    out = loop_step(spec, run)
    assert (out.iteration, out.status, out.exit_code, out.failed_ids) == (1, "running", 1, ["compiles"])
    assert fakes["check"] == 0
    rep = json.loads((run / "check.json").read_text())
    assert rep["passed"] is False and len(rep["checks"]) == 1
    assert rep["checks"][0]["id"] == "compiles" and "joints: field required" in rep["checks"][0]["message"]
    assert rep["checks"][0]["fix_hint"]
    assert not (run / "iterations/iter_01/model.xml").exists() and not (run / "model.xml").exists()
    assert (run / "iterations/iter_01/check.json").exists()
    assert "joints: field required" in _history(run).iterations[0].build_error


def test_max_iter(tmp_path, fakes):
    spec = tmp_path / "spec.yaml"
    run = tmp_path / "run"
    for i in range(3):
        spec.write_text(SPEC_BAD_REACH + f"# v{i}\n")
        out = loop_step(spec, run, max_iter=3)
    assert (out.iteration, out.status, out.passed, out.exit_code) == (3, "max_iter_reached", False, 2)
    assert (run / "report.html").exists() and (run / "renders/front.png").exists()
    assert fakes["build"] == 3

    # a changed spec after the cap starts no new iteration
    spec.write_text(SPEC_OK)
    out = loop_step(spec, run, max_iter=3)
    assert (out.iteration, out.exit_code) == (3, 2)
    assert fakes["build"] == 3 and not (run / "iterations/iter_04").exists()
    assert "NOT" in out.summary

    # raising the cap continues numbering
    out = loop_step(spec, run, max_iter=5)
    assert (out.iteration, out.status, out.exit_code) == (4, "passed", 0)
    assert _history(run).max_iter == 5


def test_unchanged_spec_starts_no_new_iteration(tmp_path, fakes):
    spec = tmp_path / "spec.yaml"
    spec.write_text(SPEC_OK)
    run = tmp_path / "run"
    loop_step(spec, run)
    out = loop_step(spec, run)
    assert (out.iteration, out.status, out.exit_code) == (1, "passed", 0)
    assert "unchanged" in out.summary
    assert fakes["build"] == 1 and fakes["render"] == 1 and fakes["report"] == 1
    assert len(_history(run).iterations) == 1

    # a failing spec rerun unchanged also keeps its iteration and fix hints
    run2 = tmp_path / "run2"
    spec.write_text(SPEC_BAD_REACH)
    loop_step(spec, run2)
    out = loop_step(spec, run2)
    assert (out.iteration, out.exit_code, out.failed_ids) == (1, 1, ["reach"])
    assert out.fix_hints and len(_history(run2).iterations) == 1


def test_spec_inside_run_dir(tmp_path, fakes):
    run = tmp_path / "run"
    run.mkdir()
    spec = run / "spec.yaml"
    spec.write_text(SPEC_OK)
    out = loop_step(spec, run)
    assert out.exit_code == 0 and spec.read_text() == SPEC_OK


def test_cli_loop_json(tmp_path, fakes):
    from typer.testing import CliRunner

    from simanything.cli import app

    spec = tmp_path / "spec.yaml"
    spec.write_text(SPEC_BAD_REACH)
    res = CliRunner().invoke(app, ["loop", str(spec), "--run-dir", str(tmp_path / "run"), "--json"])
    assert res.exit_code == 1
    data = json.loads(res.output)
    assert set(data) == {"iteration", "status", "passed", "exit_code", "n_errors", "failed_ids", "run_dir",
                         "summary", "fix_hints"}
    assert data["fix_hints"] == [{"id": "reach", "fix_hint": "check joints[1].dh.a and reach.measured_to"}]
