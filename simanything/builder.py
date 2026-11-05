"""Spec -> MJCF builder (see docs/CONTRACTS.md, section 7).

The builder is deterministic: the same spec always gives the same XML, and a
spec written in mm/deg gives exactly the same XML as its m/rad equivalent.

Rules worth knowing when reading a generated model
--------------------------------------------------
Frames
    Body ``i`` (moved by joint ``i``) has the pose given by ``Spec.chain()``.
    The *link frame* that ``link.com`` and explicit geometry (``fromto``,
    ``pos``, ``rpy``) refer to is the body frame for the ``offset`` convention
    and DH frame ``i`` for the DH conventions (the frame that the DH table
    attaches to link ``i``; for ``dh_standard`` it sits at the distal end of the
    link). The base link frame is the base body frame (= DH frame 0).

Automatic geometry
    A geometry hint without ``fromto``/``pos`` is auto-placed along the link
    *segment*: from the body origin to the next body's origin (the EE site for
    the last link, joint 1's origin for the base). Capsules/cylinders span the
    segment (or are centred on it when ``half_length`` is given); boxes and
    spheres are centred halfway. A link without hints gets one auto capsule.
    A zero-length segment (coincident origins, e.g. a spherical wrist) gets a
    sphere instead of a capsule/cylinder. A base without hints gets a cylinder
    up to joint 1, or a disk just below the base origin if they coincide.

Default radius (when a hint has none), with L = segment length:
    * link mass known:   r = sqrt(m / (pi * 1500 * max(L, 0.05)))   i.e. a solid
      cylinder of "apparent density" 1500 kg/m^3 (a hollow aluminium arm);
      for a zero-length link the sphere of that density: r = (3m / (4 pi 1500))^(1/3);
    * link mass unknown: r = max(0.1 * L, 0.03 * total chain length);
    then clamped to [0.015, 0.1] m. The base uses 1.25x the first link's radius,
    clamped to [0.03, 0.15] m.

Mass and inertia
    Each body gets an explicit ``<inertial>``. A link's mass is split over its
    primitives by volume; the inertia is the exact solid inertia of each
    primitive moved to the centre of mass (``link.com`` if given, else the
    volume-weighted centroid) with the parallel-axis theorem. Unknown masses
    are volume x 1000 kg/m^3; if ``total_mass`` is given they are scaled so that
    base + links equals it.

Actuators
    One ``<position>`` actuator per joint. Gains come from a provisional model:
    with g = static gravity torque at home and M = joint-space inertia diagonal,
        kp = max(|g| / e, min(M * wn^2, effort / e_sat)),  kv = 2 sqrt(kp M)
    with e = 0.01 rad (1 mm for slides), wn = 25 rad/s, e_sat = 0.02 rad
    (2 mm). If kp would make the joint too stiff for the time step
    (kp > M * 150^2) the armature is raised (it stands in for reflected rotor
    inertia) so the explicit position loop stays stable at dt = 0.002 s.

Contact exclusions
    MuJoCo filters parent/child contacts except when the parent is welded to
    the world, so the base / first link pair is excluded explicitly. Bodies
    whose origins coincide (zero-length links) are excluded pairwise together
    with the body whose segment ends at the shared origin, and so is any pair
    of bodies whose geoms touch in *every* one of 32 sampled configurations
    (home + 31 seeded random ones): such overlaps are structural (e.g. a link
    shorter than its neighbours' radii) rather than collisions. Each
    exclusion is listed with its reason in an XML comment.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from .spec import (Chain, GeometryHint, Link, Spec, axis_angle_mat, build_chain, dh_to_offset, load_spec,
                   make_tf, mat_to_quat, quat_to_mat, rot_x, rpy_to_mat)

TIMESTEP = 0.002
DEFAULT_DENSITY = 1000.0          # kg/m^3, for links of unknown mass (before total_mass scaling)
APPARENT_DENSITY = 1500.0         # kg/m^3, only for choosing a default radius from a known mass
R_MIN, R_MAX = 0.015, 0.1
BASE_R_MIN, BASE_R_MAX = 0.03, 0.15
EPS_LEN = 1e-6                    # m; shorter segments count as zero-length
DEFAULT_DAMPING = {"hinge": 0.1, "slide": 1.0}     # N m s/rad, N s/m
DEFAULT_ARMATURE = {"hinge": 0.01, "slide": 0.01}  # kg m^2, kg
HOLD_ERROR = {"hinge": 0.01, "slide": 0.001}       # target steady-state error under gravity
SAT_ERROR = {"hinge": 0.02, "slide": 0.002}        # error at which the effort limit is reached
WN = 25.0                         # rad/s, minimum closed-loop bandwidth (if effort allows)
WN_MAX = 150.0                    # rad/s, stability cap for the explicit position loop
N_CONTACT_SAMPLES = 32

_RGBA = ["0.55 0.6 0.68 1", "0.85 0.55 0.2 1"]
_BASE_RGBA = "0.3 0.3 0.33 1"


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #


def _num(x: float, sig: int = 12) -> str:
    x = float(x)
    if not math.isfinite(x):
        raise ValueError(f"non-finite number in model: {x}")
    if abs(x) < 1e-14:
        return "0"
    s = format(x, f".{sig}g")
    return "0" if s in ("-0", "0") else s


def _vec(v, sig: int = 12) -> str:
    return " ".join(_num(x, sig) for x in v)


def _rot_z_to(d: np.ndarray) -> np.ndarray:
    """Rotation whose z axis is the unit vector ``d``."""
    d = np.asarray(d, dtype=float)
    d = d / np.linalg.norm(d)
    z = np.array([0.0, 0.0, 1.0])
    c = float(np.dot(z, d))
    if c > 1 - 1e-12:
        return np.eye(3)
    if c < -1 + 1e-12:
        return rot_x(math.pi)
    axis = np.cross(z, d)
    return axis_angle_mat(axis, math.atan2(np.linalg.norm(axis), c))


def _motion_tf(jtype: str, axis, value: float) -> np.ndarray:
    if jtype == "hinge":
        return make_tf(axis_angle_mat(np.asarray(axis, dtype=float), value))
    a = np.asarray(axis, dtype=float)
    return make_tf(None, a / np.linalg.norm(a) * value)


def _quat_attr(R: np.ndarray) -> Optional[str]:
    q = mat_to_quat(R)
    if np.allclose(q, [1, 0, 0, 0], atol=1e-12):
        return None
    return _vec(q)


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #


@dataclass
class Prim:
    """A primitive geom in its body frame. ``size`` follows MuJoCo: capsule/cylinder
    [radius, half_length], box [hx, hy, hz], sphere [radius]. Its local z axis is
    the capsule/cylinder axis."""

    kind: str
    size: list[float]
    pos: np.ndarray
    R: np.ndarray = field(default_factory=lambda: np.eye(3))

    def volume(self) -> float:
        if self.kind == "sphere":
            return 4.0 / 3.0 * math.pi * self.size[0] ** 3
        if self.kind == "box":
            return 8.0 * self.size[0] * self.size[1] * self.size[2]
        r, h = self.size
        v = math.pi * r * r * 2 * h
        if self.kind == "capsule":
            v += 4.0 / 3.0 * math.pi * r ** 3
        return v

    def inertia_local(self, m: float) -> np.ndarray:
        """Inertia of a solid primitive of mass m about its centre, in its own frame."""
        if self.kind == "sphere":
            return np.eye(3) * 0.4 * m * self.size[0] ** 2
        if self.kind == "box":
            a, b, c = self.size
            return np.diag([m * (b * b + c * c) / 3, m * (a * a + c * c) / 3, m * (a * a + b * b) / 3])
        r, h = self.size
        if self.kind == "cylinder":
            return np.diag([m * (3 * r * r + 4 * h * h) / 12] * 2 + [0.5 * m * r * r])
        # capsule: cylinder (length 2h) + two hemispheres, mass split by volume
        vc, vs = math.pi * r * r * 2 * h, 4.0 / 3.0 * math.pi * r ** 3
        mc, ms = m * vc / (vc + vs), m * vs / (vc + vs)
        izz = 0.5 * mc * r * r + 0.4 * ms * r * r
        ixx = mc * (3 * r * r + 4 * h * h) / 12 + ms * (0.4 * r * r + h * h + 0.75 * h * r)
        return np.diag([ixx, ixx, izz])


@dataclass
class BodyPlan:
    name: str
    pos: np.ndarray
    quat: np.ndarray
    link: Link
    prims: list[Prim]
    joint_index: Optional[int]          # None for the base
    segment: np.ndarray                 # body-frame end point of this body's segment
    frame: np.ndarray = field(default_factory=lambda: np.eye(4))  # body -> link frame
    mass: float = 0.0
    mass_note: str = ""
    com: np.ndarray = field(default_factory=lambda: np.zeros(3))
    inertia: np.ndarray = field(default_factory=lambda: np.eye(3))


# --------------------------------------------------------------------------- #
# Planning
# --------------------------------------------------------------------------- #


def _link_frames(si: Spec, chain: Chain) -> list[np.ndarray]:
    """Transform from each body frame to its link frame (see module docstring)."""
    n = len(si.joints)
    if si.convention == "offset":
        return [np.eye(4) for _ in range(n)]
    types = [j.type for j in si.joints]
    _, offs, _ = dh_to_offset([j.dh for j in si.joints], types, si.convention)  # type: ignore[misc]
    frames = []
    for i, cj in enumerate(chain.joints):
        M = _motion_tf(cj.type, cj.axis, offs[i])
        if si.convention == "dh_modified":
            frames.append(M)
        elif i + 1 < n:  # dh_standard: DH frame i is where body i+1 sits (offset already folded in)
            frames.append(chain.joints[i + 1].parent_tf())
        else:
            ee_local = make_tf(rpy_to_mat(si.ee.origin.rpy), si.ee.origin.xyz)
            ee_tf = make_tf(quat_to_mat(np.array(chain.ee_quat)), chain.ee_pos)
            frames.append(ee_tf @ np.linalg.inv(ee_local))
    return frames


def _default_radius(L: float, mass: Optional[float], total_len: float) -> float:
    if mass is not None:
        if L < EPS_LEN:
            r = (3 * mass / (4 * math.pi * APPARENT_DENSITY)) ** (1 / 3)
        else:
            r = math.sqrt(mass / (math.pi * APPARENT_DENSITY * max(L, 0.05)))
    else:
        r = max(0.1 * L, 0.03 * total_len)
    return min(max(r, R_MIN), R_MAX)


def _prim_from_hint(g: GeometryHint, seg: np.ndarray, Lf: np.ndarray, r_default: float) -> Prim:
    """Turn one geometry hint into a body-frame primitive. ``seg`` is the segment end
    point (body frame), ``Lf`` the body->link frame transform."""
    Lr, Lp = Lf[:3, :3], Lf[:3, 3]
    L = float(np.linalg.norm(seg))
    r = g.radius if g.radius is not None else r_default
    to_body = lambda p: Lr @ np.asarray(p, dtype=float) + Lp  # noqa: E731

    if g.fromto is not None:
        a, b = to_body(g.fromto[:3]), to_body(g.fromto[3:])
        d = b - a
        centre, length = 0.5 * (a + b), float(np.linalg.norm(d))
        R = _rot_z_to(d) if length > EPS_LEN else Lr
        if g.shape in ("capsule", "cylinder"):
            if length <= EPS_LEN:
                return Prim("sphere", [r], centre)
            return Prim(g.shape, [r, 0.5 * length], centre, R)
        if g.shape == "sphere":
            return Prim("sphere", [r], centre)
        size = g.size if g.size is not None else [r, r, max(0.5 * length, r)]
        return Prim("box", list(size), centre, R)

    along_segment = L > EPS_LEN and g.rpy is None
    centre = to_body(g.pos) if g.pos is not None else 0.5 * seg
    if g.rpy is not None:
        R = Lr @ rpy_to_mat(g.rpy)
    elif along_segment:
        R = _rot_z_to(seg)
    else:
        R = Lr
    if g.shape == "sphere":
        return Prim("sphere", [r], centre)
    if g.shape == "box":
        if g.size is not None:
            return Prim("box", list(g.size), centre, Lr @ rpy_to_mat(g.rpy) if g.rpy is not None else Lr)
        return Prim("box", [r, r, max(0.5 * L, r)], centre, R)
    # capsule / cylinder
    if g.half_length is not None:
        return Prim(g.shape, [r, g.half_length], centre, R)
    if L <= EPS_LEN:
        return Prim("sphere", [r], centre)  # zero-length link: small sphere at the shared origin
    return Prim(g.shape, [r, 0.5 * L], centre, R)


def _plan_bodies(si: Spec, chain: Chain) -> list[BodyPlan]:
    n = len(si.joints)
    frames = _link_frames(si, chain)
    segs = [np.array(chain.joints[i + 1].pos) if i + 1 < n else np.array(chain.ee_pos) for i in range(n)]
    total_len = max(sum(float(np.linalg.norm(s)) for s in segs), 0.1)

    names = []
    bodies: list[BodyPlan] = []
    for i, (j, cj) in enumerate(zip(si.joints, chain.joints)):
        name = j.link.name or f"{j.name}_link"
        L = float(np.linalg.norm(segs[i]))
        r0 = _default_radius(L, j.link.mass, total_len)
        hints = j.link.geometry or [GeometryHint(shape="capsule")]
        prims = [_prim_from_hint(g, segs[i], frames[i], r0) for g in hints]
        bodies.append(BodyPlan(name=name, pos=np.array(cj.pos), quat=np.array(cj.quat), link=j.link,
                               prims=prims, joint_index=i, segment=segs[i]))
        names.append(name)

    # base
    seg0 = np.array(chain.joints[0].pos)
    first_r = bodies[0].prims[0].size[0] if bodies[0].prims[0].kind != "box" else min(bodies[0].prims[0].size)
    rb = min(max(1.25 * first_r, BASE_R_MIN), BASE_R_MAX)
    if si.base.link.geometry:
        base_prims = [_prim_from_hint(g, seg0, np.eye(4), rb) for g in si.base.link.geometry]
    elif np.linalg.norm(seg0) > EPS_LEN:
        base_prims = [_prim_from_hint(GeometryHint(shape="cylinder", radius=rb), seg0, np.eye(4), rb)]
    else:
        hh = 0.25 * rb
        base_prims = [Prim("cylinder", [rb, hh], np.array([0.0, 0.0, -hh]))]
    base = BodyPlan(name="base", pos=np.array(chain.base_pos), quat=np.array(chain.base_quat),
                    link=si.base.link, prims=base_prims, joint_index=None, segment=seg0)

    all_names = ["base"] + names
    dup = sorted({x for x in all_names if all_names.count(x) > 1})
    if dup:
        raise ValueError(f"body names must be unique (link names / '<joint>_link' / 'base'): {dup}")

    for b, F in zip(bodies, frames):
        b.frame = F
    return [base] + bodies


def _assign_mass_inertia(si: Spec, bodies: list[BodyPlan]) -> list[str]:
    notes: list[str] = []
    known = sum(b.link.mass for b in bodies if b.link.mass is not None)
    unknown = [b for b in bodies if b.link.mass is None]
    vol_mass = {id(b): DEFAULT_DENSITY * sum(p.volume() for p in b.prims) for b in unknown}
    scale = 1.0
    how = f"volume x {DEFAULT_DENSITY:g} kg/m^3"
    if unknown and si.total_mass is not None:
        rest = si.total_mass - known
        tot_vol_mass = sum(vol_mass.values())
        if rest > 0:
            scale = rest / tot_vol_mass
            how += f", scaled x{_num(scale, 4)} to match total_mass"
        else:
            scale = 0.01 * si.total_mass / tot_vol_mass / len(unknown)
            how += " (WARNING: known link masses already reach total_mass; set to 1% of it)"
            notes.append("known link masses already reach total_mass; unknown links get a token mass")
    for b in bodies:
        if b.link.mass is not None:
            b.mass, b.mass_note = float(b.link.mass), "mass from spec"
        else:
            b.mass, b.mass_note = vol_mass[id(b)] * scale, f"mass estimated: {how}"

        vols = np.array([p.volume() for p in b.prims])
        masses = b.mass * vols / vols.sum()
        if b.link.com is not None:
            F = b.frame
            b.com = F[:3, :3] @ np.asarray(b.link.com, dtype=float) + F[:3, 3]
        else:
            b.com = sum(m * p.pos for m, p in zip(masses, b.prims)) / b.mass
        I = np.zeros((3, 3))
        for m, p in zip(masses, b.prims):
            d = p.pos - b.com
            I += p.R @ p.inertia_local(m) @ p.R.T + m * (float(d @ d) * np.eye(3) - np.outer(d, d))
        I = 0.5 * (I + I.T)
        I += np.eye(3) * (1e-9 + 1e-6 * np.trace(I))  # keeps it strictly positive definite
        b.inertia = I
    return notes


def _coincident_excludes(bodies: list[BodyPlan]) -> list[tuple[str, str, str]]:
    """Body i+1 coincides with body i when its position in body i is zero. For a
    run of coincident bodies, exclude all non-adjacent pairs among the run plus
    the body whose segment ends at the shared origin."""
    # MuJoCo's parent/child filter does not apply when the parent is welded to the
    # world (as the fixed base is), so the base / first link pair is excluded explicitly.
    out = [(bodies[0].name, bodies[1].name, "parent/child; MuJoCo does not filter a world-fixed parent")]
    n = len(bodies)  # bodies[0] is the base, bodies[k] has parent bodies[k-1]
    k = 1
    while k < n:
        if np.linalg.norm(bodies[k].pos) < EPS_LEN:
            head = k - 1
            end = k
            while end + 1 < n and np.linalg.norm(bodies[end + 1].pos) < EPS_LEN:
                end += 1
            group = list(range(max(head - 1, 0), end + 1))
            for a in group:
                for b in group:
                    if b > a + 1 and not (a == 0 and b == 1):
                        out.append((bodies[a].name, bodies[b].name, "origins coincide"))
            k = end + 1
        else:
            k += 1
    return out


# --------------------------------------------------------------------------- #
# XML
# --------------------------------------------------------------------------- #


@dataclass
class _Dyn:
    damping: list[float]
    armature: list[float]
    kp: Optional[list[float]] = None
    kv: Optional[list[float]] = None


def _sanitize_comment(s: str) -> str:
    return s.replace("--", "- -")


def _to_xml(spec: Spec, si: Spec, chain: Chain, bodies: list[BodyPlan], dyn: _Dyn,
            excludes: list[tuple[str, str, str]], notes: list[str], final: bool) -> str:
    root = ET.Element("mujoco", model=si.name)
    root.append(ET.Comment(_sanitize_comment(
        f" Generated by sim-anything from spec '{spec.name}'. Do not edit by hand: edit the spec and rebuild. ")))
    if final and spec.estimates:
        root.append(ET.Comment(" Many numbers are estimates; see the spec's sources/estimates. "))
    for note in notes:
        root.append(ET.Comment(_sanitize_comment(f" NOTE: {note} ")))
    ET.SubElement(root, "compiler", angle="radian", autolimits="true", inertiafromgeom="false")
    ET.SubElement(root, "option", timestep=_num(TIMESTEP), integrator="implicitfast", gravity="0 0 -9.81")
    default = ET.SubElement(root, "default")
    ET.SubElement(default, "geom", rgba=_RGBA[0])
    ET.SubElement(default, "site", rgba="1 0.2 0.2 1", size="0.01")

    world = ET.SubElement(root, "worldbody")
    parent = world
    n = len(si.joints)
    for k, b in enumerate(bodies):
        attrs = {"name": b.name}
        if np.linalg.norm(b.pos) > 0:
            attrs["pos"] = _vec(b.pos)
        q = _quat_attr(quat_to_mat(b.quat))
        if q:
            attrs["quat"] = q
        el = ET.SubElement(parent, "body", attrs)
        el.append(ET.Comment(_sanitize_comment(f" {b.mass_note} ")))
        inert = {"pos": _vec(b.com), "mass": _num(b.mass, 8)}
        I = b.inertia
        if max(abs(I[0, 1]), abs(I[0, 2]), abs(I[1, 2])) <= 1e-12 * np.trace(I):
            inert["diaginertia"] = _vec(np.diag(I), 8)
        else:
            inert["fullinertia"] = _vec([I[0, 0], I[1, 1], I[2, 2], I[0, 1], I[0, 2], I[1, 2]], 8)
        ET.SubElement(el, "inertial", inert)
        if b.joint_index is not None:
            i = b.joint_index
            j, cj = si.joints[i], chain.joints[i]
            ja = {"name": j.name, "type": j.type, "axis": _vec(cj.axis)}
            if j.limits is not None:
                ja["range"] = _vec([j.limits.lower, j.limits.upper])
            ja["damping"] = _num(dyn.damping[i], 6)
            ja["armature"] = _num(dyn.armature[i], 6)
            ET.SubElement(el, "joint", ja)
        rgba = _BASE_RGBA if b.joint_index is None else _RGBA[k % 2]
        for gi, p in enumerate(b.prims):
            ga = {"name": f"{b.name}_g{gi}", "type": p.kind}
            if p.kind in ("capsule", "cylinder"):
                ax = p.R[:, 2] * p.size[1]
                ga["fromto"] = _vec(np.concatenate([p.pos - ax, p.pos + ax]))
                ga["size"] = _num(p.size[0])
            else:
                ga["size"] = _vec(p.size)
                ga["pos"] = _vec(p.pos)
                if p.kind == "box":
                    qa = _quat_attr(p.R)
                    if qa:
                        ga["quat"] = qa
            if rgba != _RGBA[0]:
                ga["rgba"] = rgba
            ET.SubElement(el, "geom", ga)
        if b.joint_index == n - 1:
            sa = {"name": si.ee.name, "pos": _vec(chain.ee_pos)}
            q = _quat_attr(quat_to_mat(np.array(chain.ee_quat)))
            if q:
                sa["quat"] = q
            ET.SubElement(el, "site", sa)
        parent = el

    if excludes:
        contact = ET.SubElement(root, "contact")
        contact.append(ET.Comment(
            " Excluded pairs (besides MuJoCo's parent/child filter): the world-fixed base and its child, "
            "bodies whose origins coincide (zero-length links, e.g. a spherical wrist) and the body whose "
            "segment ends there, and bodies whose geoms overlap in every sampled configuration (a "
            "structural overlap at a joint, not a collision). "))
        for a, b, why in excludes:
            contact.append(ET.Comment(_sanitize_comment(f" {a} / {b}: {why} ")))
            ET.SubElement(contact, "exclude", body1=a, body2=b)

    if final:
        act = ET.SubElement(root, "actuator")
        act.append(ET.Comment(" Position servos; kp holds the home pose under gravity (see builder.py). "))
        for i, j in enumerate(si.joints):
            aa = {"name": f"{j.name}_act", "joint": j.name, "kp": _num(dyn.kp[i], 4),  # type: ignore[index]
                  "kv": _num(dyn.kv[i], 4)}  # type: ignore[index]
            if j.limits is not None:
                aa["ctrlrange"] = _vec([j.limits.lower, j.limits.upper])
            if j.effort_limit is not None:
                aa["forcerange"] = _vec([-j.effort_limit, j.effort_limit])
            ET.SubElement(act, "position", aa)
        kf = ET.SubElement(root, "keyframe")
        home = [j.home for j in si.joints]
        ET.SubElement(kf, "key", name="home", qpos=_vec(home), ctrl=_vec(home))

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode") + "\n"


# --------------------------------------------------------------------------- #
# Provisional-model analysis
# --------------------------------------------------------------------------- #


def _sample_configs(si: Spec, n: int) -> list[np.ndarray]:
    rng = np.random.default_rng(0)
    home = np.array([j.home for j in si.joints], dtype=float)
    lo = np.array([j.limits.lower if j.limits else (-math.pi if j.type == "hinge" else -0.1) for j in si.joints])
    hi = np.array([j.limits.upper if j.limits else (math.pi if j.type == "hinge" else 0.1) for j in si.joints])
    return [home] + [rng.uniform(lo, hi) for _ in range(n - 1)]


def _structural_excludes(model, si: Spec, already: set[frozenset]) -> list[tuple[str, str, str]]:
    import mujoco

    data = mujoco.MjData(model)
    common: Optional[set[frozenset]] = None
    for q in _sample_configs(si, N_CONTACT_SAMPLES):
        data.qpos[:] = q
        mujoco.mj_forward(model, data)
        pairs = set()
        for c in data.contact[: data.ncon]:
            if c.dist < 0:
                b1 = model.body(model.geom_bodyid[c.geom1]).name
                b2 = model.body(model.geom_bodyid[c.geom2]).name
                pairs.add(frozenset((b1, b2)))
        common = pairs if common is None else common & pairs
        if not common:
            return []
    order = {model.body(i).name: i for i in range(model.nbody)}
    out = []
    for pr in sorted(common or [], key=lambda p: sorted(order[x] for x in p)):
        if pr in already:
            continue
        a, b = sorted(pr, key=lambda x: order[x])
        out.append((a, b, f"overlap in all {N_CONTACT_SAMPLES} sampled configurations"))
    return out


def _gains(model, si: Spec, dyn: _Dyn) -> None:
    import mujoco

    data = mujoco.MjData(model)
    data.qpos[:] = [j.home for j in si.joints]
    mujoco.mj_forward(model, data)
    g = np.array(data.qfrc_bias)
    Mdiag = np.array([data.qM[model.dof_Madr[i]] for i in range(model.nv)])
    kp, kv = [], []
    for i, j in enumerate(si.joints):
        t = j.type
        M = float(Mdiag[i])
        kp_hold = abs(g[i]) / HOLD_ERROR[t]
        kp_bw = M * WN ** 2
        if j.effort_limit is not None:
            kp_bw = min(kp_bw, j.effort_limit / SAT_ERROR[t])
        k = max(kp_hold, kp_bw, 1e-3)
        cap = M * WN_MAX ** 2
        if k > cap:  # too stiff for the time step: add reflected-rotor-like armature
            extra = k / WN_MAX ** 2 - M
            dyn.armature[i] += extra
            M += extra
        kp.append(k)
        kv.append(2.0 * math.sqrt(k * M))
    dyn.kp, dyn.kv = kp, kv


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def build_mjcf(spec: Spec) -> str:
    """Build the MJCF XML string for ``spec`` (CONTRACTS section 7)."""
    import mujoco

    si = spec.to_si()
    chain = build_chain(si)
    bodies = _plan_bodies(si, chain)
    notes = _assign_mass_inertia(si, bodies)
    excludes = _coincident_excludes(bodies)
    dyn = _Dyn(damping=[j.damping if j.damping is not None else DEFAULT_DAMPING[j.type] for j in si.joints],
               armature=[j.armature if j.armature is not None else DEFAULT_ARMATURE[j.type] for j in si.joints])

    provisional = _to_xml(spec, si, chain, bodies, dyn, excludes, notes, final=False)
    try:
        model = mujoco.MjModel.from_xml_string(provisional)
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"generated MJCF does not compile: {e}") from e
    excludes = excludes + _structural_excludes(model, si, {frozenset(e[:2]) for e in excludes})
    _gains(model, si, dyn)
    return _to_xml(spec, si, chain, bodies, dyn, excludes, notes, final=True)


def build_file(spec_path: str | Path, out_path: str | Path) -> Path:
    """Load ``spec_path``, build it and write the MJCF to ``out_path``."""
    spec = load_spec(spec_path)
    xml = build_mjcf(spec)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(xml, encoding="utf-8")
    return out


__all__ = ["build_mjcf", "build_file"]
