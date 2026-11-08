"""Score a candidate MJCF against a reference MJCF through a joint mapping.

See docs/CONTRACTS.md section 5. Public API: :func:`load_mapping`, :func:`evaluate`.

Interpretation notes (where the contract leaves room):

* Sampling: a side whose joint is unlimited imposes no constraint on the
  intersection; only when *both* sides are unlimited is a default range used:
  [-pi, pi] rad for a hinge, [-0.1, 0.1] m for a slide
  (``UNLIMITED_SLIDE_RANGE_M``; +-pi metres would be meaningless). This
  avoids an unlimited reference joint with an offset of pi halving the sampled
  range of the candidate joint.
* Convention fitting: the primary objective is the mean EE position error.
  Options whose position error ties the best one (e.g. a wrist roll whose axis
  passes through the EE point) are separated by the mean aligned orientation
  error. The discrete search (single, then pair and triple changes, restarted
  until two runs agree) is described in :func:`fit_conventions`. Conventions
  that are kinematically indistinguishable (same EE positions and aligned
  orientation errors) resolve to the lowest joint-limit MAE, then the simplest.
  Slide joints are not fitted (sign 1, offset 0).
* Base yaw: the candidate may be rotated about world z by a fitted (or given)
  multiple of 90 deg before comparison, reported as ``base_yaw_deg``.
* Joint-limit diffs: an unlimited joint is reported as its default range
  ([-pi, pi] hinge, [-0.1, 0.1] m slide) in its own coordinates; if both
  joints of a pair are unlimited the diff is 0.
"""

from __future__ import annotations

import functools
import itertools
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

import mujoco
import numpy as np
import yaml

from .schemas import EESpec, ErrorStats, EvalResult, JointConvention, JointLimitDiff, Mapping

__all__ = ["load_mapping", "evaluate", "compute_score", "kinematics_score", "sampling_interval", "default_range", "fit_conventions",
           "N_FIT_CONFIGS", "OFFSET_CHOICES"]

N_FIT_CONFIGS = 256
FIT_MAX_RUNS = 16  # descents (identity + seeded random starts) until two reach the same best cost
FIT_MAX_STEPS = 50  # accepted changes per descent
N_SCREEN_CONFIGS = 32  # configurations used to rank candidate moves before confirming them on all
N_CONFIRM = 8  # best-ranked pair moves confirmed on all configurations
TINY_POS_M = 1e-6  # mean EE position error below which pair moves are not tried
MAX_MOVE_ORDER = 3  # largest number of variables changed in one move (descent and equal-cost search)
N_TIE_SCREEN_CONFIGS = 8  # configurations used to screen equal-cost alternatives (exact ties hold on any subset)
PLATEAU_MAX = 128  # cap on the number of equal-cost alternatives collected
OFFSET_CHOICES = (0.0, math.pi / 2, -math.pi / 2, math.pi)
UNLIMITED_SLIDE_RANGE_M = 0.1  # an unlimited slide joint is sampled/compared over +-this many metres
_HINGE = int(mujoco.mjtJoint.mjJNT_HINGE)
_SLIDE = int(mujoco.mjtJoint.mjJNT_SLIDE)
_FREE = int(mujoco.mjtJoint.mjJNT_FREE)
_TYPE_NAMES = {_HINGE: "hinge", _SLIDE: "slide", _FREE: "free", int(mujoco.mjtJoint.mjJNT_BALL): "ball"}

PathLike = Union[str, Path]


# --------------------------------------------------------------------------- #
# Mapping file
# --------------------------------------------------------------------------- #


def _validate_mapping(mapping: Mapping) -> None:
    nc, nr = len(mapping.candidate.joints), len(mapping.reference.joints)
    if nc != nr:
        raise ValueError(f"mapping: candidate.joints has {nc} entries but reference.joints has {nr}")
    if nc == 0:
        raise ValueError("mapping: no joints mapped")
    if mapping.joint_conventions is not None and len(mapping.joint_conventions) != nc:
        raise ValueError(f"mapping: joint_conventions has {len(mapping.joint_conventions)} entries, "
                         f"expected one per mapped joint ({nc})")
    for side_name, side in (("candidate", mapping.candidate), ("reference", mapping.reference)):
        if (side.ee.site is None) == (side.ee.body is None):
            raise ValueError(f"mapping: {side_name}.ee needs exactly one of 'site' or 'body'")
        if len(side.ee.pos) != 3 or len(side.ee.quat) != 4:
            raise ValueError(f"mapping: {side_name}.ee pos needs 3 values and quat 4")
        if len(set(side.joints)) != len(side.joints):
            raise ValueError(f"mapping: duplicate joint names in {side_name}.joints")


def load_mapping(path: PathLike) -> Mapping:
    """Read and validate a ``map.yaml`` joint-mapping file."""
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path}: mapping file must contain a YAML mapping")
    mapping = Mapping.model_validate(data)
    _validate_mapping(mapping)
    return mapping


# --------------------------------------------------------------------------- #
# Model side
# --------------------------------------------------------------------------- #


@dataclass
class _Side:
    label: str
    model: mujoco.MjModel
    data: mujoco.MjData
    joint_ids: np.ndarray
    qadr: np.ndarray
    jtypes: list[int]
    ranges: list[Optional[tuple[float, float]]]  # None = unlimited
    site_id: int
    body_id: int
    ee_pos: np.ndarray
    ee_rot: np.ndarray
    yaw: float = 0.0  # rotation of this whole model about world z (base mounting convention)
    base_pos: Optional[np.ndarray] = None  # world pose of the mapping's base body (fixed), if any
    base_rot: Optional[np.ndarray] = None

    def fk(self, Q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """EE world positions (N,3) and rotation matrices (N,3,3) for joint configs Q (N,n)."""
        m, d = self.model, self.data
        n = Q.shape[0]
        P = np.empty((n, 3))
        R = np.empty((n, 3, 3))
        d.qpos[:] = m.qpos0
        qadr = self.qadr
        for i in range(n):
            d.qpos[qadr] = Q[i]
            mujoco.mj_kinematics(m, d)
            if self.site_id >= 0:
                P[i] = d.site_xpos[self.site_id]
                R[i] = d.site_xmat[self.site_id].reshape(3, 3)
            else:
                Rb = d.xmat[self.body_id].reshape(3, 3)
                P[i] = d.xpos[self.body_id] + Rb @ self.ee_pos
                R[i] = Rb @ self.ee_rot
        if self.base_rot is not None:
            P = (P - self.base_pos) @ self.base_rot  # rows: R^T (p - p0)
            R = np.einsum("ji,njk->nik", self.base_rot, R)
        if self.yaw != 0.0:
            c, s = math.cos(self.yaw), math.sin(self.yaw)
            Rz = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
            P = P @ Rz.T
            R = np.einsum("ij,njk->nik", Rz, R)
        return P, R


def _load_side(label: str, path: PathLike, joints: list[str], ee: EESpec,
               base_body: Optional[str] = None) -> _Side:
    try:
        model = mujoco.MjModel.from_xml_path(str(path))
    except Exception as exc:  # mujoco raises ValueError with the compiler message
        raise ValueError(f"{label} model {path} failed to load: {exc}") from exc
    data = mujoco.MjData(model)
    jids, qadr, jtypes, ranges = [], [], [], []
    for name in joints:
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if jid < 0:
            avail = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j) for j in range(model.njnt)]
            raise ValueError(f"{label} joint {name!r} not found in {path}; available: {avail}")
        jt = int(model.jnt_type[jid])
        if jt not in (_HINGE, _SLIDE):
            raise ValueError(f"{label} joint {name!r} is a {_TYPE_NAMES.get(jt, jt)} joint; "
                             "only hinge and slide joints can be mapped")
        jids.append(jid)
        qadr.append(int(model.jnt_qposadr[jid]))
        jtypes.append(jt)
        ranges.append(tuple(float(v) for v in model.jnt_range[jid]) if model.jnt_limited[jid] else None)
    site_id = body_id = -1
    if ee.site is not None:
        site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, ee.site)
        if site_id < 0:
            raise ValueError(f"{label} EE site {ee.site!r} not found in {path}")
    else:
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, ee.body)
        if body_id < 0:
            raise ValueError(f"{label} EE body {ee.body!r} not found in {path}")
    quat = np.asarray(ee.quat, dtype=float)
    if np.linalg.norm(quat) < 1e-12:
        raise ValueError(f"{label} EE quat must be non-zero")
    rot = np.empty(9)
    mujoco.mju_quat2Mat(rot, quat / np.linalg.norm(quat))
    side = _Side(label, model, data, np.array(jids, dtype=int), np.array(qadr, dtype=int), jtypes, ranges,
                 site_id, body_id, np.asarray(ee.pos, dtype=float), rot.reshape(3, 3))
    if base_body is not None:
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, base_body)
        if bid < 0:
            raise ValueError(f"{label} base body {base_body!r} not found in {path}")
        if bid > 0 and any(model.body_jntnum[b] > 0 for b in _ancestors(model, bid)):
            raise ValueError(f"{label} base body {base_body!r} must not move (it has jointed ancestors)")
        data.qpos[:] = model.qpos0
        mujoco.mj_kinematics(model, data)
        side.base_pos = data.xpos[bid].copy()
        side.base_rot = data.xmat[bid].reshape(3, 3).copy()
    return side


def _ancestors(model: mujoco.MjModel, bid: int) -> list[int]:
    out = []
    while bid > 0:
        out.append(bid)
        bid = int(model.body_parentid[bid])
    return out


# --------------------------------------------------------------------------- #
# Geometry helpers
# --------------------------------------------------------------------------- #


def _geodesic(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Rotation angle (rad) between stacks of rotation matrices, accurate near 0."""
    chord = np.linalg.norm((A - B).reshape(len(A), 9), axis=1)  # = 2*sqrt(2)*sin(theta/2)
    return 2.0 * np.arcsin(np.clip(chord / (2.0 * math.sqrt(2.0)), 0.0, 1.0))


def _best_tool_rotation(Rc: np.ndarray, Rr: np.ndarray) -> np.ndarray:
    """R* in SO(3) minimising sum ||Rr - Rc R*||_F^2: projection of mean(Rc^T Rr) onto SO(3)."""
    M = np.einsum("nji,njk->ik", Rc, Rr) / len(Rc)
    U, _, Vt = np.linalg.svd(M)
    D = np.diag([1.0, 1.0, np.sign(np.linalg.det(U @ Vt)) or 1.0])
    return U @ D @ Vt


def _aligned_angles(Rc: np.ndarray, Rr: np.ndarray) -> np.ndarray:
    Rs = _best_tool_rotation(Rc, Rr)
    return _geodesic(Rc @ Rs, Rr)


def _stats(x: np.ndarray) -> ErrorStats:
    return ErrorStats(mean=float(np.mean(x)), p95=float(np.percentile(x, 95)), max=float(np.max(x)))


def _apply(conv: list[JointConvention], Q: np.ndarray) -> np.ndarray:
    sign = np.array([c.sign for c in conv], dtype=float)
    off = np.array([c.offset for c in conv], dtype=float)
    return Q * sign + off


# --------------------------------------------------------------------------- #
# Limits and sampling
# --------------------------------------------------------------------------- #


def sampling_interval(cand_range: Optional[tuple[float, float]], ref_range: Optional[tuple[float, float]],
                      conv: JointConvention,
                      unlimited: tuple[float, float] = (-math.pi, math.pi)) -> tuple[float, float, bool]:
    """Interval (candidate coordinates) to sample one joint from.

    Intersection of the candidate range and the reference range mapped into
    candidate coordinates (q_cand = sign * (q_ref - offset)); ``None`` means
    unlimited. Returns ``(lo, hi, empty)``; on an empty intersection the
    candidate range is returned with ``empty=True``. ``unlimited`` is used when
    both sides are unlimited (see :func:`default_range`).
    """
    if cand_range is None and ref_range is None:
        return float(unlimited[0]), float(unlimited[1]), False
    if ref_range is None:
        return float(cand_range[0]), float(cand_range[1]), False
    a, b = (conv.sign * (ref_range[0] - conv.offset), conv.sign * (ref_range[1] - conv.offset))
    mapped = (min(a, b), max(a, b))
    if cand_range is None:
        return mapped[0], mapped[1], False
    lo, hi = max(cand_range[0], mapped[0]), min(cand_range[1], mapped[1])
    if hi < lo:
        return float(cand_range[0]), float(cand_range[1]), True
    return float(lo), float(hi), False


def default_range(jtype: int) -> tuple[float, float]:
    """Range assumed for an unlimited joint: [-pi, pi] rad (hinge), +-0.1 m (slide)."""
    if int(jtype) == _SLIDE:
        return -UNLIMITED_SLIDE_RANGE_M, UNLIMITED_SLIDE_RANGE_M
    return -math.pi, math.pi


def _own_range(r: Optional[tuple[float, float]], jtype: int = _HINGE) -> tuple[float, float]:
    return default_range(jtype) if r is None else (float(r[0]), float(r[1]))


def _ranges_in_ref_coords(cand: _Side, ref: _Side, i: int, sign: int, offset: float
                          ) -> tuple[tuple[float, float], tuple[float, float]]:
    """(candidate range mapped into reference coordinates, reference range) of joint pair i;
    an unlimited joint counts as its default range, and two unlimited joints as equal."""
    cr, rr = cand.ranges[i], ref.ranges[i]
    rref = _own_range(rr, ref.jtypes[i])
    if cr is None and rr is None:
        return rref, rref
    lo, hi = _own_range(cr, cand.jtypes[i])
    a, b = sign * lo + offset, sign * hi + offset
    return (min(a, b), max(a, b)), rref


def _limit_diffs(cand: _Side, ref: _Side, mapping: Mapping, conv: list[JointConvention],
                 notes: list[str]) -> tuple[list[JointLimitDiff], float]:
    diffs, hinge_abs = [], []
    unlimited = []
    for i, (cn, rn) in enumerate(zip(mapping.candidate.joints, mapping.reference.joints)):
        cref, rref = _ranges_in_ref_coords(cand, ref, i, conv[i].sign, conv[i].offset)
        if (cand.ranges[i] is None) != (ref.ranges[i] is None):
            unlimited.append(f"candidate {cn}" if cand.ranges[i] is None else f"reference {rn}")
        d = JointLimitDiff(candidate=cn, reference=rn, candidate_range=[cref[0], cref[1]],
                           reference_range=[rref[0], rref[1]], lower_diff=cref[0] - rref[0],
                           upper_diff=cref[1] - rref[1])
        diffs.append(d)
        if cand.jtypes[i] == _HINGE and ref.jtypes[i] == _HINGE:
            hinge_abs += [abs(d.lower_diff), abs(d.upper_diff)]
    if unlimited:
        notes.append("unlimited joints compared as [-pi, pi] (hinge) or "
                     f"[-{UNLIMITED_SLIDE_RANGE_M:g}, {UNLIMITED_SLIDE_RANGE_M:g}] m (slide) against a limited "
                     "counterpart: " + ", ".join(unlimited))
    mae = float(np.degrees(np.mean(hinge_abs))) if hinge_abs else 0.0
    return diffs, mae


# --------------------------------------------------------------------------- #
# Convention fitting
# --------------------------------------------------------------------------- #


def _uniform(rng: np.random.Generator, bounds: list[tuple[float, float]], n: int) -> np.ndarray:
    lo = np.array([b[0] for b in bounds])
    hi = np.array([b[1] for b in bounds])
    return lo + (hi - lo) * rng.random((n, len(bounds)))


def _hom(R: np.ndarray, t: np.ndarray) -> np.ndarray:
    T = np.zeros(R.shape[:-2] + (4, 4))
    T[..., :3, :3] = R
    T[..., :3, 3] = t
    T[..., 3, 3] = 1.0
    return T


def _screw(axis: np.ndarray, anchor: np.ndarray, jtype: int, q: np.ndarray) -> np.ndarray:
    """(N,4,4) transforms of a hinge (rotation by q about the line anchor + t*axis) or a
    slide (translation by q along axis), all in world coordinates."""
    n = len(q)
    if jtype == _SLIDE:
        return _hom(np.broadcast_to(np.eye(3), (n, 3, 3)), q[:, None] * axis)
    K = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]])
    s, c = np.sin(q)[:, None, None], np.cos(q)[:, None, None]
    R = np.eye(3) + s * K + (1.0 - c) * (K @ K)
    return _hom(R, anchor - R @ anchor)


def _xform_points(T: np.ndarray, w: Optional[np.ndarray]) -> np.ndarray:
    """Homogeneous transforms T (..., 4, 4) applied to points w (..., 3); w=None is the origin."""
    if w is None:
        return T[..., :3, 3]
    return T[..., :3, 0] * w[..., :1] + T[..., :3, 1] * w[..., 1:2] + T[..., :3, 2] * w[..., 2:] + T[..., :3, 3]


def _poe_factors(side: _Side, Q: np.ndarray, opts: list[list[tuple[int, float]]]
                 ) -> tuple[list[int], list[np.ndarray], np.ndarray]:
    """Product-of-exponentials form of ``side.fk`` (without yaw) for vectorised fitting.

    With every joint at qpos0 (where MuJoCo's joint rotations/translations are
    zero) the EE pose is M, and each mapped joint on the EE body's ancestor path
    is a screw about its world axis through its anchor, so
    ``T(q) = B E_1(q_1) ... E_k(q_k) M`` in chain (joint id) order, B being the
    ``base_body`` frame. Returns ``(order, factors, BM)``: ``order`` lists the
    mapping indices of those joints (others cannot move the EE),
    ``factors[j][k]`` is E for joint ``order[j]`` under option ``opts[i][k]``
    (``q_ref = sign * Q[:, i] + offset``), shape (K, N, 4, 4), and
    ``BM = (B, M)`` as (1, 1, 4, 4) arrays.
    """
    m, d = side.model, side.data
    d.qpos[:] = m.qpos0
    mujoco.mj_kinematics(m, d)
    if side.site_id >= 0:
        bid = int(m.site_bodyid[side.site_id])
        M = _hom(d.site_xmat[side.site_id].reshape(3, 3), d.site_xpos[side.site_id])
    else:
        bid = side.body_id
        Rb = d.xmat[bid].reshape(3, 3)
        M = _hom(Rb @ side.ee_rot, d.xpos[bid] + Rb @ side.ee_pos)
    path = set(_ancestors(m, bid))
    B = np.eye(4)
    if side.base_rot is not None:
        B = _hom(side.base_rot.T, -side.base_rot.T @ side.base_pos)
    order = sorted((i for i, j in enumerate(side.joint_ids) if int(m.jnt_bodyid[j]) in path),
                   key=lambda i: int(side.joint_ids[i]))
    factors = []
    for i in order:
        j, adr = int(side.joint_ids[i]), int(side.qadr[i])
        axis, anchor = d.xaxis[j].copy(), d.xanchor[j].copy()
        factors.append(np.stack([_screw(axis, anchor, side.jtypes[i], s * Q[:, i] + o - m.qpos0[adr])
                                 for s, o in opts[i]]))
    return order, factors, (B[None, None], M[None, None])


def fit_conventions(cand: _Side, ref: _Side, Q: np.ndarray, fit_yaw: bool = True, seed: int = 0,
                    max_runs: int = FIT_MAX_RUNS) -> list[JointConvention]:
    """Discrete fit of per-hinge sign/offset (and the candidate base yaw).

    Cost: mean EE position error over the configurations ``Q`` (candidate
    coordinates), ties broken by the mean aligned orientation error. Search:
    steepest descent over single changes (the yaw or one joint's option); when
    those stall above ``TINY_POS_M``, the best simultaneous change of two, then
    three, variables is tried (e.g. a base turn compensated further down the
    chain). Runs start from the identity, then from seeded random starting
    points, until two runs reach the same best cost (at most ``max_runs``).
    Moves are ranked on the first ``N_SCREEN_CONFIGS`` configurations and the
    best few confirmed on all of ``Q``; the reference EE pose of any convention
    is a product of precomputed per-joint screw transforms
    (:func:`_poe_factors`, checked against MuJoCo's kinematics), so a move is
    cheap to evaluate. Equal-cost alternatives (reachable from the best by
    cost-preserving changes of up to ``MAX_MOVE_ORDER`` variables, at most
    ``PLATEAU_MAX`` of them) resolve to the lowest joint-limit MAE as reported
    by :func:`evaluate`, then to the simplest (identity < sign flip < offset;
    a base yaw before joint offsets). This only chooses among kinematically
    indistinguishable conventions (e.g. a base yaw vs a joint-1 offset, a
    roll-pitch-roll shoulder flip, a last-joint offset vs a constant tool
    rotation); without it an exact model could lose its limits score. A mapped
    joint that cannot move the EE gets its lowest-MAE option. ``cand.yaw`` is
    left set to the fitted yaw.
    """
    n = len(cand.jtypes)
    hinge_opts = [(s, o) for s in (1, -1) for o in OFFSET_CHOICES]
    opts = [hinge_opts if cand.jtypes[i] == _HINGE and ref.jtypes[i] == _HINGE else [(1, 0.0)] for i in range(n)]
    yaw_opts = list(OFFSET_CHOICES) if fit_yaw else [cand.yaw]

    cand.yaw = 0.0  # the yaw is applied to the reference side instead (as its inverse)
    Pc, Rc = cand.fk(Q)
    ns = min(N_SCREEN_CONFIGS, len(Q))
    ns_tie = min(N_TIE_SCREEN_CONFIGS, len(Q))
    order, jfac, (B, M) = _poe_factors(ref, Q, opts)
    Rz = np.array([[[math.cos(-y), -math.sin(-y), 0.0], [math.sin(-y), math.cos(-y), 0.0], [0.0, 0.0, 1.0]]
                   for y in yaw_opts])
    # chain of factors: [yaw (inverse) . base frame], joints in chain order, [EE at qpos0]
    F = [(_hom(Rz, np.zeros(3)) @ B[0])[:, None]] + jfac + [M]
    var_opts = [[(1, y) for y in yaw_opts]] + [opts[i] for i in order] + [[(1, 0.0)]]
    nv = len(F)
    searchable = [v for v in range(nv) if len(var_opts[v]) > 1]

    def cx(v: int, k: int) -> int:
        s, o = var_opts[v][k]
        return (s == -1) + 2 * (o != 0.0)

    def lim(i: int, so: tuple[int, float]) -> float:
        """Joint-limit error of mapped joint i under option so (sum over both bounds)."""
        if not (cand.jtypes[i] == _HINGE and ref.jtypes[i] == _HINGE):
            return 0.0
        c, r = _ranges_in_ref_coords(cand, ref, i, *so)
        return abs(c[0] - r[0]) + abs(c[1] - r[1])

    var_lim = [[0.0] * len(yaw_opts)] + [[lim(i, so) for so in opts[i]] for i in order] + [[0.0]]

    def chain(x: tuple, stop: Optional[int] = None, lo: int = 0, hi: Optional[int] = None) -> np.ndarray:
        T = np.broadcast_to(np.eye(4), (1, 4, 4))
        for v in range(lo, nv if hi is None else hi):
            T = T @ F[v][x[v], :stop]
        return T

    identity = tuple(0 for _ in range(nv))
    if fit_yaw:
        identity = (yaw_opts.index(0.0),) + identity[1:]
    # sanity check of the factorisation against MuJoCo (identity conventions, no yaw)
    T0 = np.broadcast_to(B[0] @ chain(identity, 8, 1), (min(8, len(Q)), 4, 4))
    P0, R0 = ref.fk(Q[:8])
    if np.max(np.abs(T0[:, :3, 3] - P0)) > 1e-9 or np.max(np.abs(T0[:, :3, :3] - R0)) > 1e-9:
        raise RuntimeError("internal error: product-of-exponentials kinematics disagree with MuJoCo")

    cache: dict[tuple, tuple[float, float]] = {}

    def cost(x: tuple) -> tuple[float, float]:
        if x not in cache:
            T = np.broadcast_to(chain(x), (len(Q), 4, 4))
            pos = float(np.mean(np.linalg.norm(Pc - T[:, :3, 3], axis=1)))
            cache[x] = (pos, float(np.mean(_aligned_angles(Rc, T[:, :3, :3]))))
        return cache[x]

    def better(a: tuple[float, float], b: tuple[float, float]) -> bool:
        """a strictly better than b (position first, orientation breaks ties)."""
        tol = 1e-9 + 1e-6 * min(a[0], b[0])
        if a[0] < b[0] - tol:
            return True
        if a[0] > b[0] + tol:
            return False
        return a[1] < b[1] - 1e-9 - 1e-6 * min(a[1], b[1])

    def scan(x: tuple, vs: tuple[int, ...], ns: int = ns) -> tuple[np.ndarray, list]:
        """Screening position cost of every change of exactly the variables ``vs``
        (flat array over the alternatives, in ``itertools.product`` order)."""
        alts = [[k for k in range(len(var_opts[v])) if k != x[v]] for v in vs]
        # propagate the EE point from the tip to the base; alternatives of earlier
        # variables become leading axes
        w, nxt = None, nv
        for v, alt in zip(reversed(vs), reversed(alts)):
            w = _xform_points(chain(x, ns, v + 1, nxt), w)
            Fa = F[v][alt, :ns]
            w = _xform_points(Fa.reshape(Fa.shape[:1] + (1,) * (w.ndim - 2) + Fa.shape[1:]), w[None])
            nxt = v
        w = _xform_points(chain(x, ns, 0, nxt), w)
        return np.mean(np.linalg.norm(w - Pc[:ns], axis=-1), axis=-1).ravel(), alts

    def moved(x: tuple, vs: tuple[int, ...], alts: list, flat: int) -> tuple:
        y = list(x)
        for v, alt, k in zip(vs, alts, np.unravel_index(flat, [len(a) for a in alts])):
            y[v] = alt[k]
        return tuple(y)

    def best_move(x: tuple, order_: int) -> Optional[tuple]:
        """Best change of exactly ``order_`` variables: all are ranked on the screening
        configurations, the best ``N_CONFIRM`` (all single changes) confirmed on all."""
        scans = [(vs,) + scan(x, vs) for vs in itertools.combinations(searchable, order_)]
        if not scans:
            return None
        errs = np.concatenate([s[1] for s in scans])
        owner = np.concatenate([np.full(len(s[1]), j) for j, s in enumerate(scans)])
        start = np.cumsum([0] + [len(s[1]) for s in scans])
        picks = np.argsort(errs, kind="stable")
        best = None
        for f in (picks if order_ == 1 else picks[:N_CONFIRM]):
            vs, _, alts = scans[owner[f]]
            y = moved(x, vs, alts, int(f - start[owner[f]]))
            if best is None or better(cost(y), cost(best)):
                best = y
        return best

    def descend(x: tuple) -> tuple:
        """Steepest descent; changes of 2..MAX_MOVE_ORDER variables are tried only when
        smaller ones stall above TINY_POS_M."""
        for _ in range(FIT_MAX_STEPS):
            cur = cost(x)
            for order_ in range(1, MAX_MOVE_ORDER + 1):
                if order_ > 1 and cur[0] <= TINY_POS_M:
                    break
                y = best_move(x, order_)
                if y is not None and better(cost(y), cur):
                    break
            if y is None or not better(cost(y), cur):
                break
            x = y
        return x

    def same(a: tuple[float, float], b: tuple[float, float]) -> bool:
        return not better(a, b) and not better(b, a)

    by_cost = functools.cmp_to_key(lambda a, b: -1 if better(cost(a), cost(b)) else int(better(cost(b), cost(a))))
    rng = np.random.default_rng(seed)
    results = [descend(identity)]
    while len(results) < max_runs:
        best = min(results, key=by_cost)
        if sum(same(cost(r), cost(best)) for r in results) >= 2:
            break
        results.append(descend(tuple(int(rng.integers(len(var_opts[v]))) for v in range(nv))))
    best = min(results, key=by_cost)
    # Equal-cost solutions: collect those reachable from the best by changes of up
    # to MAX_MOVE_ORDER variables that keep the cost (exact kinematic
    # equivalences tie on every configuration, so on the screening set too).
    best_cost = cost(best)
    tied = {x for x in cache if same(cache[x], best_cost)}
    queue = sorted(tied)
    while queue and len(tied) < PLATEAU_MAX:
        x = queue.pop(0)
        e0 = float(scan(x, (), ns_tie)[0][0])
        tol = 1e-9 + 1e-6 * e0
        for r in range(1, MAX_MOVE_ORDER + 1):
            for vs in itertools.combinations(searchable, r):
                errs, alts = scan(x, vs, ns_tie)
                for f in np.flatnonzero(np.abs(errs - e0) <= tol):
                    y = moved(x, vs, alts, int(f))
                    if y not in tied and same(cost(y), best_cost):
                        tied.add(y)
                        queue.append(y)
    # lowest limit error, then simplest; on equal complexity a base yaw rather than joint offsets
    x = min(tied, key=lambda t: (round(sum(var_lim[v][t[v]] for v in range(nv)), 9),
                                 sum(cx(v, t[v]) for v in range(nv)), sum(cx(v, t[v]) for v in range(1, nv)), t))
    cand.yaw = var_opts[0][x[0]][1]
    conv = [JointConvention() for _ in range(n)]
    for j, i in enumerate(order):
        s, o = var_opts[j + 1][x[j + 1]]
        conv[i] = JointConvention(sign=s, offset=o)
    for i in set(range(n)) - set(order):  # cannot move the EE: limits decide
        s, o = min(opts[i], key=lambda so: (round(lim(i, so), 9), (so[0] == -1) + 2 * (so[1] != 0.0)))
        conv[i] = JointConvention(sign=s, offset=o)
    return conv


# --------------------------------------------------------------------------- #
# Score
# --------------------------------------------------------------------------- #


def compute_score(p95_pos_mm: float, p95_orient_aligned_deg: float, joint_limit_mae_deg: float,
                  mass_rel_diff: float, dof_match: bool) -> tuple[float, dict[str, float]]:
    """Score (0-100) and its breakdown, per docs/CONTRACTS.md section 5."""
    b = {
        "pos": math.exp(-p95_pos_mm / 25.0),
        "orient": math.exp(-p95_orient_aligned_deg / 10.0),
        "limits": math.exp(-joint_limit_mae_deg / 10.0),
        "mass": math.exp(-abs(mass_rel_diff) / 0.2),
        "dof": 1.0 if dof_match else 0.0,
    }
    score = 100.0 * (0.5 * b["pos"] + 0.2 * b["orient"] + 0.15 * b["limits"] + 0.1 * b["mass"] + 0.05 * b["dof"])
    return score, b


def kinematics_score(breakdown: dict[str, float]) -> float:
    """0-100 from the EE position and aligned orientation terms only, in the weights of ``score``."""
    return 100.0 * (5.0 * breakdown["pos"] + 2.0 * breakdown["orient"]) / 7.0


LIMIT_DISAGREE_DEG = 1.0
LIMIT_DISAGREE_M = 0.001
MASS_DISAGREE_REL = 0.05


def _disagreements(diffs: list[JointLimitDiff], jtypes: list[int], mass_c: float, mass_r: float,
                   mass_rel: float) -> list[str]:
    """Joint limits and total mass where candidate and reference differ: often a sourced datasheet
    value against a choice the reference made, so they are listed rather than scored as model error."""
    out = []
    for d, t in zip(diffs, jtypes):
        if t == _HINGE:
            if max(abs(d.lower_diff), abs(d.upper_diff)) > math.radians(LIMIT_DISAGREE_DEG):
                c, r = np.degrees(d.candidate_range), np.degrees(d.reference_range)
                out.append(f"{d.candidate} limits: candidate [{c[0]:.0f}, {c[1]:.0f}] deg vs reference "
                           f"{d.reference} [{r[0]:.0f}, {r[1]:.0f}] deg")
        elif max(abs(d.lower_diff), abs(d.upper_diff)) > LIMIT_DISAGREE_M:
            out.append(f"{d.candidate} limits: candidate [{d.candidate_range[0]:.3f}, {d.candidate_range[1]:.3f}] m "
                       f"vs reference {d.reference} [{d.reference_range[0]:.3f}, {d.reference_range[1]:.3f}] m")
    if abs(mass_rel) > MASS_DISAGREE_REL:
        out.append(f"total mass: candidate {mass_c:.2f} kg vs reference {mass_r:.2f} kg ({mass_rel * 100:+.0f}%)")
    return out


# --------------------------------------------------------------------------- #
# Evaluate
# --------------------------------------------------------------------------- #


def _joint_names(model: mujoco.MjModel, exclude: set[int]) -> list[str]:
    return [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j) or f"#{j}"
            for j in range(model.njnt) if j not in exclude and int(model.jnt_type[j]) != _FREE]


def evaluate(candidate_path: PathLike, reference_path: PathLike, mapping: Union[Mapping, dict[str, Any]], *,
             n_samples: int = 2000, seed: int = 0) -> EvalResult:
    """Compare the candidate model's EE kinematics, limits and mass with the reference's."""
    if isinstance(mapping, dict):
        mapping = Mapping.model_validate(mapping)
    _validate_mapping(mapping)
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")
    notes: list[str] = []
    cand = _load_side("candidate", candidate_path, mapping.candidate.joints, mapping.candidate.ee,
                      mapping.candidate.base_body)
    ref = _load_side("reference", reference_path, mapping.reference.joints, mapping.reference.ee,
                     mapping.reference.base_body)
    n = len(mapping.candidate.joints)

    # -- structure notes ------------------------------------------------------
    for m, label in ((cand.model, "candidate"), (ref.model, "reference")):
        if any(int(t) == _FREE for t in m.jnt_type):
            notes.append(f"{label} has a free joint; it is held at qpos0")
    extra_ref = _joint_names(ref.model, set(ref.joint_ids.tolist()))
    if extra_ref:
        notes.append(f"reference has {len(extra_ref)} unmapped joint(s) held at qpos0: {', '.join(extra_ref)}")
    extra_cand = _joint_names(cand.model, set(cand.joint_ids.tolist()))
    if extra_cand:
        notes.append(f"candidate has {len(extra_cand)} unmapped joint(s) held at qpos0: {', '.join(extra_cand)}")
    for i in range(n):
        if cand.jtypes[i] != ref.jtypes[i]:
            notes.append(f"joint type mismatch: candidate {mapping.candidate.joints[i]} is "
                         f"{_TYPE_NAMES[cand.jtypes[i]]}, reference {mapping.reference.joints[i]} is "
                         f"{_TYPE_NAMES[ref.jtypes[i]]}")

    rng = np.random.default_rng(seed)
    if mapping.base_yaw is not None:
        cand.yaw = float(mapping.base_yaw)

    # -- conventions ------------------------------------------------------------
    if mapping.joint_conventions is not None:
        conv = list(mapping.joint_conventions)
        fitted = False
    elif mapping.fit_conventions:
        fit_bounds = [_own_range(r, t) for r, t in zip(cand.ranges, cand.jtypes)]
        Qfit = _uniform(rng, fit_bounds, N_FIT_CONFIGS)
        conv = fit_conventions(cand, ref, Qfit, fit_yaw=mapping.base_yaw is None, seed=seed)
        fitted = True
        if cand.yaw != 0.0:
            notes.append(f"fitted candidate base yaw {math.degrees(cand.yaw):+.0f} deg (mounting-frame convention)")
        if any(t == _SLIDE for t in cand.jtypes):
            notes.append("slide joint conventions are not fitted (sign 1, offset 0)")
        changed = [f"{mapping.candidate.joints[i]}: sign {c.sign:+d}, offset {math.degrees(c.offset):+.0f} deg"
                   for i, c in enumerate(conv) if c.sign != 1 or c.offset != 0.0]
        if changed:
            notes.append("fitted non-identity conventions: " + "; ".join(changed))
    else:
        conv = [JointConvention() for _ in range(n)]
        fitted = False

    # -- sampling ---------------------------------------------------------------
    bounds = []
    for i in range(n):
        lo, hi, empty = sampling_interval(cand.ranges[i], ref.ranges[i], conv[i],
                                          unlimited=default_range(cand.jtypes[i]))
        if empty:
            notes.append(f"joint {mapping.candidate.joints[i]}: candidate range and mapped reference range "
                         "do not intersect; sampling the candidate range")
        bounds.append((lo, hi))
    Q = _uniform(rng, bounds, n_samples)
    Pc, Rc = cand.fk(Q)
    Pr, Rr = ref.fk(_apply(conv, Q))

    pos_mm = np.linalg.norm(Pc - Pr, axis=1) * 1000.0
    raw_deg = np.degrees(_geodesic(Rc, Rr))
    aligned_deg = np.degrees(_aligned_angles(Rc, Rr))

    # -- limits, mass, dof ------------------------------------------------------
    limit_diffs, limit_mae = _limit_diffs(cand, ref, mapping, conv, notes)
    mass_c = float(np.sum(cand.model.body_mass))
    mass_r = float(np.sum(ref.model.body_mass))
    mass_diff = mass_c - mass_r
    if mass_r > 0:
        mass_rel = mass_diff / mass_r
    else:
        mass_rel = 0.0
        notes.append("reference total mass is 0; mass_rel_diff set to 0")
    if extra_ref:
        notes.append("reference mass includes the bodies of its unmapped joints")
    dof_c = sum(1 for t in cand.model.jnt_type if int(t) != _FREE)
    dof_match = dof_c == n

    pos_stats = _stats(pos_mm)
    aligned_stats = _stats(aligned_deg)
    score, breakdown = compute_score(pos_stats.p95, aligned_stats.p95, limit_mae, mass_rel, dof_match)

    return EvalResult(
        candidate=str(candidate_path), reference=str(reference_path), robot=mapping.robot,
        n_samples=n_samples, seed=seed, dof_candidate=dof_c, dof_reference=n, dof_match=dof_match,
        conventions=conv, conventions_fitted=fitted, base_yaw_deg=math.degrees(cand.yaw),
        ee_position_error_mm=pos_stats, ee_orientation_error_deg=_stats(raw_deg),
        ee_orientation_error_aligned_deg=aligned_stats,
        joint_limits=limit_diffs, joint_limit_mae_deg=limit_mae,
        mass_candidate=mass_c, mass_reference=mass_r, mass_diff=mass_diff, mass_rel_diff=mass_rel,
        score=score, score_breakdown=breakdown, kinematics_score=kinematics_score(breakdown),
        disagreements=_disagreements(limit_diffs, list(cand.jtypes), mass_c, mass_r, mass_rel), notes=notes,
    )
