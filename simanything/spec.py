"""The sim-anything robot specification schema (spec.yaml).

A spec describes a serial robot arm from public information. The LLM agent fills
it in; deterministic code (builder.py) turns it into MJCF.

Conventions
-----------
* Units are declared once in ``units`` (length: m|mm, angle: deg|rad). Every
  length / angle in the file uses those units. ``Spec.to_si()`` returns a copy in
  metres and radians; all downstream code works on the SI copy.
* Masses are kg, torques N*m (forces N), linear velocities (length unit)/s,
  angular velocities (angle unit)/s. ``damping`` and ``armature`` are always SI
  and not converted: damping N*m*s/rad (hinge) or N*s/m (slide), armature
  kg*m^2 (hinge) or kg (slide).
* Rotations given as ``rpy`` are fixed-axis roll/pitch/yaw (URDF convention):
  R = Rz(yaw) @ Ry(pitch) @ Rx(roll).
* The kinematic chain is given in exactly one ``convention``:
    - ``offset``      : every joint has ``origin`` (xyz + rpy of the joint frame
                        relative to the parent link frame) and ``axis`` (in the
                        joint frame). Same idea as URDF.
    - ``dh_standard`` : classic (distal) DH. Joint i rotates about z_{i-1};
                        T_{i-1,i} = Rz(theta_i) Tz(d_i) Tx(a_i) Rx(alpha_i).
    - ``dh_modified`` : Craig's modified (proximal) DH. Joint i rotates about z_i;
                        T_{i-1,i} = Rx(alpha_{i-1}) Tx(a_{i-1}) Rz(theta_i) Tz(d_i).
                        The values stored on joint i are (a_{i-1}, alpha_{i-1},
                        d_i, theta_offset_i), i.e. exactly one row of the table.
  For DH conventions a revolute joint's variable is theta (q + theta_offset); a
  prismatic joint's variable is d (q + d).
* "Link frame" (used by ``link.com``, explicit geometry ``pos``/``fromto``):
  for ``offset`` it is the child frame of the joint (the joint's own frame); for
  DH conventions link i's frame is DH frame i (for ``dh_standard`` that is at
  the distal end of link i, as in published DH dynamics tables).
* ``ee`` is a fixed offset from the frame after the last joint (frame n for DH,
  the last link frame for ``offset``) to the end-effector site (tool flange).
* ``sources`` maps a field path to the http(s) URL that supports it, or to
  ``doc:<relative path>`` for a local document (e.g. a sources.md quoting the
  values). Every key of ``sources``/``estimates`` must name a field of the spec
  (the checker reports keys that match nothing as likely typos). ``estimates`` lists
  field paths whose values were estimated rather than read from a source.
  A path covers itself and everything under it, e.g. ``joints[2]`` covers
  ``joints[2].dh.a``; ``joints[*].limits`` covers the limits of every joint.
  Every number in the spec must be covered by ``sources`` or ``estimates``.
"""

from __future__ import annotations

import difflib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterator, Literal, Optional

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = 1

Vec3 = list[float]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #


class Units(_Base):
    length: Literal["m", "mm"] = "m"
    angle: Literal["deg", "rad"] = "deg"


class Pose(_Base):
    xyz: Vec3 = Field(default_factory=lambda: [0.0, 0.0, 0.0], min_length=3, max_length=3)
    rpy: Vec3 = Field(default_factory=lambda: [0.0, 0.0, 0.0], min_length=3, max_length=3)


class DH(_Base):
    """One row of a DH table. See module docstring for the two conventions."""

    a: float = 0.0
    alpha: float = 0.0
    d: float = 0.0
    theta_offset: float = 0.0


class Limits(_Base):
    lower: float
    upper: float

    @model_validator(mode="after")
    def _ordered(self) -> "Limits":
        if not self.lower < self.upper:
            raise ValueError(f"limits.lower ({self.lower}) must be < limits.upper ({self.upper})")
        return self


class GeometryHint(_Base):
    """Primitive collision/visual geometry for a link.

    If neither ``fromto`` nor ``pos`` is given, the builder places the primitive
    automatically: a capsule/cylinder spans from the link frame origin to the
    next joint's origin (or the EE site for the last link); a box/sphere is
    centred halfway between them.
    """

    shape: Literal["capsule", "cylinder", "box", "sphere"] = "capsule"
    radius: Optional[float] = Field(default=None, gt=0, description="capsule/cylinder/sphere radius")
    half_length: Optional[float] = Field(default=None, gt=0, description="capsule/cylinder half length")
    size: Optional[Vec3] = Field(default=None, min_length=3, max_length=3,
                                 description="box half sizes [x, y, z], all > 0")
    fromto: Optional[list[float]] = Field(default=None, min_length=6, max_length=6,
                                          description="explicit endpoints in the link frame")
    pos: Optional[Vec3] = Field(default=None, min_length=3, max_length=3)
    rpy: Optional[Vec3] = Field(default=None, min_length=3, max_length=3)

    @field_validator("size")
    @classmethod
    def _positive_size(cls, v: Optional[Vec3]) -> Optional[Vec3]:
        if v is not None and not all(float(x) > 0 for x in v):
            raise ValueError(f"size must be 3 positive half sizes, got {v}")
        return v


class Link(_Base):
    name: Optional[str] = None
    mass: Optional[float] = Field(default=None, gt=0)
    com: Optional[Vec3] = Field(default=None, description="centre of mass in the link frame")
    geometry: list[GeometryHint] = Field(default_factory=list)


class Joint(_Base):
    name: str
    type: Literal["hinge", "slide"] = "hinge"
    # offset convention
    origin: Optional[Pose] = None
    axis: Vec3 = Field(default_factory=lambda: [0.0, 0.0, 1.0], min_length=3, max_length=3)
    # DH conventions
    dh: Optional[DH] = None
    limits: Optional[Limits] = None
    velocity_limit: Optional[float] = Field(default=None, gt=0,
                                            description="(angle unit)/s for hinges, (length unit)/s for slides")
    effort_limit: Optional[float] = Field(default=None, gt=0, description="N*m for hinges, N for slides")
    damping: Optional[float] = Field(default=None, ge=0,
                                     description="always SI, not affected by `units`: N*m*s/rad for hinges, "
                                                 "N*s/m for slides")
    armature: Optional[float] = Field(default=None, ge=0,
                                      description="reflected rotor inertia, always SI: kg*m^2 for hinges, kg for "
                                                  "slides")
    home: float = Field(default=0.0, description="home position, within limits when limits are given")
    link: Link = Field(default_factory=Link, description="the child link moved by this joint")

    @field_validator("axis")
    @classmethod
    def _nonzero_axis(cls, v: Vec3) -> Vec3:
        if float(np.linalg.norm(v)) < 1e-9:
            raise ValueError("axis must be non-zero")
        return v

    @model_validator(mode="after")
    def _home_within_limits(self) -> "Joint":
        if self.limits is not None and not self.limits.lower <= self.home <= self.limits.upper:
            raise ValueError(f"joint '{self.name}': home ({self.home}) must lie within limits "
                             f"[{self.limits.lower}, {self.limits.upper}]")
        return self


class EndEffector(_Base):
    name: str = "ee_site"
    origin: Pose = Field(default_factory=Pose)


class Base(_Base):
    origin: Pose = Field(default_factory=Pose, description="pose of the robot base in the world")
    link: Link = Field(default_factory=Link, description="the fixed base link")


class Reach(_Base):
    """Rated reach and how it is measured (docs/CONTRACTS.md section 4). ``wrist_center`` is the
    origin of the body of joint ``dof-2`` (0-based); an arm with fewer than 3 joints has no wrist,
    so it falls back to the EE site."""

    value: float = Field(gt=0)
    measured_from: Literal["shoulder", "base_origin", "base_axis_horizontal"] = "shoulder"
    measured_to: Literal["ee_site", "wrist_center"] = "ee_site"


class DrawingDim(_Base):
    """A dimension read off a published drawing of the arm at a stated pose (docs/CONTRACTS.md section 4,
    check ``drawing``): ``height`` = the point's height above the base frame origin (along base z),
    ``horizontal`` = its distance from the first joint's axis. Catches misread table rows that leave
    the spec self-consistent."""

    measure: Literal["height", "horizontal"]
    value: float = Field(description="length unit")
    point: Literal["ee_site", "wrist_center"] = "ee_site"
    q: Optional[list[float]] = Field(default=None, description="joint values of the drawn pose (spec units); "
                                                               "omitted = all zero")
    tolerance: Optional[float] = Field(default=None, gt=0, description="length unit; default 2 mm")


class Spec(_Base):
    schema_version: int = SCHEMA_VERSION
    name: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    description: Optional[str] = None
    dof: int = Field(ge=1)
    units: Units = Field(default_factory=Units)
    convention: Literal["offset", "dh_standard", "dh_modified"] = "offset"
    base: Base = Field(default_factory=Base)
    joints: list[Joint]
    ee: EndEffector = Field(default_factory=EndEffector)
    total_mass: Optional[float] = Field(default=None, gt=0)
    payload: Optional[float] = Field(default=None, ge=0)
    reach: Optional[Reach] = None
    drawing: list[DrawingDim] = Field(default_factory=list)
    repeatability: Optional[float] = Field(default=None, gt=0)
    sources: dict[str, str] = Field(default_factory=dict)
    estimates: list[str] = Field(default_factory=list)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _consistent(self) -> "Spec":
        if self.dof != len(self.joints):
            raise ValueError(f"dof={self.dof} but {len(self.joints)} joints are listed")
        names = [j.name for j in self.joints]
        if len(set(names)) != len(names):
            raise ValueError(f"joint names must be unique: {names}")
        for i, j in enumerate(self.joints):
            if self.convention == "offset":
                if j.dh is not None:
                    raise ValueError(f"joints[{i}] ({j.name}): convention is 'offset' but 'dh' is set")
                if j.origin is None:
                    raise ValueError(f"joints[{i}] ({j.name}): convention 'offset' requires 'origin'")
            else:
                if j.dh is None:
                    raise ValueError(f"joints[{i}] ({j.name}): convention '{self.convention}' requires 'dh'")
                if j.origin is not None:
                    raise ValueError(f"joints[{i}] ({j.name}): 'origin' is only for convention 'offset'")
                if [float(x) for x in j.axis] != [0.0, 0.0, 1.0]:
                    raise ValueError(f"joints[{i}] ({j.name}): DH joints always move along/about local z; "
                                     "remove 'axis' or encode a reversed direction with the DH parameters")
        for i, dim in enumerate(self.drawing):
            if dim.q is not None and len(dim.q) != self.dof:
                raise ValueError(f"drawing[{i}].q has {len(dim.q)} values for {self.dof} joints")
        for key in list(self.sources) + list(self.estimates):
            _parse_path(key)  # raises on malformed paths
        return self

    # ------------------------------------------------------------------ #
    def to_si(self) -> "Spec":
        """Return a deep copy with lengths in metres and angles in radians."""
        return _to_si(self)

    def chain(self) -> "Chain":
        """The kinematic chain in SI units, converted to the offset form."""
        return build_chain(self)


# --------------------------------------------------------------------------- #
# IO
# --------------------------------------------------------------------------- #


def load_spec(path: str | Path) -> Spec:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at top level")
    return Spec.model_validate(data)


def dump_spec(spec: Spec, path: str | Path) -> None:
    data = spec.model_dump(mode="json", exclude_none=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def json_schema() -> dict[str, Any]:
    schema = Spec.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "sim-anything robot spec"
    return schema


def write_json_schema(path: str | Path) -> None:
    Path(path).write_text(json.dumps(json_schema(), indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Unit conversion
# --------------------------------------------------------------------------- #


def _to_si(spec: Spec) -> Spec:
    L = 0.001 if spec.units.length == "mm" else 1.0
    A = math.pi / 180.0 if spec.units.angle == "deg" else 1.0
    s = spec.model_copy(deep=True)

    def pose(p: Pose) -> None:
        p.xyz = [v * L for v in p.xyz]
        p.rpy = [v * A for v in p.rpy]

    def link(lk: Link) -> None:
        if lk.com is not None:
            lk.com = [v * L for v in lk.com]
        for g in lk.geometry:
            if g.radius is not None:
                g.radius *= L
            if g.half_length is not None:
                g.half_length *= L
            if g.size is not None:
                g.size = [v * L for v in g.size]
            if g.fromto is not None:
                g.fromto = [v * L for v in g.fromto]
            if g.pos is not None:
                g.pos = [v * L for v in g.pos]
            if g.rpy is not None:
                g.rpy = [v * A for v in g.rpy]

    pose(s.base.origin)
    link(s.base.link)
    for j in s.joints:
        q = A if j.type == "hinge" else L  # unit of the joint variable
        if j.origin is not None:
            pose(j.origin)
        if j.dh is not None:
            j.dh.a *= L
            j.dh.d *= L
            j.dh.alpha *= A
            j.dh.theta_offset *= A
        if j.limits is not None:
            j.limits = Limits(lower=j.limits.lower * q, upper=j.limits.upper * q)
        if j.velocity_limit is not None:
            j.velocity_limit *= q
        j.home *= q
        link(j.link)
    pose(s.ee.origin)
    if s.reach is not None:
        s.reach.value *= L
    for dim in s.drawing:
        dim.value *= L
        if dim.tolerance is not None:
            dim.tolerance *= L
        if dim.q is not None:
            dim.q = [v * (A if j.type == "hinge" else L) for v, j in zip(dim.q, s.joints)]
    if s.repeatability is not None:
        s.repeatability *= L
    s.units = Units(length="m", angle="rad")
    return s


# --------------------------------------------------------------------------- #
# Rotation helpers (rotation matrices; quaternions are MuJoCo order w, x, y, z)
# --------------------------------------------------------------------------- #


def rot_x(t: float) -> np.ndarray:
    c, s = math.cos(t), math.sin(t)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=float)


def rot_y(t: float) -> np.ndarray:
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=float)


def rot_z(t: float) -> np.ndarray:
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)


def rpy_to_mat(rpy: Vec3) -> np.ndarray:
    r, p, y = rpy
    return rot_z(y) @ rot_y(p) @ rot_x(r)


def mat_to_quat(R: np.ndarray) -> np.ndarray:
    """Rotation matrix -> unit quaternion (w, x, y, z), w >= 0."""
    R = np.asarray(R, dtype=float)
    tr = R[0, 0] + R[1, 1] + R[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = [0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s]
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        q = [(R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s]
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        q = [(R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s]
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        q = [(R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s]
    q = np.array(q, dtype=float)
    q /= np.linalg.norm(q)
    if q[0] < 0:
        q = -q
    return q


def quat_to_mat(q: np.ndarray) -> np.ndarray:
    w, x, y, z = np.asarray(q, dtype=float) / np.linalg.norm(q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def make_tf(R: np.ndarray | None = None, p: np.ndarray | list | None = None) -> np.ndarray:
    T = np.eye(4)
    if R is not None:
        T[:3, :3] = R
    if p is not None:
        T[:3, 3] = p
    return T


def pose_to_tf(p: Pose) -> np.ndarray:
    return make_tf(rpy_to_mat(p.rpy), p.xyz)


def axis_angle_mat(axis: np.ndarray, angle: float) -> np.ndarray:
    a = np.asarray(axis, dtype=float)
    a = a / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(angle) * K + (1 - math.cos(angle)) * (K @ K)


# --------------------------------------------------------------------------- #
# Kinematic chain in offset form (SI) + DH converter + numpy FK
# --------------------------------------------------------------------------- #


class ChainJoint(BaseModel):
    """One body of the MJCF chain: its pose in the parent body, and its joint.

    The joint sits at the body origin; ``axis`` is in the body frame. For a hinge
    the joint value q rotates about the axis; for a slide it translates along it.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    type: Literal["hinge", "slide"]
    pos: list[float]
    quat: list[float]  # w x y z
    axis: list[float]

    def parent_tf(self) -> np.ndarray:
        return make_tf(quat_to_mat(np.array(self.quat)), self.pos)


class Chain(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_pos: list[float]
    base_quat: list[float]
    joints: list[ChainJoint]
    ee_pos: list[float]  # in the last body frame
    ee_quat: list[float]

    def fk(self, q: np.ndarray | list[float], upto: int | None = None) -> np.ndarray:
        """4x4 world pose of the EE site (or of body ``upto`` if given)."""
        q = np.asarray(q, dtype=float)
        T = make_tf(quat_to_mat(np.array(self.base_quat)), self.base_pos)
        for i, j in enumerate(self.joints):
            T = T @ j.parent_tf()
            if upto is not None and i == upto:
                return T
            T = T @ motion_tf(j.type, j.axis, q[i])
        return T @ make_tf(quat_to_mat(np.array(self.ee_quat)), self.ee_pos)


def _tf_to_pos_quat(T: np.ndarray) -> tuple[list[float], list[float]]:
    pos = [float(x) for x in T[:3, 3]]
    pos = [0.0 if abs(x) < 1e-12 else x for x in pos]
    quat = [float(x) for x in mat_to_quat(T[:3, :3])]
    quat = [0.0 if abs(x) < 1e-12 else x for x in quat]
    return pos, quat


def dh_to_offset(rows: list[DH], types: list[str], convention: str
                 ) -> tuple[list[np.ndarray], list[float], np.ndarray]:
    """Convert DH rows (SI) to body transforms.

    Returns (body_tfs, qpos_offsets, tail_tf):
      * body_tfs[i]: pose of body i (whose joint moves about/along local z) in body i-1
        (body -1 is the robot base frame = DH frame 0),
      * qpos_offsets[i]: theta_offset (hinge) or d (slide) added to q_i,
      * tail_tf: fixed transform from the last body to DH frame n.
    For a hinge joint the body transform excludes the joint's own theta (it is the
    joint's motion); for a slide joint it excludes d.
    """
    n = len(rows)
    body_tfs: list[np.ndarray] = []
    offsets: list[float] = []
    if convention == "dh_standard":
        # body 0 sits at frame 0 (joint 1 axis = z0). Between body i and body i+1:
        # Rz(theta_i) Tz(d_i) Tx(a_i) Rx(alpha_i), with the variable part being the joint motion.
        prev_tail = np.eye(4)
        for i, (r, t) in enumerate(zip(rows, types)):
            body_tfs.append(prev_tail)
            if t == "hinge":
                offsets.append(r.theta_offset)
                fixed = make_tf(None, [0, 0, r.d]) @ make_tf(None, [r.a, 0, 0]) @ make_tf(rot_x(r.alpha))
            else:
                offsets.append(r.d)
                fixed = make_tf(rot_z(r.theta_offset)) @ make_tf(None, [r.a, 0, 0]) @ make_tf(rot_x(r.alpha))
            prev_tail = fixed
        tail = prev_tail
    elif convention == "dh_modified":
        for r, t in zip(rows, types):
            pre = make_tf(rot_x(r.alpha)) @ make_tf(None, [r.a, 0, 0])
            if t == "hinge":
                offsets.append(r.theta_offset)
                body_tfs.append(pre @ make_tf(None, [0, 0, r.d]))
            else:
                offsets.append(r.d)
                body_tfs.append(pre @ make_tf(rot_z(r.theta_offset)))
        tail = np.eye(4)
    else:
        raise ValueError(f"not a DH convention: {convention}")
    assert len(body_tfs) == n
    return body_tfs, offsets, tail


def motion_tf(jtype: str, axis: list[float], value: float) -> np.ndarray:
    """4x4 transform of a hinge (rotation by ``value`` about ``axis``) or slide (translation along it)."""
    if jtype == "hinge":
        return make_tf(axis_angle_mat(np.asarray(axis, dtype=float), value))
    a = np.asarray(axis, dtype=float)
    return make_tf(None, a / np.linalg.norm(a) * value)


def sample_configs(spec: Spec, n: int, seed: int = 0) -> np.ndarray:
    """Home plus ``n - 1`` seeded uniform configurations within the limits of an SI spec.
    Unlimited hinges use [-pi, pi], unlimited slides [-0.1, 0.1] m."""
    rng = np.random.default_rng(seed)
    lo = np.array([j.limits.lower if j.limits else (-math.pi if j.type == "hinge" else -0.1) for j in spec.joints])
    hi = np.array([j.limits.upper if j.limits else (math.pi if j.type == "hinge" else 0.1) for j in spec.joints])
    home = np.array([j.home for j in spec.joints], dtype=float)
    return np.vstack([home[None, :], rng.uniform(lo, hi, size=(max(n - 1, 0), len(lo)))])


def build_chain(spec: Spec) -> Chain:
    """Convert any spec convention into body poses (SI) ready for MJCF.

    DH theta/d offsets are folded into the next body's pose (a joint's motion
    about/along a fixed axis commutes with a constant motion about/along the same
    axis), so the MJCF joint value equals the spec joint value.
    """
    s = spec.to_si() if (spec.units.length != "m" or spec.units.angle != "rad") else spec
    base_pos, base_quat = _tf_to_pos_quat(pose_to_tf(s.base.origin))
    ee_tf = pose_to_tf(s.ee.origin)
    types = [j.type for j in s.joints]
    if s.convention == "offset":
        tfs = [pose_to_tf(j.origin) for j in s.joints]  # type: ignore[arg-type]
        axes = []
        for j in s.joints:
            ax = np.asarray(j.axis, dtype=float)
            axes.append([float(x) for x in ax / np.linalg.norm(ax)])
        offs = [0.0] * len(s.joints)
    else:
        rows = [j.dh for j in s.joints]
        tfs, offs, tail = dh_to_offset(rows, types, s.convention)  # type: ignore[arg-type]
        axes = [[0.0, 0.0, 1.0] for _ in s.joints]
        ee_tf = tail @ ee_tf
    # fold constant joint offsets into the child transform
    for i in range(len(tfs)):
        if offs[i] != 0.0:
            M = motion_tf(types[i], axes[i], offs[i])
            if i + 1 < len(tfs):
                tfs[i + 1] = M @ tfs[i + 1]
            else:
                ee_tf = M @ ee_tf
    joints = []
    for j, T, ax in zip(s.joints, tfs, axes):
        pos, quat = _tf_to_pos_quat(T)
        joints.append(ChainJoint(name=j.name, type=j.type, pos=pos, quat=quat, axis=ax))
    ee_pos, ee_quat = _tf_to_pos_quat(ee_tf)
    return Chain(base_pos=base_pos, base_quat=base_quat, joints=joints, ee_pos=ee_pos, ee_quat=ee_quat)


def dh_fk(rows: list[DH], q: list[float], convention: str, types: list[str] | None = None) -> np.ndarray:
    """Textbook DH forward kinematics (SI), frame 0 -> frame n. Used to cross-check the converter."""
    types = types or ["hinge"] * len(rows)
    T = np.eye(4)
    for r, qi, t in zip(rows, q, types):
        th = r.theta_offset + (qi if t == "hinge" else 0.0)
        d = r.d + (qi if t == "slide" else 0.0)
        if convention == "dh_standard":
            A = make_tf(rot_z(th)) @ make_tf(None, [0, 0, d]) @ make_tf(None, [r.a, 0, 0]) @ make_tf(rot_x(r.alpha))
        else:
            A = make_tf(rot_x(r.alpha)) @ make_tf(None, [r.a, 0, 0]) @ make_tf(rot_z(th)) @ make_tf(None, [0, 0, d])
        T = T @ A
    return T


# --------------------------------------------------------------------------- #
# Field paths, numeric-field iteration and source coverage
# --------------------------------------------------------------------------- #

_TOKEN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)|\[(\*|\d+)\]")
_IGNORED_TOP = {"schema_version", "units", "sources", "estimates", "notes", "name", "manufacturer",
                "model", "description", "convention"}


def _parse_path(path: str) -> list[str]:
    """'joints[2].dh.a' -> ['joints', '2', 'dh', 'a'];  'joints[*].limits' -> ['joints', '*', 'limits']."""
    tokens: list[str] = []
    pos = 0
    p = path.strip()
    if not p:
        raise ValueError("empty field path")
    while pos < len(p):
        if p[pos] == ".":
            pos += 1
            continue
        m = _TOKEN.match(p, pos)
        if not m:
            raise ValueError(f"malformed field path: {path!r}")
        tokens.append(m.group(1) if m.group(1) is not None else m.group(2))
        pos = m.end()
    return tokens


def path_covers(key: str, path: str) -> bool:
    """True if field path ``key`` (possibly with [*]) equals ``path`` or is a prefix of it."""
    k, p = _parse_path(key), _parse_path(path)
    if len(k) > len(p):
        return False
    return all(a == b or (a == "*" and b.isdigit()) for a, b in zip(k, p))


def iter_numeric_fields(spec: Spec) -> Iterator[tuple[str, float]]:
    """Yield (field_path, value) for every number the spec author supplied.

    Fields left at their schema default (e.g. zero base pose, default axis) and
    numbers that are exactly zero are not yielded: an absent or zero number needs
    no source. Vectors yield one path for the vector (e.g.
    ``joints[0].origin.xyz``, value = its norm) rather than per element.
    """
    data = spec.model_dump(mode="python", exclude_none=True, exclude_unset=True)

    def walk(obj: Any, path: str) -> Iterator[tuple[str, float]]:
        if isinstance(obj, bool):
            return
        if isinstance(obj, (int, float)):
            if float(obj) != 0.0:
                yield path, float(obj)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if not path and k in _IGNORED_TOP:
                    continue
                yield from walk(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            if obj and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in obj):
                if any(float(x) != 0.0 for x in obj):
                    yield path, float(np.linalg.norm(np.asarray(obj, dtype=float)))
            else:
                for i, v in enumerate(obj):
                    yield from walk(v, f"{path}[{i}]")

    yield from walk(data, "")


def uncovered_fields(spec: Spec) -> list[str]:
    """Numeric field paths covered by neither ``sources`` nor ``estimates``."""
    keys = list(spec.sources) + list(spec.estimates)
    out = []
    for path, _ in iter_numeric_fields(spec):
        if path == "dof":
            continue  # implied by the joint list
        if not any(path_covers(k, path) for k in keys):
            out.append(path)
    return out


_SOURCE_VALUE = re.compile(r"^(https?://[^\s/?#]+[^\s]*|doc:(?![/\\~])(?![A-Za-z]:)[^\s]+)$")


def _bad_source_value(v: str) -> bool:
    v = str(v).strip()
    if not _SOURCE_VALUE.match(v):
        return True
    if v.startswith("doc:"):  # a relative path inside the repository: no `..` segments, no backslashes
        rel = v[4:]
        return "\\" in rel or ".." in rel.split("/")
    return False


def bad_source_values(spec: Spec) -> list[tuple[str, str]]:
    """(key, value) for every ``sources`` value that is neither an http(s) URL nor a
    ``doc:<relative path>`` reference (e.g. ``doc:benchmark/inputs/x/sources.md``; no ``..`` segment,
    no backslash)."""
    return [(k, v) for k, v in spec.sources.items() if _bad_source_value(v)]


def _is_vector(x: Any) -> bool:
    return isinstance(x, list) and bool(x) and all(isinstance(e, (int, float)) and not isinstance(e, bool)
                                                   for e in x)


def _path_exists(data: Any, tokens: list[str]) -> bool:
    if not tokens:
        return True
    t, rest = tokens[0], tokens[1:]
    if isinstance(data, dict):
        return t in data and _path_exists(data[t], rest)
    if isinstance(data, list) and not _is_vector(data):  # vectors are sourced as a whole, not per element
        if t == "*":
            return any(_path_exists(x, rest) for x in data)
        return t.isdigit() and int(t) < len(data) and _path_exists(data[int(t)], rest)
    return False


def _key_data(spec: Spec) -> dict:
    data = spec.model_dump(mode="python")
    forbidden = "dh" if spec.convention == "offset" else "origin"  # cannot hold a value in this convention
    for j in data["joints"]:
        j.pop(forbidden, None)
    return data


def unmatched_keys(spec: Spec) -> list[str]:
    """``sources``/``estimates`` keys that name no field of this spec at all (a typo, a wrong index, a
    field of another convention, or one element of a vector such as ``joints[0].origin.xyz[2]``). A key
    naming an existing field is fine even if its value is zero, a default or null."""
    data = _key_data(spec)
    out = []
    for k in list(spec.sources) + list(spec.estimates):
        try:
            ok = _path_exists(data, _parse_path(k))
        except ValueError:
            ok = False
        if not ok and k not in out:
            out.append(k)
    return out


def _vector_prefix(data: Any, tokens: list[str]) -> Optional[int]:
    """Number of leading tokens that name a numeric vector, if ``tokens`` index into one."""
    for n in range(len(tokens)):
        if _is_vector(_get_path(data, tokens[:n])) and n < len(tokens):
            return n
    return None


def _get_path(data: Any, tokens: list[str]) -> Any:
    for t in tokens:
        if isinstance(data, dict) and t in data:
            data = data[t]
        elif isinstance(data, list) and t.isdigit() and int(t) < len(data):
            data = data[int(t)]
        else:
            return None
    return data


def _all_key_paths(data: Any, path: str = "") -> Iterator[str]:
    if path:
        yield path
    if isinstance(data, dict):
        for k, v in data.items():
            yield from _all_key_paths(v, f"{path}.{k}" if path else k)
    elif isinstance(data, list) and not _is_vector(data):
        for i, v in enumerate(data):
            yield from _all_key_paths(v, f"{path}[{i}]")


def suggest_key(spec: Spec, key: str) -> Optional[str]:
    """The field path meant by an unmatched ``sources``/``estimates`` key: the whole vector for a key
    naming one element of it, else the closest existing field path (difflib), or None."""
    data = _key_data(spec)
    try:
        toks = _parse_path(key)
    except ValueError:
        toks = None
    if toks:
        n = _vector_prefix(data, [t if t != "*" else "0" for t in toks])
        if n:
            out = ""
            for t in toks[:n]:
                out += f"[{t}]" if (t.isdigit() or t == "*") else (f".{t}" if out else t)
            return out
    paths = {p for p in _all_key_paths(data) if _parse_path(p)[0] not in _IGNORED_TOP}
    paths |= {re.sub(r"\[\d+\]", "[*]", p) for p in paths}
    m = difflib.get_close_matches(key, sorted(paths), n=1, cutoff=0.6)
    return m[0] if m else None


def describe_key(spec: Spec, key: str) -> str:
    """``key`` with a suggestion, e.g. ```joints[2].dh.aa` (did you mean `joints[2].dh.a`?)``."""
    sug = suggest_key(spec, key)
    if sug is None:
        return f"`{key}`"
    try:
        element = _vector_prefix(_key_data(spec), [t if t != "*" else "0" for t in _parse_path(key)]) is not None
    except ValueError:
        element = False
    if element:
        return f"`{key}` (one element of a vector: source the whole vector path `{sug}`)"
    return f"`{key}` (did you mean `{sug}`?)"


def duplicate_keys(spec: Spec) -> list[str]:
    """Keys listed in both ``sources`` and ``estimates`` (the source wins; the estimate entry is noise)."""
    est = {tuple(_safe_parse(k)) for k in spec.estimates}
    return [k for k in spec.sources if tuple(_safe_parse(k)) in est]


def _safe_parse(key: str) -> list[str]:
    try:
        return _parse_path(key)
    except ValueError:
        return [key]


def estimate_counts(spec: Spec) -> tuple[int, int]:
    """(numbers that are estimates, numbers that need a source or estimate), as in ``uncovered_fields``."""
    n = est = 0
    for path, _ in iter_numeric_fields(spec):
        if path == "dof":
            continue
        n += 1
        est += is_estimate(spec, path)
    return est, n


def _specificity(key: str) -> tuple[int, int]:
    toks = _parse_path(key)
    return len(toks), sum(t != "*" for t in toks)


def is_estimate(spec: Spec, path: str) -> bool:
    """True if ``path`` is covered by ``estimates`` and no ``sources`` key covers it at least as
    specifically (e.g. ``sources: {reach.value: url}`` with ``estimates: [reach]`` makes
    ``reach.value`` sourced but ``reach.measured_to`` estimated)."""
    est = [_specificity(k) for k in spec.estimates if path_covers(k, path)]
    if not est:
        return False
    src = [_specificity(k) for k in spec.sources if path_covers(k, path)]
    return not src or max(est) > max(src)


__all__ = [
    "Spec", "Joint", "Link", "GeometryHint", "DH", "Limits", "Pose", "Units", "EndEffector", "Base",
    "Reach", "DrawingDim", "Chain", "ChainJoint", "load_spec", "dump_spec", "json_schema", "write_json_schema",
    "build_chain", "sample_configs", "motion_tf", "dh_to_offset", "dh_fk", "iter_numeric_fields", "uncovered_fields", "path_covers",
    "is_estimate", "bad_source_values", "unmatched_keys", "suggest_key", "describe_key", "duplicate_keys", "estimate_counts", "rpy_to_mat", "mat_to_quat", "quat_to_mat", "make_tf", "pose_to_tf", "axis_angle_mat",
    "rot_x", "rot_y", "rot_z", "SCHEMA_VERSION",
]
