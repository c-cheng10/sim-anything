"""Tests for simanything.check (component B).

Hand-written MJCF fixtures paired with small hand-written specs: one good model that
passes everything and deliberately broken variants that trip one specific check.
These tests do not depend on simanything.builder.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pytest
import yaml

from simanything.check import CHECK_IDS, inertia_problems, run_checks
from simanything.spec import load_spec

CONTRACT_IDS = ["compiles", "joint_structure", "ee_site", "kinematics_match", "joint_limits", "reach", "total_mass",
                "mass_plausibility", "inertia_valid", "self_collision_home", "collision_exclusions", "stable_hold", "actuators",
                "sources_complete"]
WARNING_CHECKS = {"mass_plausibility", "collision_exclusions"}
SPEC_CHECKS = {"joint_structure", "ee_site", "kinematics_match", "joint_limits", "reach", "total_mass", "actuators",
               "sources_complete"}

R150 = 2.6179939  # 150 deg in rad

SPEC = {
    "name": "test_2link",
    "dof": 2,
    "units": {"length": "m", "angle": "deg"},
    "convention": "offset",
    "base": {"link": {"mass": 1.0,
                      "geometry": [{"shape": "cylinder", "radius": 0.06, "half_length": 0.03, "pos": [0, 0, 0.03]}]}},
    "joints": [
        {"name": "shoulder", "type": "hinge", "origin": {"xyz": [0, 0, 0.1]}, "axis": [0, 1, 0],
         "limits": {"lower": -150, "upper": 150}, "effort_limit": 20,
         "link": {"mass": 1.0, "geometry": [{"shape": "capsule", "radius": 0.03}]}},
        {"name": "elbow", "type": "hinge", "origin": {"xyz": [0.3, 0, 0]}, "axis": [0, 1, 0],
         "limits": {"lower": -150, "upper": 150}, "effort_limit": 10,
         "link": {"mass": 0.5, "geometry": [{"shape": "capsule", "radius": 0.025}]}},
    ],
    "ee": {"name": "ee_site", "origin": {"xyz": [0.25, 0, 0]}},
    "total_mass": 2.5,
    "reach": {"value": 0.55, "measured_from": "shoulder", "measured_to": "ee_site"},
    "sources": {"total_mass": "https://example.com/datasheet.pdf"},
    "estimates": ["base", "joints", "ee", "reach"],
}

ACT = {
    "shoulder": '<position name="shoulder_act" joint="shoulder" kp="500" kv="15" forcerange="-20 20"/>',
    "elbow": '<position name="elbow_act" joint="elbow" kp="200" kv="5" forcerange="-10 10"/>',
}


def mjcf(*, elbow_joint: str | None = None, elbow_range: str = f"-{R150} {R150}",
         acts: dict[str, str] | None = None, site: str = '<site name="ee_site" pos="0.25 0 0"/>',
         key: str | None = "0 0", elbow_extra: str = "", elbow_inertial: str | None = None,
         base_mass: float = 1.0) -> str:
    if elbow_joint is None:
        elbow_joint = f'<joint name="elbow" type="hinge" axis="0 1 0" range="{elbow_range}" damping="0.5"/>'
    acts = ACT if acts is None else acts
    elbow_inertial = elbow_inertial or '<inertial pos="0.125 0 0" mass="0.5" diaginertia="0.0002 0.003 0.003"/>'
    keyframe = f'<keyframe><key name="home" qpos="{key}"/></keyframe>' if key is not None else ""
    return f"""<mujoco model="test_2link">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="0.002" integrator="implicitfast"/>
  <worldbody>
    <body name="base" pos="0 0 0">
      <inertial pos="0 0 0.03" mass="{base_mass}" diaginertia="0.002 0.002 0.002"/>
      <geom name="base_geom" type="cylinder" size="0.06 0.03" pos="0 0 0.03"/>
      <body name="shoulder_link" pos="0 0 0.1">
        <joint name="shoulder" type="hinge" axis="0 1 0" range="-{R150} {R150}" damping="0.5"/>
        <inertial pos="0.15 0 0" mass="1.0" diaginertia="0.0005 0.008 0.008"/>
        <geom name="shoulder_geom" type="capsule" fromto="0 0 0 0.3 0 0" size="0.03"/>
        <body name="elbow_link" pos="0.3 0 0">
          {elbow_joint}
          {elbow_inertial}
          <geom name="elbow_geom" type="capsule" fromto="0 0 0 0.25 0 0" size="0.025"/>
          {site}
          {elbow_extra}
        </body>
      </body>
    </body>
  </worldbody>
  <actuator>
    {"".join(acts.values())}
  </actuator>
  {keyframe}
</mujoco>
"""


def write_case(tmp_path: Path, xml: str, spec: dict | None = None, *, spec_text: str | None = None
               ) -> tuple[Path, Path | None]:
    model = tmp_path / "model.xml"
    model.write_text(xml)
    if spec is None and spec_text is None:
        return model, None
    sp = tmp_path / "spec.yaml"
    sp.write_text(spec_text if spec_text is not None else yaml.safe_dump(spec, sort_keys=False))
    return model, sp


def spec_with(**changes) -> dict:
    s = json.loads(json.dumps(SPEC))
    for k, v in changes.items():
        s[k] = v
    return s


def by_id(report):
    return {c.id: c for c in report.checks}


def error_failures(report) -> set[str]:
    return {c.id for c in report.checks if not c.passed and c.severity == "error"}


def assert_fails(report, cid: str):
    c = by_id(report)[cid]
    assert c.passed is False, c
    assert c.severity == "error"
    assert c.fix_hint and c.fix_hint.strip()
    assert report.passed is False
    return c


# --------------------------------------------------------------------------- #
# Good model
# --------------------------------------------------------------------------- #


def test_good_model_passes_everything(tmp_path):
    model, spec = write_case(tmp_path, mjcf(), SPEC)
    t0 = time.perf_counter()
    report = run_checks(model, spec)
    elapsed = time.perf_counter() - t0
    assert [c.id for c in report.checks] == CONTRACT_IDS == CHECK_IDS
    failed = [(c.id, c.message) for c in report.checks if not c.passed]
    assert failed == []
    assert report.passed and report.n_checks == len(CONTRACT_IDS) and report.n_failed == 0 and report.n_errors == 0
    reach = by_id(report)["reach"]
    assert reach.measured == pytest.approx(0.55, rel=1e-3)
    assert reach.expected == pytest.approx(0.55)
    assert reach.tolerance == 0.05
    assert reach.details["samples"] == 5000
    assert by_id(report)["total_mass"].measured == pytest.approx(2.5)
    assert elapsed < 5.0


def test_report_json_keys(tmp_path):
    model, spec = write_case(tmp_path, mjcf(), spec_with(total_mass=4.0))
    d = run_checks(model, spec).to_json_dict()
    json.dumps(d)  # serialisable
    assert set(d) >= {"model", "spec", "passed", "n_checks", "n_failed", "n_errors", "mujoco_version", "checks"}
    assert d["n_checks"] == len(CONTRACT_IDS) and d["passed"] is False and d["n_errors"] >= 1
    for c in d["checks"]:
        assert set(c) >= {"id", "pass", "measured", "expected", "tolerance", "severity", "message", "fix_hint",
                          "details"}
        assert "passed" not in c
        if not c["pass"]:
            assert c["fix_hint"]


def test_no_spec_skips_spec_checks(tmp_path):
    model, _ = write_case(tmp_path, mjcf())
    report = run_checks(model)
    assert report.passed and report.spec is None
    for c in report.checks:
        if c.id in SPEC_CHECKS:
            assert c.passed and c.severity == "info" and c.message == "skipped: no spec"
        else:
            assert c.passed and c.severity == ("warning" if c.id in WARNING_CHECKS else "error"), c


def test_reach_metric_definitions(tmp_path):
    model, spec = write_case(tmp_path, mjcf(), spec_with(reach={"value": 0.65, "measured_from": "base_origin"}))
    r = by_id(run_checks(model, spec))["reach"]
    assert r.passed and r.measured == pytest.approx(0.65, rel=1e-3)
    model, spec = write_case(tmp_path, mjcf(), spec_with(reach={"value": 0.55,
                                                                "measured_from": "base_axis_horizontal"}))
    r = by_id(run_checks(model, spec))["reach"]
    assert r.passed and r.measured == pytest.approx(0.55, rel=1e-3)


# --------------------------------------------------------------------------- #
# Broken models / specs
# --------------------------------------------------------------------------- #


def test_non_compiling_xml(tmp_path):
    model, spec = write_case(tmp_path, mjcf().replace("</worldbody>", ""), SPEC)
    report = run_checks(model, spec)
    c = assert_fails(report, "compiles")
    assert c.message
    assert [x.id for x in report.checks] == CONTRACT_IDS
    assert error_failures(report) == {"compiles"}
    assert by_id(report)["sources_complete"].passed  # spec-only check still runs
    for x in report.checks:
        if not x.passed:
            assert x.fix_hint


def test_mujoco_compile_error_message(tmp_path):
    bad = mjcf(elbow_inertial='<inertial pos="0 0 0" mass="-1" diaginertia="0.1 0.1 0.1"/>')
    model, spec = write_case(tmp_path, bad, SPEC)
    c = assert_fails(run_checks(model, spec), "compiles")
    assert "mass" in c.message.lower() and "joints[*].link.mass" in c.fix_hint


def test_missing_joint(tmp_path):
    xml = mjcf(elbow_joint="", acts={"shoulder": ACT["shoulder"]}, key="0")
    model, spec = write_case(tmp_path, xml, SPEC)
    report = run_checks(model, spec)
    c = assert_fails(report, "joint_structure")
    assert "elbow" in c.message
    assert error_failures(report) == {"joint_structure"}


def test_extra_joint(tmp_path):
    extra = ('<body name="wrist_link" pos="0.25 0 0"><joint name="wrist" type="hinge" axis="0 1 0" range="-1 1"/>'
             '<inertial pos="0 0 0" mass="0.01" diaginertia="1e-5 1e-5 1e-5"/></body>')
    acts = dict(ACT, wrist='<position name="wrist_act" joint="wrist" kp="10" kv="0.5"/>')
    model, spec = write_case(tmp_path, mjcf(elbow_extra=extra, acts=acts, key="0 0 0"),
                             spec_with(total_mass=2.51))
    report = run_checks(model, spec)
    c = assert_fails(report, "joint_structure")
    assert "wrist" in c.message
    assert error_failures(report) == {"joint_structure"}


def test_free_joint_is_unexpected(tmp_path):
    xml = mjcf(key=None).replace('<body name="base" pos="0 0 0">',
                                 '<body name="base" pos="0 0 0"><freejoint name="float"/>')
    model, spec = write_case(tmp_path, xml, SPEC)
    c = assert_fails(run_checks(model, spec), "joint_structure")
    assert "free" in c.fix_hint


def test_renamed_joint(tmp_path):
    xml = mjcf(elbow_joint=f'<joint name="elbow_joint" type="hinge" axis="0 1 0" range="-{R150} {R150}"/>',
               acts={"shoulder": ACT["shoulder"],
                     "elbow": '<position name="elbow_act" joint="elbow_joint" kp="200" kv="5"/>'})
    model, spec = write_case(tmp_path, xml, SPEC)
    report = run_checks(model, spec)
    c = assert_fails(report, "joint_structure")
    assert "renamed" in c.fix_hint and "joints[1].name" in c.fix_hint
    assert error_failures(report) == {"joint_structure"}


def test_wrong_joint_type(tmp_path):
    xml = mjcf(elbow_joint='<joint name="elbow" type="slide" axis="1 0 0" range="-0.05 0.05" damping="5"/>')
    model, spec = write_case(tmp_path, xml, SPEC)
    c = assert_fails(run_checks(model, spec), "joint_structure")
    assert "joints[1].type" in c.fix_hint


def test_wrong_joint_order(tmp_path):
    s = spec_with()
    s["joints"] = [s["joints"][1], s["joints"][0]]
    model, spec = write_case(tmp_path, mjcf(), s)
    c = assert_fails(run_checks(model, spec), "joint_structure")
    assert "chain order" in c.fix_hint


def test_kinematics_match_hand_edited_axis(tmp_path):
    # flipping the elbow axis keeps the reach, limits and everything else intact
    xml = mjcf(elbow_joint=f'<joint name="elbow" type="hinge" axis="0 -1 0" range="-{R150} {R150}" damping="0.5"/>')
    model, spec = write_case(tmp_path, xml, SPEC)
    report = run_checks(model, spec)
    c = assert_fails(report, "kinematics_match")
    assert "'elbow' (joints[1])" in c.message and "axis" in c.message
    assert "rebuild" in c.fix_hint and "notes" in c.fix_hint
    assert c.measured["ee_position_m"] > 1e-3
    assert error_failures(report) == {"kinematics_match"}


def test_kinematics_match_swapped_link_lengths(tmp_path):
    # 0.25 then 0.3 instead of 0.3 then 0.25: same max reach, wrong kinematics
    xml = (mjcf(site='<site name="ee_site" pos="0.3 0 0"/>')
           .replace('<body name="elbow_link" pos="0.3 0 0">', '<body name="elbow_link" pos="0.25 0 0">'))
    model, spec = write_case(tmp_path, xml, SPEC)
    report = run_checks(model, spec)
    c = assert_fails(report, "kinematics_match")
    assert "'elbow' (joints[1])" in c.message and "mm off" in c.message
    assert c.measured["joint_position_m"] == pytest.approx(0.05, rel=1e-6)
    assert by_id(report)["reach"].passed


def test_kinematics_match_ee_offset_only(tmp_path):
    model, spec = write_case(tmp_path, mjcf(site='<site name="ee_site" pos="0.25 0 0" euler="0 0 0.1"/>'), SPEC)
    c = assert_fails(run_checks(model, spec), "kinematics_match")
    assert c.measured["ee_orientation_rad"] == pytest.approx(0.1, rel=1e-6)
    assert "ee.origin" in c.fix_hint


def test_wrong_limits(tmp_path):
    model, spec = write_case(tmp_path, mjcf(elbow_range="-1 1"), SPEC)
    report = run_checks(model, spec)
    c = assert_fails(report, "joint_limits")
    assert "joints[1].limits" in c.fix_hint
    assert error_failures(report) == {"joint_limits"}


def test_missing_spec_limits_is_warning(tmp_path):
    s = spec_with()
    del s["joints"][1]["limits"]
    model, spec = write_case(tmp_path, mjcf(), s)
    report = run_checks(model, spec)
    c = by_id(report)["joint_limits"]
    assert not c.passed and c.severity == "warning" and "joints[1].limits" in c.fix_hint
    assert report.passed  # warnings never block


URL = "https://example.com/datasheet.pdf"


def sourced_reach(**reach) -> dict:
    """SPEC with the whole reach (value and definition) sourced rather than estimated."""
    return spec_with(reach=reach, sources={"total_mass": URL, "reach": URL}, estimates=["base", "joints", "ee"])


def test_reach_too_long(tmp_path):
    model, spec = write_case(tmp_path, mjcf(), sourced_reach(value=0.45))
    report = run_checks(model, spec)
    c = assert_fails(report, "reach")
    assert "above" in c.message and "too long" in c.fix_hint
    assert "list reach.measured_from/measured_to in `estimates` instead of switching endpoints" in c.fix_hint
    assert "reach.measured_to" in c.fix_hint and "joints[1].origin.xyz" in c.fix_hint
    assert c.measured == pytest.approx(0.55, rel=1e-3) and c.expected == pytest.approx(0.45)
    assert c.details["relative_error"] == pytest.approx(0.55 / 0.45 - 1, rel=1e-2)
    assert error_failures(report) == {"reach"}


def test_reach_too_short(tmp_path):
    model, spec = write_case(tmp_path, mjcf(), sourced_reach(value=0.7))
    c = assert_fails(run_checks(model, spec), "reach")
    assert "below" in c.message and "too short" in c.fix_hint and "joints[*].limits" in c.fix_hint


def test_reach_definition_estimated_is_warning(tmp_path):
    s = spec_with(reach={"value": 0.45}, sources={"total_mass": URL, "reach.value": URL},
                  estimates=["base", "joints", "ee", "reach.measured_from", "reach.measured_to"])
    model, spec = write_case(tmp_path, mjcf(), s)
    report = run_checks(model, spec)
    c = by_id(report)["reach"]
    assert not c.passed and c.severity == "warning" and report.passed
    assert "reach definition is assumed" in c.message and c.details["definition_estimated"]
    assert not c.details["value_estimated"] and "reach.value is itself an estimate" not in c.fix_hint
    assert "instead of switching endpoints" in c.fix_hint


def test_reach_value_estimated_is_warning(tmp_path):
    # SPEC lists the whole `reach` in estimates: value and definition are both estimates
    model, spec = write_case(tmp_path, mjcf(), spec_with(reach={"value": 0.7}))
    report = run_checks(model, spec)
    c = by_id(report)["reach"]
    assert not c.passed and c.severity == "warning" and report.passed
    assert "reach.value is an estimate" in c.message
    assert "reach.value is itself an estimate" in c.fix_hint


def test_reach_hint_names_only_lengths_that_matter(tmp_path, examples_dir):
    # base_axis_horizontal: the first joint's d (along the first axis) does not change the measured reach
    data = yaml.safe_load((examples_dir / "toy_6dof_dh.yaml").read_text())
    data["reach"]["value"] = 700
    data["sources"] = {"reach": URL}
    data["estimates"] = ["joints", "total_mass"]
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(yaml.safe_dump(data))
    model = tmp_path / "model.xml"
    model.write_text(_chain_mjcf(load_spec(spec_path)))
    c = assert_fails(run_checks(model, spec_path, n_reach_samples=500), "reach")
    sens = c.details["length_sensitivity"]
    assert "joints[0].dh.d" not in sens and "joints[0].dh.d" not in c.fix_hint
    assert {"joints[1].dh.a", "joints[2].dh.a"} <= set(sens)
    assert c.fix_hint.index("joints[1].dh.a") < c.fix_hint.index("Also check")


def test_reach_uses_si_units(tmp_path):
    # radians and the same reach expressed with angle unit rad: limits and reach still match
    s = spec_with(units={"length": "m", "angle": "rad"})
    for j in s["joints"]:
        j["limits"] = {"lower": -R150, "upper": R150}
    model, spec = write_case(tmp_path, mjcf(), s)
    report = run_checks(model, spec)
    assert report.passed, [(c.id, c.message) for c in report.checks if not c.passed]


def test_mass_mismatch(tmp_path):
    model, spec = write_case(tmp_path, mjcf(), spec_with(total_mass=4.0))
    report = run_checks(model, spec)
    c = assert_fails(report, "total_mass")
    assert "total_mass" in c.fix_hint and "joints[*].link.mass" in c.fix_hint
    assert error_failures(report) == {"total_mass"}


def test_no_reach_is_warning(tmp_path):
    s = spec_with()
    del s["reach"]
    model, spec = write_case(tmp_path, mjcf(), s)
    report = run_checks(model, spec)
    c = by_id(report)["reach"]
    assert not c.passed and c.severity == "warning" and report.passed
    assert "no rated reach" in c.message and "reach" in c.fix_hint


def test_mass_plausibility_density(tmp_path):
    # 50 kg in a 2.5 cm x 25 cm capsule: ~ 50,000 kg/m^3
    heavy = mjcf(elbow_inertial='<inertial pos="0.125 0 0" mass="50" diaginertia="0.02 0.3 0.3"/>')
    model, spec = write_case(tmp_path, heavy, spec_with(total_mass=52.0))
    report = run_checks(model, spec)
    c = by_id(report)["mass_plausibility"]
    assert not c.passed and c.severity == "warning"
    assert "density" in c.message and "'elbow_link' (joints[1].link)" in c.message
    assert "joints[1].link" in c.fix_hint and c.details["density"]["elbow_link"] > 20000


def test_mass_plausibility_light_link_and_light_arm(tmp_path):
    # 50 g in total for a 0.55 m reach, and a 0.2 g forearm (0.4% of it)
    light = mjcf(elbow_inertial='<inertial pos="0.125 0 0" mass="0.0002" diaginertia="1e-7 2e-6 2e-6"/>',
                 base_mass=0.01).replace('mass="1.0" diaginertia="0.0005 0.008 0.008"',
                                         'mass="0.04" diaginertia="0.00004 0.0006 0.0006"')
    model, spec = write_case(tmp_path, light, spec_with(total_mass=0.0502))
    c = by_id(run_checks(model, spec))["mass_plausibility"]
    assert not c.passed and c.severity == "warning"
    assert "< 0.5% of the total mass" in c.message and "'elbow_link'" in c.message
    assert "per metre of reach" in c.message and c.details["kg_per_m_reach"] < 0.1


def test_inertia_problems_function():
    masses = np.array([1.0, 0.0, 1.0, 1.0, 1.0])
    inertias = np.array([[1, 1, 1], [1, 1, 1], [0.1, 0.1, 1.0], [1, -1, 1], [0.5, 0.5, 1.0]])
    probs = dict(inertia_problems(masses, inertias))
    assert set(probs) == {1, 2, 3}
    assert "A+B>=C" in probs[2]


def test_invalid_inertia_in_model(tmp_path):
    # MuJoCo rejects A+B<C at compile time, but accepts a massless body with zero inertia when
    # the body has no joint of its own (welded to its parent).
    extra = '<body name="flange" pos="0.25 0 0"><inertial pos="0 0 0" mass="0" diaginertia="0 0 0"/></body>'
    model, spec = write_case(tmp_path, mjcf(elbow_extra=extra), SPEC)
    report = run_checks(model, spec)
    c = assert_fails(report, "inertia_valid")
    assert "flange" in c.message and "joints[1].link.mass" in c.fix_hint
    assert error_failures(report) == {"inertia_valid"}


def test_self_collision_at_home(tmp_path):
    # fold the forearm back so its tool-end sphere sinks into the base cylinder (not parent/child)
    s = spec_with()
    s["joints"][1]["home"] = 150
    tool = '<geom name="tool_ball" type="sphere" size="0.045" pos="0.25 0 0"/>'
    model, spec = write_case(tmp_path, mjcf(key=f"0 {R150 - 1e-3}", elbow_extra=tool), s)
    report = run_checks(model, spec)
    c = assert_fails(report, "self_collision_home")
    assert "'base'" in c.message and "'elbow_link'" in c.message
    assert "joints[1].link.geometry[*].radius" in c.fix_hint and "base.link.geometry[*].radius" in c.fix_hint
    assert c.measured > 1e-3
    assert c.details["contacts"][0]["penetration"] > 1e-3


def test_collision_exclusions_reported(tmp_path):
    # the same folded pose as above, but the colliding pair is hidden by a hand-written <exclude>
    s = spec_with()
    s["joints"][1]["home"] = 150
    tool = '<geom name="tool_ball" type="sphere" size="0.045" pos="0.25 0 0"/>'
    excl = ('<contact><!-- base / elbow_link: hides the tool ball --><exclude body1="base" body2="elbow_link"/>'
            '<exclude body1="base" body2="shoulder_link"/></contact>')
    xml = mjcf(key=f"0 {R150 - 1e-3}", elbow_extra=tool).replace("<actuator>", excl + "<actuator>")
    model, spec = write_case(tmp_path, xml, s)
    report = run_checks(model, spec)
    assert by_id(report)["self_collision_home"].passed
    c = by_id(report)["collision_exclusions"]
    assert not c.passed and c.severity == "warning" and c.measured == 1
    assert "base / elbow_link (hides the tool ball)" in c.message
    assert "base / shoulder_link (no reason given)" in c.message
    assert "joints[1].link.geometry" in c.fix_hint
    kinds = {(r["body1"], r["body2"]): r["kind"] for r in c.details["excluded"]}
    assert kinds == {("base", "elbow_link"): "other", ("base", "shoulder_link"): "parent/child"}
    assert report.passed


def test_collision_exclusions_zero_length_links_ok(tmp_path):
    extra = ('<body name="w1" pos="0.25 0 0"><joint name="w1j" axis="1 0 0"/>'
             '<inertial pos="0 0 0" mass="0.1" diaginertia="1e-4 1e-4 1e-4"/>'
             '<body name="w2"><joint name="w2j" axis="0 0 1"/>'
             '<inertial pos="0 0 0" mass="0.1" diaginertia="1e-4 1e-4 1e-4"/></body></body>')
    excl = '<contact><exclude body1="elbow_link" body2="w2"/><exclude body1="shoulder_link" body2="w2"/></contact>'
    xml = mjcf(elbow_extra=extra, key="0 0 0 0").replace("<actuator>", excl + "<actuator>")
    model, spec = write_case(tmp_path, xml, SPEC)
    c = by_id(run_checks(model, spec))["collision_exclusions"]
    kinds = {(r["body1"], r["body2"]): r["kind"] for r in c.details["excluded"]}
    # elbow_link -> w1 (0.25 m) -> w2 (zero offset): separated only by the zero-length link w1
    assert kinds[("elbow_link", "w2")] == "zero-length links between"
    assert kinds[("shoulder_link", "w2")] == "other"
    assert not c.passed and c.measured == 1


def test_unstable_weak_actuators(tmp_path):
    weak = {"shoulder": '<position name="shoulder_act" joint="shoulder" kp="2" kv="0.5"/>',
            "elbow": '<position name="elbow_act" joint="elbow" kp="2" kv="0.5"/>'}
    model, spec = write_case(tmp_path, mjcf(acts=weak), SPEC)
    report = run_checks(model, spec)
    c = assert_fails(report, "stable_hold")
    assert "drifted" in c.message and "joints[*].link.mass" in c.fix_hint and "effort_limit" in c.fix_hint
    assert error_failures(report) == {"stable_hold"}


def test_saturated_actuator_named(tmp_path):
    acts = dict(ACT, shoulder='<position name="shoulder_act" joint="shoulder" kp="500" kv="15" forcerange="-1 1"/>')
    model, spec = write_case(tmp_path, mjcf(acts=acts), SPEC)
    c = assert_fails(run_checks(model, spec), "stable_hold")
    assert c.details["saturated_joints"] == ["shoulder"]
    assert "joints[0].effort_limit" in c.fix_hint


def test_huge_mass_unstable(tmp_path):
    heavy = mjcf(elbow_inertial='<inertial pos="0.125 0 0" mass="500" diaginertia="0.2 3 3"/>', base_mass=1.0)
    model, spec = write_case(tmp_path, heavy, SPEC)
    report = run_checks(model, spec)
    assert_fails(report, "stable_hold")
    c = assert_fails(report, "total_mass")
    assert "joints[1].link.mass is 0.500 kg in the spec but 500.000 kg in the model" in c.fix_hint


def test_missing_actuator(tmp_path):
    model, spec = write_case(tmp_path, mjcf(acts={"shoulder": ACT["shoulder"]}), SPEC)
    report = run_checks(model, spec)
    c = assert_fails(report, "actuators")
    assert "elbow" in c.message and "elbow" in c.fix_hint
    assert error_failures(report) <= {"actuators", "stable_hold"}


def test_duplicate_actuator(tmp_path):
    acts = dict(ACT, extra='<motor name="elbow_motor" joint="elbow" gear="1"/>')
    model, spec = write_case(tmp_path, mjcf(acts=acts), SPEC)
    c = assert_fails(run_checks(model, spec), "actuators")
    assert "elbow_motor" in c.fix_hint


def test_missing_ee_site(tmp_path):
    model, spec = write_case(tmp_path, mjcf(site=""), SPEC)
    report = run_checks(model, spec)
    c = assert_fails(report, "ee_site")
    assert "ee_site" in c.fix_hint
    assert error_failures(report) == {"ee_site", "reach"}


def test_ee_site_on_wrong_body(tmp_path):
    xml = mjcf(site="").replace('<geom name="shoulder_geom"', '<site name="ee_site" pos="0.3 0 0"/><geom name="shoulder_geom"')
    model, spec = write_case(tmp_path, xml, SPEC)
    c = assert_fails(run_checks(model, spec), "ee_site")
    assert "elbow_link" in c.fix_hint


def test_spec_number_without_source(tmp_path):
    s = spec_with(estimates=["base", "joints", "ee"])  # reach.value now uncovered
    model, spec = write_case(tmp_path, mjcf(), s)
    report = run_checks(model, spec)
    c = assert_fails(report, "sources_complete")
    assert "reach.value" in c.message
    assert "add a source URL for reach.value to `sources` or list it in `estimates`" in c.fix_hint
    assert error_failures(report) == {"sources_complete"}


def test_invalid_spec_reported_not_raised(tmp_path):
    model, spec = write_case(tmp_path, mjcf(), spec_text="name: x\ndof: 3\njoints: []\n")
    report = run_checks(model, spec)
    assert not report.passed
    c = assert_fails(report, "joint_structure")
    assert "validate" in c.fix_hint
    assert by_id(report)["compiles"].passed


# --------------------------------------------------------------------------- #
# A 6-DOF DH arm (MJCF generated here from Spec.chain(), not by the builder)
# --------------------------------------------------------------------------- #


def _chain_mjcf(spec) -> str:
    s = spec.to_si()
    ch = s.chain()
    n = len(ch.joints)
    mass = s.total_mass / (n + 1)

    def f(v):
        return " ".join(f"{x:.9g}" for x in v)

    out = ['<mujoco><compiler angle="radian" autolimits="true"/>'
           '<option timestep="0.002" integrator="implicitfast"/><worldbody>',
           f'<body name="base" pos="{f(ch.base_pos)}" quat="{f(ch.base_quat)}">'
           f'<inertial pos="0 0 0" mass="{mass}" diaginertia="0.01 0.01 0.01"/>']
    for j, sj in zip(ch.joints, s.joints):
        out.append(f'<body name="{j.name}_link" pos="{f(j.pos)}" quat="{f(j.quat)}">'
                   f'<joint name="{j.name}" type="{j.type}" axis="{f(j.axis)}" '
                   f'range="{sj.limits.lower:.9g} {sj.limits.upper:.9g}" damping="5"/>'
                   f'<inertial pos="0 0 0" mass="{mass}" diaginertia="0.01 0.01 0.01"/>')
    out.append(f'<site name="{s.ee.name}" pos="{f(ch.ee_pos)}"/>' + "</body>" * (n + 1) + "</worldbody><actuator>")
    out += [f'<position name="{j.name}_act" joint="{j.name}" kp="2000" kv="100"/>' for j in s.joints]
    out.append("</actuator></mujoco>")
    return "".join(out)


def test_dh_6dof_example(tmp_path, examples_dir):
    data = yaml.safe_load((examples_dir / "toy_6dof_dh.yaml").read_text())
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(yaml.safe_dump(data))
    model = tmp_path / "model.xml"
    model.write_text(_chain_mjcf(load_spec(spec_path)))
    t0 = time.perf_counter()
    report = run_checks(model, spec_path)
    assert time.perf_counter() - t0 < 5.0
    checks = by_id(report)
    for cid in CONTRACT_IDS:
        if cid != "reach":
            assert checks[cid].passed, checks[cid]
    # Independent max of the reach metric (horizontal distance from the j1 axis) via the spec's numpy FK.
    ch = load_spec(spec_path).to_si().chain()
    rng = np.random.default_rng(1)
    lims = np.array([[j.limits.lower, j.limits.upper] for j in load_spec(spec_path).to_si().joints])
    best = max(np.hypot(*ch.fk(q)[:2, 3]) for q in rng.uniform(lims[:, 0], lims[:, 1], size=(3000, 6)))
    measured = checks["reach"].measured
    assert measured >= best - 1e-6  # the refined max is at least the sampled max
    assert measured <= best * 1.03
    # deterministic for a fixed seed
    assert by_id(run_checks(model, spec_path, seed=0))["reach"].measured == pytest.approx(measured)
