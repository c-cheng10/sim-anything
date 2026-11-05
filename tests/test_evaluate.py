"""Tests for simanything.evaluate (docs/CONTRACTS.md section 5)."""

from __future__ import annotations

import math
import re
import time
from pathlib import Path

import numpy as np
import pytest
import yaml

from simanything.evaluate import compute_score, evaluate, load_mapping, sampling_interval
from simanything.schemas import EvalResult, JointConvention, Mapping

FIX = Path(__file__).resolve().parent / "fixtures" / "eval"
REF = FIX / "arm_ref.xml"
CAND = FIX / "arm_cand.xml"
PI = math.pi

REF_JOINTS = ["j1", "j2", "j3", "j4"]


def _self_mapping(joints=REF_JOINTS, ee=None, **kw) -> Mapping:
    ee = ee or {"site": "tool"}
    return Mapping.model_validate({"candidate": {"joints": joints, "ee": ee},
                                   "reference": {"joints": joints, "ee": {"site": "tool"}}, **kw})


def _variant(tmp_path: Path, src: Path, name: str, *subs: tuple[str, str]) -> Path:
    text = src.read_text()
    for old, new in subs:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    out = tmp_path / name
    out.write_text(text)
    return out


# --------------------------------------------------------------------------- #
# Mapping file
# --------------------------------------------------------------------------- #


def test_load_mapping_fixture():
    m = load_mapping(FIX / "arm_map.yaml")
    assert m.robot == "arm"
    assert m.candidate.joints == ["a1", "a2", "a3", "a4"]
    assert m.reference.ee.site == "tool"
    assert m.joint_conventions is None and m.fit_conventions is True


def test_mapping_yaml_round_trip(tmp_path):
    m = Mapping.model_validate({
        "robot": "x",
        "candidate": {"joints": ["a", "b"], "ee": {"site": "ee"}},
        "reference": {"joints": ["A", "B"], "ee": {"body": "flange", "pos": [0, 0, 0.1], "quat": [0, 1, 0, 0]}},
        "joint_conventions": [{"sign": -1, "offset": PI / 2}, {"sign": 1, "offset": 0.0}],
        "fit_conventions": False,
    })
    p = tmp_path / "map.yaml"
    p.write_text(yaml.safe_dump(m.model_dump(mode="json")))
    assert load_mapping(p) == m


@pytest.mark.parametrize("bad, msg", [
    ({"reference": {"joints": ["A"], "ee": {"site": "s"}}}, "same|entries"),
    ({"joint_conventions": [{"sign": 1, "offset": 0}]}, "joint_conventions"),
    ({"candidate": {"joints": ["a", "b"], "ee": {}}}, "exactly one"),
    ({"candidate": {"joints": ["a", "b"], "ee": {"site": "s", "body": "b"}}}, "exactly one"),
])
def test_load_mapping_rejects_bad_files(tmp_path, bad, msg):
    data = {"candidate": {"joints": ["a", "b"], "ee": {"site": "s"}},
            "reference": {"joints": ["A", "B"], "ee": {"site": "s"}}}
    data.update(bad)
    p = tmp_path / "map.yaml"
    p.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match=msg):
        load_mapping(p)


# --------------------------------------------------------------------------- #
# Self-contained kinematic tests
# --------------------------------------------------------------------------- #


def test_self_evaluation_is_perfect():
    res = evaluate(REF, REF, _self_mapping(REF_JOINTS + ["finger"]), n_samples=500)
    assert isinstance(res, EvalResult)
    assert res.ee_position_error_mm.max < 1e-9
    assert res.ee_orientation_error_deg.max < 1e-6
    assert res.ee_orientation_error_aligned_deg.max < 1e-6
    assert res.conventions_fitted
    assert all(c.sign == 1 and c.offset == 0.0 for c in res.conventions)
    assert res.joint_limit_mae_deg == 0.0
    assert res.dof_match and res.dof_candidate == 5
    assert res.mass_diff == 0.0
    assert res.score == pytest.approx(100.0, abs=1e-6)
    assert not any("unmapped" in n for n in res.notes)


def test_conventions_are_recovered_and_tool_rotation_aligned():
    res = evaluate(CAND, REF, load_mapping(FIX / "arm_map.yaml"), n_samples=1000, seed=3)
    got = [(c.sign, c.offset) for c in res.conventions]
    assert got == [(1, PI / 2), (-1, 0.0), (1, -PI / 2), (-1, 0.0)]
    assert res.conventions_fitted
    assert res.ee_position_error_mm.max < 1e-6
    # The candidate tool site is rotated 90 deg about z: large raw, ~0 aligned error.
    assert res.ee_orientation_error_deg.mean == pytest.approx(90.0, abs=1e-6)
    assert res.ee_orientation_error_aligned_deg.max < 1e-6
    assert res.dof_match and res.dof_candidate == 4 and res.dof_reference == 4
    # The reference's unmapped finger joint is reported, and its mass counted.
    assert any("unmapped" in n and "finger" in n for n in res.notes)
    assert res.mass_reference == pytest.approx(5.25)
    assert res.mass_candidate == pytest.approx(5.2)
    assert res.mass_rel_diff == pytest.approx(-0.05 / 5.25)


def test_wrong_given_conventions_are_used_as_is():
    m = load_mapping(FIX / "arm_map.yaml")
    m.joint_conventions = [JointConvention() for _ in range(4)]
    res = evaluate(CAND, REF, m, n_samples=200)
    assert not res.conventions_fitted
    assert all(c.sign == 1 and c.offset == 0.0 for c in res.conventions)
    assert res.ee_position_error_mm.mean > 100.0


def test_no_fit_uses_identity():
    m = load_mapping(FIX / "arm_map.yaml")
    m.fit_conventions = False
    res = evaluate(CAND, REF, m, n_samples=200)
    assert not res.conventions_fitted
    assert [(c.sign, c.offset) for c in res.conventions] == [(1, 0.0)] * 4


def test_joint_limits_in_reference_coordinates():
    res = evaluate(CAND, REF, load_mapping(FIX / "arm_map.yaml"), n_samples=100)
    lim = {d.candidate: d for d in res.joint_limits}
    # a1: [-3, 3] shifted by +pi/2
    assert lim["a1"].candidate_range == pytest.approx([-3 + PI / 2, 3 + PI / 2])
    assert lim["a1"].lower_diff == pytest.approx(PI / 2)
    # a2: [-1, 2.5] with sign -1 -> [-2.5, 1] vs [-2, 2]
    assert lim["a2"].candidate_range == pytest.approx([-2.5, 1.0])
    assert (lim["a2"].lower_diff, lim["a2"].upper_diff) == pytest.approx((-0.5, -1.0))
    # a3: [-1, 4] shifted by -pi/2 vs [-2.5, 2.5]
    assert lim["a3"].lower_diff == pytest.approx(-1 - PI / 2 + 2.5)
    # a4 / j4 both unlimited -> no difference
    assert (lim["a4"].lower_diff, lim["a4"].upper_diff) == (0.0, 0.0)
    expected = np.degrees(np.mean([PI / 2, PI / 2, 0.5, 1.0, abs(-1 - PI / 2 + 2.5), abs(4 - PI / 2 - 2.5), 0, 0]))
    assert res.joint_limit_mae_deg == pytest.approx(expected)


def test_ee_body_with_offset_matches_site():
    # The reference tool site sits at the origin of link4 == link3 origin + 0.3 m along x.
    m = _self_mapping(ee={"body": "link3", "pos": [0.3, 0.0, 0.0]})
    res = evaluate(REF, REF, m, n_samples=300)
    assert res.ee_position_error_mm.max < 1e-9
    # link3 differs from the tool frame by the j4 rotation: not a constant tool rotation.
    assert res.ee_orientation_error_aligned_deg.max > 10.0


def test_rotated_tool_frame_only_affects_raw_orientation(tmp_path):
    rot = _variant(tmp_path, REF, "rot.xml",
                   ('<site name="tool" pos="0 0 0"/>', '<site name="tool" pos="0 0 0" euler="0.4 -1.1 2.0"/>'))
    res = evaluate(rot, REF, _self_mapping(), n_samples=400)
    assert res.ee_position_error_mm.max < 1e-9
    assert res.ee_orientation_error_deg.mean > 60.0
    assert res.ee_orientation_error_deg.max - res.ee_orientation_error_deg.mean < 1e-6  # constant offset
    assert res.ee_orientation_error_aligned_deg.max < 1e-6
    assert res.score_breakdown["orient"] == pytest.approx(1.0)


def test_perturbed_link_gives_exact_offset_error(tmp_path):
    delta = 0.02
    longer = _variant(tmp_path, REF, "long.xml",
                      ('<body name="link3" pos="0.4 0 0">', f'<body name="link3" pos="{0.4 + delta} 0 0">'))
    res = evaluate(longer, REF, _self_mapping(REF_JOINTS + ["finger"]), n_samples=500)
    for v in (res.ee_position_error_mm.mean, res.ee_position_error_mm.p95, res.ee_position_error_mm.max):
        assert v == pytest.approx(delta * 1000, abs=1e-6)
    assert res.ee_orientation_error_deg.max < 1e-6


def test_slide_joint_mapping(tmp_path):
    m = _self_mapping(REF_JOINTS + ["finger"], ee={"body": "finger"})
    m.reference.ee = m.candidate.ee
    shifted = _variant(tmp_path, REF, "fing.xml", ('range="0 0.04"', 'range="0.01 0.05"'))
    res = evaluate(shifted, REF, m, n_samples=300)
    assert res.ee_position_error_mm.max < 1e-9
    fd = res.joint_limits[-1]
    assert (fd.lower_diff, fd.upper_diff) == pytest.approx((0.01, 0.01))
    # slide limits do not enter the (hinge, degrees) MAE
    assert res.joint_limit_mae_deg == 0.0


def test_empty_intersection_falls_back_with_note(tmp_path):
    far = _variant(tmp_path, REF, "far.xml", ('range="-2 2"', 'range="2.5 3"'))
    m = _self_mapping(fit_conventions=False)
    res = evaluate(far, REF, m, n_samples=50)
    assert any("do not intersect" in n and "j2" in n for n in res.notes)


def test_unknown_joint_and_site_raise():
    with pytest.raises(ValueError, match="nope"):
        evaluate(REF, REF, _self_mapping(["j1", "nope"]))
    with pytest.raises(ValueError, match="site 'missing'"):
        evaluate(REF, REF, _self_mapping(ee={"site": "missing"}))


def test_seed_is_reproducible():
    m = load_mapping(FIX / "arm_map.yaml")
    a = evaluate(CAND, REF, m, n_samples=100, seed=7)
    b = evaluate(CAND, REF, m, n_samples=100, seed=7)
    assert a == b


# --------------------------------------------------------------------------- #
# Sampling intervals
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("cand, ref, sign, offset, expected", [
    ((-1.0, 2.0), (-3.0, 3.0), 1, 0.0, (-1.0, 2.0, False)),
    ((-3.0, 3.0), (-1.0, 2.0), 1, 0.0, (-1.0, 2.0, False)),
    # q_ref = -q_cand: reference [-1, 2] maps to candidate [-2, 1]
    ((-3.0, 3.0), (-1.0, 2.0), -1, 0.0, (-2.0, 1.0, False)),
    # q_ref = q_cand + 1: reference [-1, 2] maps to [-2, 1], intersect [-1.5, 3] -> [-1.5, 1]
    ((-1.5, 3.0), (-1.0, 2.0), 1, 1.0, (-1.5, 1.0, False)),
    # q_ref = -q_cand + 1: reference [-1, 2] maps to [-1, 2], intersect [0, 3] -> [0, 2]
    ((0.0, 3.0), (-1.0, 2.0), -1, 1.0, (0.0, 2.0, False)),
    # unlimited reference: candidate range
    ((-0.5, 0.5), None, -1, PI, (-0.5, 0.5, False)),
    # unlimited candidate: mapped reference range
    (None, (0.0, 1.0), -1, 0.0, (-1.0, 0.0, False)),
    (None, None, 1, PI, (-PI, PI, False)),
    # empty -> candidate range, flagged
    ((0.5, 1.0), (0.0, 1.0), -1, 0.0, (0.5, 1.0, True)),
])
def test_sampling_interval(cand, ref, sign, offset, expected):
    lo, hi, empty = sampling_interval(cand, ref, JointConvention(sign=sign, offset=offset))
    assert (lo, hi) == pytest.approx(expected[:2])
    assert empty is expected[2]


# --------------------------------------------------------------------------- #
# Score
# --------------------------------------------------------------------------- #


def test_score_formula():
    s, b = compute_score(0.0, 0.0, 0.0, 0.0, True)
    assert s == pytest.approx(100.0)
    assert b == {"pos": 1.0, "orient": 1.0, "limits": 1.0, "mass": 1.0, "dof": 1.0}

    s, b = compute_score(25.0, 10.0, 10.0, -0.2, False)
    e = math.exp(-1)
    assert b == pytest.approx({"pos": e, "orient": e, "limits": e, "mass": e, "dof": 0.0})
    assert s == pytest.approx(100 * 0.95 * e)

    s, _ = compute_score(50.0, 0.0, 0.0, 0.0, True)
    assert s == pytest.approx(100 * (0.5 * math.exp(-2) + 0.5))


def test_score_in_result_matches_formula():
    res = evaluate(CAND, REF, load_mapping(FIX / "arm_map.yaml"), n_samples=200)
    s, b = compute_score(res.ee_position_error_mm.p95, res.ee_orientation_error_aligned_deg.p95,
                         res.joint_limit_mae_deg, res.mass_rel_diff, res.dof_match)
    assert res.score == pytest.approx(s)
    assert res.score_breakdown == pytest.approx(b)


# --------------------------------------------------------------------------- #
# Menagerie (skipped when absent)
# --------------------------------------------------------------------------- #

UR5E_JOINTS = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
               "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]


def _ur5e_mapping() -> Mapping:
    side = {"joints": UR5E_JOINTS, "ee": {"site": "attachment_site"}}
    return Mapping.model_validate({"robot": "ur5e", "candidate": side, "reference": side})


def _ur5e_copy(menagerie_dir: Path, tmp_path: Path, *subs: tuple[str, str]) -> Path:
    src = menagerie_dir / "universal_robots_ur5e" / "ur5e.xml"
    assets = (src.parent / "assets").resolve()
    text = src.read_text()
    text, n = re.subn(r'meshdir="assets"', f'meshdir="{assets}"', text)
    assert n == 1
    for old, new in subs:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    out = tmp_path / "ur5e_perturbed.xml"
    out.write_text(text)
    return out


@pytest.mark.menagerie
def test_ur5e_self_evaluation(menagerie_dir):
    ur5e = menagerie_dir / "universal_robots_ur5e" / "ur5e.xml"
    t0 = time.perf_counter()
    res = evaluate(ur5e, ur5e, _ur5e_mapping(), n_samples=2000, seed=0)
    elapsed = time.perf_counter() - t0
    assert res.ee_position_error_mm.max < 1e-9
    assert res.ee_orientation_error_deg.max < 1e-6
    assert res.ee_orientation_error_aligned_deg.max < 1e-6
    assert all(c.sign == 1 and c.offset == 0.0 for c in res.conventions)
    assert res.dof_match and res.mass_diff == 0.0 and res.joint_limit_mae_deg == 0.0
    assert res.score == pytest.approx(100.0, abs=1e-6)
    assert elapsed < 10.0


@pytest.mark.menagerie
def test_ur5e_lengthened_forearm(menagerie_dir, tmp_path):
    # Moving a body origin by d translates everything below it rigidly by R_parent(q) d,
    # so the EE position error is exactly |d| in every configuration and orientation is unchanged.
    delta = 0.05
    cand = _ur5e_copy(menagerie_dir, tmp_path, ('pos="0 -0.131 0.425"', f'pos="0 -0.131 {0.425 + delta}"'))
    ref = menagerie_dir / "universal_robots_ur5e" / "ur5e.xml"
    res = evaluate(cand, ref, _ur5e_mapping(), n_samples=2000, seed=1)
    assert all(c.sign == 1 and c.offset == 0.0 for c in res.conventions)
    for v in (res.ee_position_error_mm.mean, res.ee_position_error_mm.p95, res.ee_position_error_mm.max):
        assert v == pytest.approx(delta * 1000, abs=1e-6)
    assert res.ee_orientation_error_deg.max < 1e-6
    assert res.score_breakdown["pos"] == pytest.approx(math.exp(-50.0 / 25.0))


def test_base_yaw_is_fitted_instead_of_joint1_offset(tmp_path):
    """A candidate whose base frame is turned 180 deg about z (a mounting convention)
    gets base_yaw_deg = 180 with identity joint conventions, so limits compare cleanly."""
    xml = REF.read_text().replace('<body name="base">', '<body name="base" euler="0 0 3.14159265358979">')
    cand = tmp_path / "turned.xml"
    cand.write_text(xml)
    m = {"candidate": {"joints": ["j1", "j2", "j3", "j4"], "ee": {"site": "tool"}},
         "reference": {"joints": ["j1", "j2", "j3", "j4"], "ee": {"site": "tool"}}}
    res = evaluate(cand, REF, m, n_samples=300)
    assert abs(abs(res.base_yaw_deg) - 180.0) < 1e-6
    assert [(c.sign, c.offset) for c in res.conventions] == [(1, 0.0)] * 4
    assert res.ee_position_error_mm.max < 1e-6
    assert res.joint_limit_mae_deg == pytest.approx(0.0, abs=1e-9)


def test_base_body_frames_remove_mounting_offset(tmp_path):
    """A reference standing on a pedestal (base body raised) matches when both sides
    express EE poses in their base body frames."""
    xml = REF.read_text().replace('<body name="base">', '<body name="base" pos="0 0 0.12">')
    raised = tmp_path / "raised.xml"
    raised.write_text(xml)
    side = {"joints": ["j1", "j2", "j3", "j4"], "ee": {"site": "tool"}}
    m = {"candidate": side, "reference": side}
    res = evaluate(REF, raised, m, n_samples=200)
    assert res.ee_position_error_mm.max == pytest.approx(120.0, abs=1e-6)
    m2 = {"candidate": {**side, "base_body": "base"}, "reference": {**side, "base_body": "base"}}
    res2 = evaluate(REF, raised, m2, n_samples=200)
    assert res2.ee_position_error_mm.max < 1e-6
    with pytest.raises(ValueError):
        evaluate(REF, raised, {"candidate": {**side, "base_body": "link2"}, "reference": side}, n_samples=10)


def test_unlimited_slide_uses_a_sane_default_range(tmp_path):
    """An unlimited slide is sampled over +-0.1 m, not +-pi metres."""
    from simanything.evaluate import UNLIMITED_SLIDE_RANGE_M, default_range

    assert UNLIMITED_SLIDE_RANGE_M == 0.1
    assert default_range(3) == (-PI, PI)  # mjJNT_HINGE
    assert default_range(2) == (-0.1, 0.1)  # mjJNT_SLIDE
    assert sampling_interval(None, None, JointConvention(), unlimited=(-0.1, 0.1)) == (-0.1, 0.1, False)

    free = _variant(tmp_path, REF, "free_ref.xml", (' range="0 0.04"', ""))
    # same slide, but moving along x instead of z: EE error = sqrt(2) |q|
    tilted = _variant(tmp_path, free, "free_cand.xml", ('type="slide" axis="0 0 1"', 'type="slide" axis="1 0 0"'))
    m = _self_mapping(REF_JOINTS + ["finger"], ee={"body": "finger"}, fit_conventions=False)
    m.reference.ee = m.candidate.ee
    res = evaluate(tilted, free, m, n_samples=400)
    assert res.ee_position_error_mm.max <= math.sqrt(2) * 100 + 1e-6
    assert res.ee_position_error_mm.max > 100  # the default range is actually used
    fd = res.joint_limits[-1]
    assert fd.candidate_range == pytest.approx([-0.1, 0.1]) and fd.reference_range == pytest.approx([-0.1, 0.1])

    # unlimited candidate slide vs limited reference slide: compared as [-0.1, 0.1] m
    res = evaluate(free, REF, m, n_samples=50)
    fd = res.joint_limits[-1]
    assert (fd.lower_diff, fd.upper_diff) == pytest.approx((-0.1, 0.06))
    assert any("[-0.1, 0.1] m (slide)" in n for n in res.notes)
