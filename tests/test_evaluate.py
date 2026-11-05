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


PANDA_JOINTS = [f"joint{i}" for i in range(1, 8)]


def _reconventioned(src: Path, out: Path, joints: list[str], conv: list[tuple[int, float]], yaw: float) -> Path:
    """Exact copy of ``src`` whose joint i satisfies q_src = sign * q_out + offset (axis
    flipped, zero moved via the joint ``ref``, range mapped) and whose top-level bodies are
    turned by -yaw about world z, so the evaluator should fit ``conv`` and base yaw ``yaw``.
    Values are written with full float precision, so the kinematics are identical."""
    import xml.etree.ElementTree as ET

    import mujoco

    model = mujoco.MjModel.from_xml_path(str(src))
    tree = ET.parse(src)
    root = tree.getroot()
    for comp in root.iter("compiler"):
        for attr in ("meshdir", "texturedir", "assetdir"):
            if attr in comp.attrib:
                comp.set(attr, str((src.parent / comp.get(attr)).resolve()))
    fmt = lambda v: " ".join(repr(float(a)) for a in v)  # noqa: E731
    for name, (s, o) in zip(joints, conv):
        el = next(e for e in root.iter("joint") if e.get("name") == name)
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        r0 = float(model.qpos0[model.jnt_qposadr[jid]])
        lo, hi = (s * (v - o) for v in model.jnt_range[jid])
        el.set("axis", fmt(s * model.jnt_axis[jid]))
        el.set("ref", repr(s * (r0 - o)))
        el.set("range", fmt(sorted((lo, hi))))
    c, sn = math.cos(-yaw), math.sin(-yaw)
    qz = np.array([math.cos(-yaw / 2), 0.0, 0.0, math.sin(-yaw / 2)])
    for el in root.find("worldbody").findall("body"):
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, el.get("name"))
        quat = np.empty(4)
        mujoco.mju_mulQuat(quat, qz, model.body_quat[bid])
        for attr in ("euler", "axisangle", "xyaxes", "zaxis"):
            el.attrib.pop(attr, None)
        el.set("quat", fmt(quat))
        el.set("pos", fmt(np.array([[c, -sn, 0.0], [sn, c, 0.0], [0.0, 0.0, 1.0]]) @ model.body_pos[bid]))
    tree.write(out)
    return out


def _random_conventions(rng: np.random.Generator, n: int, frac: float) -> tuple[list[tuple[int, float]], float]:
    choices = (0.0, PI / 2, -PI / 2, PI)
    conv = [(int(rng.choice([1, -1])), float(rng.choice(choices))) if rng.random() < frac else (1, 0.0)
            for _ in range(n)]
    yaw = float(rng.choice(choices)) if rng.random() < frac else 0.0
    return conv, yaw


MENAGERIE_ARMS = {
    "panda": ("franka_emika_panda/panda_nohand.xml", PANDA_JOINTS),
    "ur5e": ("universal_robots_ur5e/ur5e.xml", UR5E_JOINTS),
}


@pytest.mark.menagerie
@pytest.mark.parametrize("robot", sorted(MENAGERIE_ARMS))
def test_reconventioned_menagerie_arm_is_recovered(menagerie_dir, tmp_path, robot):
    """Re-conventioned exact copies (random signs/offsets on all or some joints plus a base
    yaw) must fit to ~0 EE error (the discrete search must not stop in a local minimum)
    and ~0 limit MAE (among kinematically equivalent conventions, e.g. yaw vs joint-1
    offset or the Panda's roll-pitch-roll shoulder flip, the one matching the limits wins),
    so they score 100."""
    rel, joints = MENAGERIE_ARMS[robot]
    ref = menagerie_dir / rel
    side = {"joints": joints, "ee": {"site": "attachment_site"}}
    # Trials 0-5: every joint and the yaw re-conventioned; 6-8: about 30% of them.
    # (Before pair/triple moves, Panda trials 0, 3 and 4 stopped at 27-353 mm.)
    for trial in range(9):
        conv, yaw = _random_conventions(np.random.default_rng(1000 + trial), len(joints), 1.0 if trial < 6 else 0.3)
        cand = _reconventioned(ref, tmp_path / f"{robot}_{trial}.xml", joints, conv, yaw)
        res = evaluate(cand, ref, {"candidate": side, "reference": side}, n_samples=500, seed=trial)
        assert res.ee_position_error_mm.max < 1e-6, (trial, conv, yaw, res.conventions, res.base_yaw_deg)
        assert res.ee_orientation_error_aligned_deg.max < 1e-6, (trial, conv, yaw)
        assert res.joint_limit_mae_deg < 1e-6, (trial, conv, yaw, res.conventions, res.base_yaw_deg)
        assert res.score == pytest.approx(100.0, abs=1e-4)


@pytest.mark.menagerie
def test_seven_dof_evaluate_is_fast(menagerie_dir, tmp_path):
    ref = menagerie_dir / MENAGERIE_ARMS["panda"][0]
    conv, yaw = _random_conventions(np.random.default_rng(7), 7, 1.0)
    cand = _reconventioned(ref, tmp_path / "panda.xml", PANDA_JOINTS, conv, yaw)
    side = {"joints": PANDA_JOINTS, "ee": {"site": "attachment_site"}}
    t0 = time.perf_counter()
    evaluate(cand, ref, {"candidate": side, "reference": side}, n_samples=2000, seed=0)
    assert time.perf_counter() - t0 < 15.0


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


def test_equal_cost_conventions_resolve_to_lowest_limit_mae(tmp_path):
    """The candidate is the reference with joint 1's zero turned by +90 deg about z and
    joint 4's zero by +90 deg about its own (EE-through) axis, limits moved accordingly.
    'yaw +90, j1 offset 0' fits the EE as well as 'j1 offset +90' (and j4 offsets 0 or
    +-90 only rotate the tool frame by a constant), but only the latter matches the
    limits; the simpler/yaw-first choice would cost ~45 deg of limit MAE."""
    h = PI / 2
    ref = _variant(tmp_path, REF, "ref_lim.xml",
                   ('<joint name="j4" axis="1 0 0"/>', '<joint name="j4" axis="1 0 0" range="-1 2"/>'))
    cand = _variant(tmp_path, ref, "cand_lim.xml",
                    ('<body name="link1" pos="0 0 0.1">', f'<body name="link1" pos="0 0 0.1" euler="0 0 {h!r}">'),
                    ('<joint name="j1" axis="0 0 1" range="-3 3"/>',
                     f'<joint name="j1" axis="0 0 1" range="{-3 - h!r} {3 - h!r}"/>'),
                    ('<body name="link4" pos="0.3 0 0">', f'<body name="link4" pos="0.3 0 0" euler="{h!r} 0 0">'),
                    ('range="-1 2"', f'range="{-1 - h!r} {2 - h!r}"'))
    res = evaluate(cand, ref, _self_mapping(REF_JOINTS + ["finger"]), n_samples=300)
    assert res.ee_position_error_mm.max < 1e-6
    assert res.ee_orientation_error_aligned_deg.max < 1e-6
    assert res.base_yaw_deg == 0.0
    assert [(c.sign, c.offset) for c in res.conventions] == [(1, h), (1, 0.0), (1, 0.0), (1, h), (1, 0.0)]
    assert res.joint_limit_mae_deg == pytest.approx(0.0, abs=1e-9)
    assert res.score == pytest.approx(100.0, abs=1e-6)


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
