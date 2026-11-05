"""CLI error handling and the friendly schema-error formatter."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from simanything.cli import app
from simanything.errors import describe_exception, loc_to_path
from simanything.schemas import Mapping
from simanything.spec import Spec

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "tests" / "fixtures" / "eval"


def _runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:  # click >= 8.2 always separates stderr
        return CliRunner()


def _bad_spec(tmp_path: Path) -> Path:
    data = yaml.safe_load((ROOT / "examples" / "toy_6dof_dh.yaml").read_text())
    data["dof"] = "abc"
    data["joints"][2]["efort_limit"] = data["joints"][2].pop("effort_limit")
    data["joints"][1]["dh"]["alfa"] = 3
    data["reach"]["measured_to"] = "flange"
    p = tmp_path / "my_robot.yaml"
    p.write_text(yaml.safe_dump(data, sort_keys=False))
    return p


def test_loc_to_path():
    assert loc_to_path(("joints", 2, "dh", "a")) == "joints[2].dh.a"
    assert loc_to_path(("joints", 0, "link", "geometry", 1, "radius"), Spec) == "joints[0].link.geometry[1].radius"
    assert loc_to_path(("sources", "joints[0].dh"), Spec) == "sources['joints[0].dh']"


def test_describe_validation_error_lists_all_errors_friendly(tmp_path):
    data = yaml.safe_load(_bad_spec(tmp_path).read_text())
    with pytest.raises(ValidationError) as ei:
        Spec.model_validate(data)
    text = describe_exception(ei.value)
    assert text.startswith("invalid spec: 4 schema errors")
    assert "  - dof: Input should be a valid integer" in text and "(got 'abc')" in text
    assert "joints[2].efort_limit: unknown field; did you mean 'effort_limit'" in text
    assert "joints[1].dh.alfa: unknown field; did you mean 'alpha'?" in text
    assert "reach.measured_to:" in text and "(got 'flange')" in text
    assert "pydantic.dev" not in text and "joints.2" not in text and "type=" not in text


def test_describe_mapping_error():
    data = yaml.safe_load((EVAL / "arm_map.yaml").read_text())
    data["candidate"]["jionts"] = data["candidate"].pop("joints")
    with pytest.raises(ValidationError) as ei:
        Mapping.model_validate(data)
    text = describe_exception(ei.value, "mapping")
    assert "candidate.joints: required field is missing" in text
    assert "candidate.jionts: unknown field; did you mean 'joints'?" in text


def test_validate_failed_prefix(tmp_path):
    spec = tmp_path / "s.yaml"
    data = yaml.safe_load((ROOT / "examples" / "toy_2link.yaml").read_text())
    data["estimates"] = []
    spec.write_text(yaml.safe_dump(data))
    res = _runner().invoke(app, ["validate", str(spec)])
    assert res.exit_code == 1
    assert "FAILED:" in res.stdout and "ok:" not in res.stdout
    res = _runner().invoke(app, ["validate", str(ROOT / "examples" / "toy_2link.yaml")])
    assert res.exit_code == 0 and res.stdout.strip().splitlines()[-1].startswith("ok:")


@pytest.mark.parametrize("cmd", ["validate", "build"])
def test_schema_errors_are_friendly(tmp_path, cmd):
    spec = _bad_spec(tmp_path)
    args = [cmd, str(spec)] + (["-o", str(tmp_path / "m.xml")] if cmd == "build" else [])
    res = _runner().invoke(app, args)
    assert res.exit_code == 1
    assert res.exception is None or isinstance(res.exception, SystemExit)
    err = res.stderr
    assert "4 schema errors" in err and "joints[2].efort_limit" in err and "'effort_limit'" in err
    assert "pydantic.dev" not in err and "Traceback" not in err


def test_check_explains_bad_spec_on_stderr(tmp_path):
    spec = _bad_spec(tmp_path)
    res = _runner().invoke(app, ["check", str(ROOT / "tests" / "fixtures" / "report" / "model.xml"),
                                 "--spec", str(spec), "--json"])
    assert res.exit_code == 1
    assert "joints[2].efort_limit: unknown field" in res.stderr


def test_loop_build_error_is_friendly_and_names_the_spec(tmp_path):
    spec = _bad_spec(tmp_path)
    res = _runner().invoke(app, ["loop", str(spec), "--run-dir", str(tmp_path / "run")])
    assert res.exit_code == 1
    assert "joints[2].efort_limit: unknown field; did you mean 'effort_limit'" in res.stdout
    assert f"sim-anything validate {spec}" in res.stdout and "pydantic.dev" not in res.stdout


def test_eval_bad_map_is_a_clean_error(tmp_path):
    bad = tmp_path / "map.yaml"
    bad.write_text("candidate: {jionts: [a], ee: {site: s}}\nreference: {joints: [b], ee: {site: s}}\n")
    args = ["eval", str(EVAL / "arm_cand.xml"), "--reference", str(EVAL / "arm_ref.xml"), "--map", str(bad)]
    res = _runner().invoke(app, args)
    assert res.exit_code == 1 and isinstance(res.exception, SystemExit)
    assert res.stderr.startswith("eval failed:") and "candidate.jionts: unknown field" in res.stderr

    bad.write_text("candidate: {joints: [nope], ee: {site: s}}\nreference: {joints: [b], ee: {site: s}}\n")
    res = _runner().invoke(app, args)
    assert res.exit_code == 1 and isinstance(res.exception, SystemExit)
    assert "eval failed:" in res.stderr and "nope" in res.stderr

    bad.write_text("- just\n- a list\n")
    res = _runner().invoke(app, args)
    assert res.exit_code == 1 and "eval failed:" in res.stderr


def test_render_broken_model_is_a_clean_error(tmp_path):
    model = tmp_path / "broken.xml"
    model.write_text('<mujoco><worldbody><body><geom type="nosuch"/></body></worldbody></mujoco>')
    res = _runner().invoke(app, ["render", str(model), "-o", str(tmp_path / "r")])
    assert res.exit_code == 1 and isinstance(res.exception, SystemExit)
    assert res.stderr.startswith("render failed:") and res.stdout == ""
    assert "does not load" in res.stderr and "Traceback" not in res.stderr
