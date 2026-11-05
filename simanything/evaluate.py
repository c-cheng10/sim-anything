"""Score a candidate MJCF against a reference MJCF through a joint mapping.

See docs/CONTRACTS.md section 5. Public API: :func:`load_mapping`, :func:`evaluate`.

Interpretation notes (where the contract leaves room):

* Sampling: a side whose joint is unlimited imposes no constraint on the
  intersection; only when *both* sides are unlimited is [-pi, pi] used. This
  avoids an unlimited reference joint with an offset of pi halving the sampled
  range of the candidate joint.
* Convention fitting: the primary objective is the mean EE position error.
  Options whose position error ties the best one (e.g. a wrist roll whose axis
  passes through the EE point) are separated by the mean aligned orientation
  error, and the current choice is kept on a full tie. Slide joints are not
  fitted (sign 1, offset 0).
* Joint-limit diffs: an unlimited joint is reported as [-pi, pi] in its own
  coordinates; if both joints of a pair are unlimited the diff is 0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

import mujoco
import numpy as np
import yaml

from .schemas import EESpec, ErrorStats, EvalResult, JointConvention, JointLimitDiff, Mapping

__all__ = ["load_mapping", "evaluate", "compute_score", "sampling_interval", "fit_conventions",
           "N_FIT_CONFIGS", "OFFSET_CHOICES"]

N_FIT_CONFIGS = 256
FIT_SWEEPS = 2
OFFSET_CHOICES = (0.0, math.pi / 2, -math.pi / 2, math.pi)
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
        return P, R


def _load_side(label: str, path: PathLike, joints: list[str], ee: EESpec) -> _Side:
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
    return _Side(label, model, data, np.array(jids, dtype=int), np.array(qadr, dtype=int), jtypes, ranges,
                 site_id, body_id, np.asarray(ee.pos, dtype=float), rot.reshape(3, 3))


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
                      conv: JointConvention) -> tuple[float, float, bool]:
    """Interval (candidate coordinates) to sample one joint from.

    Intersection of the candidate range and the reference range mapped into
    candidate coordinates (q_cand = sign * (q_ref - offset)); ``None`` means
    unlimited. Returns ``(lo, hi, empty)``; on an empty intersection the
    candidate range is returned with ``empty=True``.
    """
    if cand_range is None and ref_range is None:
        return -math.pi, math.pi, False
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


def _own_range(r: Optional[tuple[float, float]]) -> tuple[float, float]:
    return (-math.pi, math.pi) if r is None else (float(r[0]), float(r[1]))


def _limit_diffs(cand: _Side, ref: _Side, mapping: Mapping, conv: list[JointConvention],
                 notes: list[str]) -> tuple[list[JointLimitDiff], float]:
    diffs, hinge_abs = [], []
    unlimited = []
    for i, (cn, rn) in enumerate(zip(mapping.candidate.joints, mapping.reference.joints)):
        cr, rr, c = cand.ranges[i], ref.ranges[i], conv[i]
        rref = _own_range(rr)
        if cr is None and rr is None:
            cref = rref
        else:
            lo, hi = _own_range(cr)
            a, b = c.sign * lo + c.offset, c.sign * hi + c.offset
            cref = (min(a, b), max(a, b))
            if cr is None:
                unlimited.append(f"candidate {cn}")
            if rr is None:
                unlimited.append(f"reference {rn}")
        d = JointLimitDiff(candidate=cn, reference=rn, candidate_range=[cref[0], cref[1]],
                           reference_range=[rref[0], rref[1]], lower_diff=cref[0] - rref[0],
                           upper_diff=cref[1] - rref[1])
        diffs.append(d)
        if cand.jtypes[i] == _HINGE and ref.jtypes[i] == _HINGE:
            hinge_abs += [abs(d.lower_diff), abs(d.upper_diff)]
    if unlimited:
        notes.append("unlimited joints compared as [-pi, pi] against a limited counterpart: "
                     + ", ".join(unlimited))
    mae = float(np.degrees(np.mean(hinge_abs))) if hinge_abs else 0.0
    return diffs, mae


# --------------------------------------------------------------------------- #
# Convention fitting
# --------------------------------------------------------------------------- #


def _uniform(rng: np.random.Generator, bounds: list[tuple[float, float]], n: int) -> np.ndarray:
    lo = np.array([b[0] for b in bounds])
    hi = np.array([b[1] for b in bounds])
    return lo + (hi - lo) * rng.random((n, len(bounds)))


def fit_conventions(cand: _Side, ref: _Side, Q: np.ndarray,
                    sweeps: int = FIT_SWEEPS) -> list[JointConvention]:
    """Discrete per-hinge sign/offset fit by coordinate descent (see module docstring)."""
    n = len(cand.jtypes)
    Pc, Rc = cand.fk(Q)
    conv = [JointConvention() for _ in range(n)]
    fittable = [i for i in range(n) if cand.jtypes[i] == _HINGE and ref.jtypes[i] == _HINGE]
    options = [(s, o) for s in (1, -1) for o in OFFSET_CHOICES]

    def cost(cv: list[JointConvention]) -> tuple[float, float]:
        Pr, Rr = ref.fk(_apply(cv, Q))
        pos = float(np.mean(np.linalg.norm(Pc - Pr, axis=1)))
        ori = float(np.mean(_aligned_angles(Rc, Rr)))
        return pos, ori

    for _ in range(sweeps):
        for i in fittable:
            cur = (conv[i].sign, conv[i].offset)
            ordered = [cur] + [o for o in options if o != cur]
            results = []
            for s, o in ordered:
                trial = list(conv)
                trial[i] = JointConvention(sign=s, offset=o)
                results.append(((s, o), *cost(trial)))
            best_pos = min(r[1] for r in results)
            near = [r for r in results if r[1] <= best_pos + 1e-9 + 1e-6 * best_pos]
            best_ori = min(r[2] for r in near)
            choice = next(r for r in near if r[2] <= best_ori + 1e-9)
            conv[i] = JointConvention(sign=choice[0][0], offset=choice[0][1])
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
    cand = _load_side("candidate", candidate_path, mapping.candidate.joints, mapping.candidate.ee)
    ref = _load_side("reference", reference_path, mapping.reference.joints, mapping.reference.ee)
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

    # -- conventions ------------------------------------------------------------
    if mapping.joint_conventions is not None:
        conv = list(mapping.joint_conventions)
        fitted = False
    elif mapping.fit_conventions:
        fit_bounds = [_own_range(r) for r in cand.ranges]
        Qfit = _uniform(rng, fit_bounds, N_FIT_CONFIGS)
        conv = fit_conventions(cand, ref, Qfit)
        fitted = True
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
        lo, hi, empty = sampling_interval(cand.ranges[i], ref.ranges[i], conv[i])
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
        conventions=conv, conventions_fitted=fitted,
        ee_position_error_mm=pos_stats, ee_orientation_error_deg=_stats(raw_deg),
        ee_orientation_error_aligned_deg=aligned_stats,
        joint_limits=limit_diffs, joint_limit_mae_deg=limit_mae,
        mass_candidate=mass_c, mass_reference=mass_r, mass_diff=mass_diff, mass_rel_diff=mass_rel,
        score=score, score_breakdown=breakdown, notes=notes,
    )
