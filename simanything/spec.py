"""The sim-anything robot specification schema (spec.yaml).

A spec describes a serial robot arm from public information. The LLM agent fills
it in; deterministic code (builder.py) turns it into MJCF.

Conventions
-----------
* Units are declared once in ``units`` (length: m|mm, angle: deg|rad). Every
  length / angle in the file uses those units. ``Spec.to_si()`` returns a copy in
  metres and radians; all downstream code works on the SI copy.
* Masses are kg, torques N*m, linear velocities (length unit)/s, angular
  velocities (angle unit)/s.
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
* ``sources`` maps a field path to the URL that supports it. ``estimates`` lists
  field paths whose values were estimated rather than read from a source.
  A path covers itself and everything under it, e.g. ``joints[2]`` covers
  ``joints[2].dh.a``; ``joints[*].limits`` covers the limits of every joint.
  Every number in the spec must be covered by ``sources`` or ``estimates``.
"""

from __future__ import annotations

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
    size: Optional[Vec3] = Field(default=None, description="box half sizes [x, y, z]")
    fromto: Optional[list[float]] = Field(default=None, min_length=6, max_length=6,
                                          description="explicit endpoints in the link frame")
    pos: Optional[Vec3] = None
    rpy: Optional[Vec3] = None


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
    velocity_limit: Optional[float] = Field(default=None, gt=0)
    effort_limit: Optional[float] = Field(default=None, gt=0)
    damping: Optional[float] = Field(default=None, ge=0)
    armature: Optional[float] = Field(default=None, ge=0)
    home: float = 0.0
    link: Link = Field(default_factory=Link, description="the child link moved by this joint")

    @field_validator("axis")
    @classmethod
    def _nonzero_axis(cls, v: Vec3) -> Vec3:
        if float(np.linalg.norm(v)) < 1e-9:
            raise ValueError("axis must be non-zero")
        return v


class EndEffector(_Base):
    name: str = "ee_site"
    origin: Pose = Field(default_factory=Pose)


class Base(_Base):
    origin: Pose = Field(default_factory=Pose, description="pose of the robot base in the world")
    link: Link = Field(default_factory=Link, description="the fixed base link")


class Reach(_Base):
    value: float = Field(gt=0)
    measured_from: Literal["shoulder", "base_origin", "base_axis_horizontal"] = "shoulder"
    measured_to: Literal["ee_site", "wrist_center"] = "ee_site"


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
    qpos_offset: float = 0.0  # added to q before applying the joint motion (DH theta/d offsets)

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
            v = q[i] + j.qpos_offset
            if j.type == "hinge":
                T = T @ make_tf(axis_angle_mat(np.array(j.axis), v))
            else:
                T = T @ make_tf(None, np.asarray(j.axis, dtype=float) / np.linalg.norm(j.axis) * v)
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


def _motion_tf(jtype: str, axis: list[float], value: float) -> np.ndarray:
    if jtype == "hinge":
        return make_tf(axis_angle_mat(np.asarray(axis, dtype=float), value))
    a = np.asarray(axis, dtype=float)
    return make_tf(None, a / np.linalg.norm(a) * value)


def build_chain(spec: Spec) -> Chain:
    """Convert any spec convention into body poses (SI) ready for MJCF.

    DH theta/d offsets are folded into the next body's pose (a joint's motion
    about/along a fixed axis commutes with a constant motion about/along the same
    axis), so the MJCF joint value equals the spec joint value and every
    ``qpos_offset`` in the result is 0.
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
            M = _motion_tf(types[i], axes[i], offs[i])
            if i + 1 < len(tfs):
                tfs[i + 1] = M @ tfs[i + 1]
            else:
                ee_tf = M @ ee_tf
    joints = []
    for j, T, ax in zip(s.joints, tfs, axes):
        pos, quat = _tf_to_pos_quat(T)
        joints.append(ChainJoint(name=j.name, type=j.type, pos=pos, quat=quat, axis=ax, qpos_offset=0.0))
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


def is_estimate(spec: Spec, path: str) -> bool:
    return any(path_covers(k, path) for k in spec.estimates)


__all__ = [
    "Spec", "Joint", "Link", "GeometryHint", "DH", "Limits", "Pose", "Units", "EndEffector", "Base",
    "Reach", "Chain", "ChainJoint", "load_spec", "dump_spec", "json_schema", "write_json_schema",
    "build_chain", "dh_to_offset", "dh_fk", "iter_numeric_fields", "uncovered_fields", "path_covers",
    "is_estimate", "rpy_to_mat", "mat_to_quat", "quat_to_mat", "make_tf", "pose_to_tf", "axis_angle_mat",
    "rot_x", "rot_y", "rot_z", "SCHEMA_VERSION",
]
