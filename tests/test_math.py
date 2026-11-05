"""Regression tests for the builder's mass/inertia maths and frame conventions, and for the reach
metric's point/origin rules. Reference values come from MuJoCo itself (inertia from geometry) or
from independent textbook formulas (dh_fk), not from the builder."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np
import pytest

from simanything.builder import Prim, build_mjcf
from simanything.check import run_checks
from simanything.check.physics import geom_volume
from simanything.spec import (DH, EndEffector, GeometryHint, Joint, Link, Pose, Spec, Units, dh_fk, dump_spec,
                              load_spec, quat_to_mat)

ROOT = Path(__file__).resolve().parents[1]
DENSITY = 1000.0


def _mujoco_body(geom_xml: str) -> tuple[float, np.ndarray, np.ndarray]:
    """(mass, COM, full inertia tensor about the COM in the body frame) that MuJoCo computes from geoms."""
    xml = (f'<mujoco><compiler inertiafromgeom="true"/><worldbody><body name="b"><freejoint/>{geom_xml}'
           '</body></worldbody></mujoco>')
    m = mujoco.MjModel.from_xml_string(xml)
    return float(m.body_mass[1]), np.array(m.body_ipos[1]), _full_inertia(m, 1)


def _full_inertia(m: mujoco.MjModel, b: int) -> np.ndarray:
    R = quat_to_mat(m.body_iquat[b])
    return R @ np.diag(m.body_inertia[b]) @ R.T


# --------------------------------------------------------------------------- #
# Per-primitive inertia vs MuJoCo's inertia from geometry
# --------------------------------------------------------------------------- #

PRIMS = [
    ("sphere", [0.07], '<geom type="sphere" size="0.07" density="1000"/>'),
    ("capsule", [0.04, 0.15], '<geom type="capsule" size="0.04 0.15" density="1000"/>'),
    ("capsule", [0.06, 0.01], '<geom type="capsule" size="0.06 0.01" density="1000"/>'),  # nearly a sphere
    ("cylinder", [0.05, 0.2], '<geom type="cylinder" size="0.05 0.2" density="1000"/>'),
    ("cylinder", [0.2, 0.02], '<geom type="cylinder" size="0.2 0.02" density="1000"/>'),  # a disk
    ("box", [0.1, 0.03, 0.05], '<geom type="box" size="0.1 0.03 0.05" density="1000"/>'),
]


@pytest.mark.parametrize("kind,size,geom", PRIMS)
def test_primitive_inertia_matches_mujoco(kind, size, geom):
    p = Prim(kind, size, np.zeros(3))
    mass = DENSITY * p.volume()
    m_ref, com_ref, I_ref = _mujoco_body(geom)
    assert mass == pytest.approx(m_ref, rel=1e-9)
    assert np.allclose(com_ref, 0, atol=1e-12)
    assert np.allclose(p.inertia_local(mass), I_ref, rtol=1e-7, atol=1e-12)


def _geom_xml(p: Prim, density: float) -> str:
    if p.kind in ("capsule", "cylinder"):
        ax = p.R[:, 2] * p.size[1]
        ft = " ".join(f"{x:.15g}" for x in np.concatenate([p.pos - ax, p.pos + ax]))
        return f'<geom type="{p.kind}" size="{p.size[0]:.15g}" fromto="{ft}" density="{density:.15g}"/>'
    from simanything.spec import mat_to_quat

    q = " ".join(f"{x:.15g}" for x in mat_to_quat(p.R))
    pos = " ".join(f"{x:.15g}" for x in p.pos)
    size = " ".join(f"{x:.15g}" for x in p.size)
    return f'<geom type="{p.kind}" size="{size}" pos="{pos}" quat="{q}" density="{density:.15g}"/>'


def test_parallel_axis_multi_geom_combination():
    """Several offset/rotated primitives with one density: the builder's combination (mass split by
    volume, parallel-axis theorem about the volume centroid) equals MuJoCo's."""
    from simanything.builder import _rot_z_to
    from simanything.spec import rpy_to_mat

    prims = [Prim("capsule", [0.04, 0.12], np.array([0.1, 0.02, 0.0]), _rot_z_to(np.array([1.0, 0.2, 0.1]))),
             Prim("box", [0.05, 0.02, 0.03], np.array([-0.05, 0.1, 0.04]), rpy_to_mat([0.3, -0.2, 0.7])),
             Prim("sphere", [0.05], np.array([0.0, -0.08, 0.12])),
             Prim("cylinder", [0.03, 0.06], np.array([0.2, 0.0, -0.1]), _rot_z_to(np.array([0.0, 1.0, 1.0])))]
    mass = 3.7
    vol = sum(p.volume() for p in prims)
    # the builder's maths, through the same code path as a real link
    from simanything.builder import BodyPlan, _assign_mass_inertia

    body = BodyPlan(name="x", pos=np.zeros(3), quat=np.array([1.0, 0, 0, 0]), link=Link(mass=mass), prims=prims,
                    joint_index=0, segment=np.array([0.3, 0, 0]))
    spec = Spec(name="t", dof=1, units=Units(angle="rad"), joints=[Joint(name="j", origin=Pose())])
    _assign_mass_inertia(spec, [body])
    m_ref, com_ref, I_ref = _mujoco_body("".join(_geom_xml(p, mass / vol) for p in prims))
    assert body.mass == pytest.approx(m_ref, rel=1e-9)
    assert np.allclose(body.com, com_ref, atol=1e-12)
    # the builder adds 1e-6 * trace(I) (+1e-9) to the diagonal to keep the tensor strictly positive
    reg = 1e-9 + 1e-6 * np.trace(I_ref)
    # (MuJoCo stores the combined tensor as principal values + frame: ~1e-9 relative round-off)
    assert np.allclose(body.inertia - reg * np.eye(3), I_ref, rtol=1e-7, atol=1e-10)
    # and the offsets matter: without the parallel-axis terms the result would be far off
    assert not np.allclose(sum(p.R @ p.inertia_local(mass * p.volume() / vol) @ p.R.T for p in prims), I_ref,
                           rtol=0.05)


@pytest.mark.parametrize("name", ["toy_2link", "toy_6dof_dh", "toy_6dof_mdh", "toy_scara"])
def test_example_body_inertias_match_mujoco(name):
    """For every body of the built examples without an explicit link.com: mass, COM and the full
    inertia tensor equal what MuJoCo derives from the same geoms at a uniform density."""
    spec = load_spec(ROOT / "examples" / f"{name}.yaml")
    xml = build_mjcf(spec)
    m = mujoco.MjModel.from_xml_string(xml)
    root = ET.fromstring(xml)
    root.find("compiler").set("inertiafromgeom", "true")
    explicit_com = {"base"} if spec.base.link.com is not None else set()
    explicit_com |= {j.link.name or f"{j.name}_link" for j in spec.joints if j.link.com is not None}
    for body in root.iter("body"):
        b = m.body(body.get("name")).id
        geoms = [g for g in range(m.ngeom) if m.geom_bodyid[g] == b]
        density = m.body_mass[b] / sum(geom_volume(m, g) for g in geoms)
        for g in body.findall("geom"):
            g.set("density", repr(float(density)))
        body.remove(body.find("inertial"))
    m2 = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))
    checked = 0
    for b in range(1, m.nbody):
        assert m2.body_mass[b] == pytest.approx(m.body_mass[b], rel=1e-7)
        if m.body(b).name in explicit_com:
            continue
        assert np.allclose(m2.body_ipos[b], m.body_ipos[b], atol=1e-9)
        I1, I2 = _full_inertia(m, b), _full_inertia(m2, b)
        assert np.allclose(I1, I2 + (1e-9 + 1e-6 * np.trace(I2)) * np.eye(3), rtol=1e-5, atol=1e-10)
        checked += 1
    assert checked >= 3


# --------------------------------------------------------------------------- #
# Link frames: DH frame i for link.com and explicit geometry
# --------------------------------------------------------------------------- #

ROWS = [DH(a=0.0, alpha=math.pi / 2, d=0.2, theta_offset=0.3), DH(a=-0.4, alpha=0.1, d=0.05, theta_offset=-0.5),
        DH(a=-0.3, alpha=-0.4, d=0.0, theta_offset=0.2), DH(a=0.05, alpha=math.pi / 2, d=0.12, theta_offset=0.0)]


@pytest.mark.parametrize("conv", ["dh_standard", "dh_modified"])
@pytest.mark.parametrize("slide_at", [None, 2])
def test_dh_link_frame_com_and_geometry(conv, slide_at):
    rng = np.random.default_rng(5)
    types = ["slide" if i == slide_at else "hinge" for i in range(len(ROWS))]
    coms = [rng.uniform(-0.1, 0.1, 3) for _ in ROWS]
    gpos = [rng.uniform(-0.1, 0.1, 3) for _ in ROWS]
    joints = [Joint(name=f"j{i}", type=t, dh=r,
                    limits={"lower": -0.1, "upper": 0.1} if t == "slide" else None,
                    link=Link(mass=1.0, com=list(c), geometry=[GeometryHint(shape="sphere", radius=0.02,
                                                                            pos=list(g))]))
              for i, (t, r, c, g) in enumerate(zip(types, ROWS, coms, gpos))]
    spec = Spec(name="frames", dof=len(ROWS), units=Units(angle="rad"), convention=conv, joints=joints)
    m = mujoco.MjModel.from_xml_string(build_mjcf(spec))
    d = mujoco.MjData(m)
    for _ in range(5):
        q = np.array([rng.uniform(-0.1, 0.1) if t == "slide" else rng.uniform(-2, 2) for t in types])
        d.qpos[:] = q
        mujoco.mj_kinematics(m, d)
        for i in range(len(ROWS)):
            T = dh_fk(ROWS[: i + 1], list(q[: i + 1]), conv, types[: i + 1])  # world pose of DH frame i+1
            b = m.body(f"j{i}_link").id
            assert np.allclose(d.xipos[b], T[:3, :3] @ coms[i] + T[:3, 3], atol=1e-9)
            g = m.geom(f"j{i}_link_g0").id
            assert np.allclose(d.geom_xpos[g], T[:3, :3] @ gpos[i] + T[:3, 3], atol=1e-9)


# --------------------------------------------------------------------------- #
# Reach metric: wrist_center point and the parallel-axis shoulder rule
# --------------------------------------------------------------------------- #


def _reach(tmp_path, joints, ee, reach) -> dict:
    spec = Spec(name="r", dof=len(joints), units=Units(angle="rad"), joints=joints,
                ee=EndEffector(origin=Pose(xyz=ee)), reach=reach, estimates=["joints", "ee", "reach"])
    sp, mp = tmp_path / "spec.yaml", tmp_path / "model.xml"
    dump_spec(spec, sp)
    mp.write_text(build_mjcf(spec))
    return {c.id: c for c in run_checks(mp, sp, n_reach_samples=400).checks}["reach"]


def _j(name, xyz, axis):
    return Joint(name=name, origin=Pose(xyz=xyz), axis=axis, limits={"lower": -2.5, "upper": 2.5})


def test_wrist_center_is_body_of_joint_dof_minus_2(tmp_path):
    # waist (z) then shoulder/elbow/wrist about y; wrist_center = body of joints[2] (the elbow here),
    # 0.3 m from the shoulder in every configuration
    joints = [_j("waist", [0, 0, 0.1], [0, 0, 1]), _j("shoulder", [0, 0, 0.1], [0, 1, 0]),
              _j("elbow", [0.3, 0, 0], [0, 1, 0]), _j("wrist", [0.25, 0, 0], [0, 1, 0])]
    c = _reach(tmp_path, joints, [0.1, 0, 0], {"value": 0.3, "measured_to": "wrist_center"})
    assert c.passed and c.measured == pytest.approx(0.3, abs=1e-9)
    assert "elbow_link" in c.details["point"] and "shoulder_link" in c.details["origin"]


@pytest.mark.parametrize("xyz2,axis2,expected,origin_body", [
    # parallel to joint 1 (SCARA-like): shoulder at the 1st joint (from the 2nd it would be 0.7)
    ([0.25, 0, 0], [0, 0, 1], 0.45, "j1_link"),
    # not parallel: shoulder at the 2nd joint, on the first axis (from the 1st it would be 0.224)
    ([0, 0, 0.1], [0, 1, 0], 0.20, "j2_link"),
])
def test_shoulder_rule_parallel_first_axes(tmp_path, xyz2, axis2, expected, origin_body):
    joints = [_j("j1", [0, 0, 0.4], [0, 0, 1]), _j("j2", xyz2, axis2)]
    c = _reach(tmp_path, joints, [0.2, 0, 0], {"value": expected, "measured_from": "shoulder"})
    assert c.passed, c.message
    assert c.measured == pytest.approx(expected, rel=1e-3)
    assert origin_body in c.details["origin"]
    assert ("parallel" in c.details["origin"]) == (axis2 == [0, 0, 1])
