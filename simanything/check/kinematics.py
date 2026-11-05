"""Kinematic checks: kinematics_match and reach (see docs/CONTRACTS.md section 4)."""

from __future__ import annotations

import math
from typing import Callable, Optional

import mujoco
import numpy as np

from ..schemas import CheckResult
from ..spec import is_estimate
from .context import HINGE, JOINT_TYPE_NAMES, CheckContext, result, skipped_no_spec

REACH_TOL = 0.05  # relative
REFINE_TOP = 8  # best samples refined by local search
REFINE_ITERS = 60


def _sample_ranges(ctx: CheckContext, jids: list[int]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    m = ctx.model
    assert m is not None
    lo, hi, notes = [], [], []
    for jid in jids:
        if m.jnt_limited[jid]:
            a, b = (float(x) for x in m.jnt_range[jid])
        elif int(m.jnt_type[jid]) == HINGE:
            a, b = -math.pi, math.pi
        else:
            a = b = float(ctx.home_qpos[m.jnt_qposadr[jid]])  # type: ignore[index]
            notes.append(f"slide joint '{ctx.joint_name(jid)}' is unlimited; held at home for reach sampling")
        lo.append(a)
        hi.append(b)
    return np.array(lo), np.array(hi), notes


def check_reach(ctx: CheckContext, *, seed: int = 0, n_samples: int = 5000) -> CheckResult:
    if not ctx.has_spec:
        return skipped_no_spec("reach")
    m, d, spec = ctx.model, ctx.data, ctx.spec
    assert m is not None and d is not None and spec is not None
    if spec.reach is None:
        return result("reach", False, severity="warning",
                      message="no rated reach: the chain is not checked against any external dimension",
                      fix_hint="Add `reach` (value, measured_from, measured_to) from the datasheet with a source; it "
                               "is the main cross-check of the link lengths. If the source gives no reach, keep it "
                               "absent and say so in `notes`.")
    reach = spec.reach
    matched = ctx.matched()
    if not matched:
        return result("reach", False, expected=reach.value, tolerance=REACH_TOL,
                      message="no spec joint found in the model; cannot measure reach",
                      fix_hint="Fix the joint_structure failure first (joint names must equal joints[i].name).")
    jids = [jid for _, jid in matched]
    qhome = np.asarray(ctx.home_qpos, dtype=float)
    mujoco.mj_resetData(m, d)
    d.qpos[:] = qhome
    mujoco.mj_kinematics(m, d)
    notes: list[str] = []

    # ---- origin of the measurement (fixed point/line, evaluated at home) ----
    origin_desc = reach.measured_from
    shoulder_i = matched[0][0]  # spec index of the joint whose body origin is the shoulder
    if reach.measured_from == "shoulder":
        b_first = int(m.jnt_bodyid[jids[0]])
        if len(jids) == 1:
            b, origin_desc = b_first, f"body '{ctx.body_name(b_first)}' (1st joint)"
        else:
            b_second = int(m.jnt_bodyid[jids[1]])
            both_hinge = int(m.jnt_type[jids[0]]) == HINGE and int(m.jnt_type[jids[1]]) == HINGE
            parallel = both_hinge and abs(float(np.dot(d.xaxis[jids[0]], d.xaxis[jids[1]]))) > 1 - 1e-6
            if parallel:
                # planar/SCARA-like arm: the first joint is the shoulder
                b = b_first
                origin_desc = f"body '{ctx.body_name(b)}' (1st joint; axes of joints 1 and 2 are parallel)"
                notes.append("first two joint axes are parallel, so the shoulder is taken at the 1st joint")
            else:
                b, origin_desc = b_second, f"body '{ctx.body_name(b_second)}' (2nd joint)"
                shoulder_i = matched[1][0]
        o = d.xpos[b].copy()
        dist: Callable[[np.ndarray], float] = lambda p: float(np.linalg.norm(p - o))
    elif reach.measured_from == "base_origin":
        bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "base")
        if bid >= 0:
            o = d.xpos[bid].copy()
            origin_desc = "body 'base'"
        else:
            o = np.asarray(spec.base.origin.xyz, dtype=float)
            origin_desc = "spec base.origin (no body named 'base')"
        dist = lambda p: float(np.linalg.norm(p - o))
    else:  # base_axis_horizontal
        a0 = d.xanchor[jids[0]].copy()
        u = d.xaxis[jids[0]].copy()
        u /= np.linalg.norm(u)
        origin_desc = f"axis of joint '{ctx.joint_name(jids[0])}'"

        def dist(p: np.ndarray) -> float:
            v = p - a0
            return float(np.linalg.norm(v - np.dot(v, u) * u))

    # ---- measured point ----
    point: Callable[[], np.ndarray]
    if reach.measured_to == "ee_site":
        sid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, spec.ee.name)
        if sid < 0:
            return result("reach", False, expected=reach.value, tolerance=REACH_TOL,
                          message=f"cannot measure reach: no site '{spec.ee.name}' (see ee_site)",
                          fix_hint="Fix the ee_site failure first: the model needs a site named ee.name.")
        point = lambda: d.site_xpos[sid]
        to_desc = f"site '{spec.ee.name}'"
    else:
        k = max(spec.dof - 2, 0)
        jid_w = ctx.joint_ids[k]
        if jid_w is None:
            return result("reach", False, expected=reach.value, tolerance=REACH_TOL,
                          message=f"cannot measure reach: wrist joint joints[{k}] not found in the model",
                          fix_hint="Fix the joint_structure failure first.")
        bw = int(m.jnt_bodyid[jid_w])
        point = lambda: d.xpos[bw]
        to_desc = f"origin of body '{ctx.body_name(bw)}' (joints[{k}], wrist centre)"

    # ---- sampling ----
    lo, hi, n2 = _sample_ranges(ctx, jids)
    notes += n2
    qadr = np.array([m.jnt_qposadr[j] for j in jids], dtype=int)
    rng = np.random.default_rng(seed)
    Q = rng.uniform(lo, hi, size=(n_samples, len(jids)))

    def metric(q: np.ndarray) -> float:
        d.qpos[qadr] = q
        mujoco.mj_kinematics(m, d)
        return dist(point())

    d.qpos[:] = qhome
    vals = np.fromiter((metric(q) for q in Q), dtype=float, count=n_samples)
    sample_max = float(np.max(vals))

    # ---- local refinement of the best samples (random sampling under-estimates the max) ----
    best = sample_max
    best_q = Q[int(np.argmax(vals))].copy()
    span = hi - lo
    rng_ref = np.random.default_rng(seed + 1)
    for idx in np.argsort(vals)[::-1][:REFINE_TOP]:
        q, f = Q[idx].copy(), float(vals[idx])
        step = 0.1 * span
        for _ in range(REFINE_ITERS):
            cand = np.clip(q + rng_ref.normal(size=q.shape) * step, lo, hi)
            fc = metric(cand)
            if fc > f:
                q, f = cand, fc
            else:
                step *= 0.93
        if f > best:
            best, best_q = f, q
    measured = best
    expected = float(reach.value)
    rel = (measured - expected) / expected
    details = {
        "samples": n_samples, "seed": seed, "sample_max": sample_max, "refined_max": measured,
        "relative_error": rel, "measured_from": reach.measured_from, "measured_to": reach.measured_to,
        "origin": origin_desc, "point": to_desc, "home_source": ctx.home_source,
        "argmax_q": {ctx.joint_name(j): float(x) for j, x in zip(jids, best_q)},
    }
    if notes:
        details["notes"] = notes
    raw = ctx.spec_raw if ctx.spec_raw is not None else spec
    def_est = [f for f in ("reach.measured_from", "reach.measured_to") if is_estimate(raw, f)]
    value_est = is_estimate(raw, "reach.value")
    details["definition_estimated"] = bool(def_est)
    details["value_estimated"] = value_est
    if abs(rel) <= REACH_TOL:
        return result("reach", True, measured=measured, expected=expected, tolerance=REACH_TOL,
                      message=f"max reach {measured:.3f} m within {abs(rel) * 100:.1f}% of rated {expected:.3f} m",
                      details=details)
    too_long = rel > 0
    msg = (f"max reach {measured:.3f} m is {abs(rel) * 100:.1f}% {'above' if too_long else 'below'} "
           f"rated {expected:.3f} m")
    caveats = []
    if def_est:
        caveats.append(f"the reach definition is assumed ({' and '.join(def_est)} listed in estimates)")
    if value_est:
        caveats.append("reach.value is an estimate")
    if caveats:
        msg += "; warning only: " + "; ".join(caveats)
    try:
        lengths = _reach_sensitivities(spec, reach, shoulder_i, best_q, len(jids))
    except Exception:  # noqa: BLE001 - the hint must not crash the check
        lengths = []
    details["length_sensitivity"] = {p: e for p, e in lengths}
    return result("reach", False, severity="warning" if caveats else "error", measured=measured,
                  expected=expected, tolerance=REACH_TOL, message=msg,
                  fix_hint=_reach_hint(ctx, too_long, [p for p, _ in lengths[:4]], bool(def_est), value_est),
                  details=details)


def _reach_metric_spec(spec, reach, shoulder_i: int, q: np.ndarray, qhome: np.ndarray) -> float:
    """The reach metric of ``spec`` (SI) at configuration ``q``, computed with the spec's own FK."""
    ch = spec.chain()
    if reach.measured_to == "ee_site":
        p = ch.fk(q)[:3, 3]
    else:
        p = ch.fk(q, upto=max(spec.dof - 2, 0))[:3, 3]
    if reach.measured_from == "shoulder":
        return float(np.linalg.norm(p - ch.fk(qhome, upto=shoulder_i)[:3, 3]))
    if reach.measured_from == "base_origin":
        return float(np.linalg.norm(p - np.asarray(ch.base_pos)))
    T0 = ch.fk(qhome, upto=0)
    u = T0[:3, :3] @ np.asarray(ch.joints[0].axis, dtype=float)
    u /= np.linalg.norm(u)
    v = p - T0[:3, 3]
    return float(np.linalg.norm(v - np.dot(v, u) * u))


def _reach_sensitivities(spec, reach, shoulder_i: int, best_q: np.ndarray, n_matched: int
                         ) -> list[tuple[str, float]]:
    """(spec length path, effect), largest |effect| first, where effect = d(reach metric)/d(ln length)
    at the configuration of maximum reach (to first order the argmax does not move). Lengths that do
    not change the measured quantity (e.g. an offset along the first axis for base_axis_horizontal,
    or anything before the shoulder) are left out."""
    if n_matched != spec.dof:
        return []
    qhome = np.array([j.home for j in spec.joints], dtype=float)
    q = np.asarray(best_q, dtype=float)
    base = _reach_metric_spec(spec, reach, shoulder_i, q, qhome)
    h = 1e-4

    def scale_dh(i: int, f: str) -> Callable:
        return lambda s: setattr(s.joints[i].dh, f, getattr(s.joints[i].dh, f) * (1 + h))

    def scale_xyz(get: Callable) -> Callable:
        return lambda s: setattr(get(s), "xyz", [x * (1 + h) for x in get(s).xyz])

    params: list[tuple[str, Callable]] = []
    for i, j in enumerate(spec.joints):
        if j.dh is not None:
            params += [(f"joints[{i}].dh.{f}", scale_dh(i, f)) for f in ("a", "d") if abs(getattr(j.dh, f)) > 0]
        elif j.origin is not None and float(np.linalg.norm(j.origin.xyz)) > 0:
            params.append((f"joints[{i}].origin.xyz", scale_xyz(lambda s, i=i: s.joints[i].origin)))
    if float(np.linalg.norm(spec.ee.origin.xyz)) > 0:
        params.append(("ee.origin.xyz", scale_xyz(lambda s: s.ee.origin)))
    out = []
    for path, bump in params:
        s2 = spec.model_copy(deep=True)
        bump(s2)
        eff = (_reach_metric_spec(s2, reach, shoulder_i, q, qhome) - base) / h
        if abs(eff) > 1e-3 * max(base, 1e-9):
            out.append((path, float(eff)))
    out.sort(key=lambda pe: -abs(pe[1]))
    return out


def _reach_hint(ctx: CheckContext, too_long: bool, lengths: list[str], def_est: bool, value_est: bool) -> str:
    spec = ctx.spec
    assert spec is not None and spec.reach is not None
    r = spec.reach
    names = ", ".join(lengths) if lengths else "the link offsets"
    first = (f"Reach is too {'long' if too_long else 'short'}: re-check the lengths that set the measured reach "
             f"({names}; largest effect first) against the datasheet")
    if not too_long:
        extra = []
        if r.measured_to == "ee_site" and "ee.origin.xyz" not in lengths:
            extra.append("a missing EE/flange offset (ee.origin.xyz)")
        if spec.convention != "offset":
            extra.append("DH signs/offsets (joints[*].dh.alpha, theta_offset)")
        extra.append("joint limits that may prevent stretching out (joints[*].limits)")
        first += ", " + ", ".join(extra)
    parts = [first + ". Also check `units.length` (mm vs m)."]
    if value_est:
        parts.append("reach.value is itself an estimate: re-check it, or find a source for it.")
    other_to = "wrist_center" if r.measured_to == "ee_site" else "ee_site"
    if def_est:
        parts.append(f"The reach definition (measured_from = {r.measured_from}, measured_to = {r.measured_to}) is "
                     "assumed, so this is only a warning.")
    else:
        parts.append(f"Confirm the source's reach definition: reach.measured_to = {r.measured_to} (vs {other_to}), "
                     f"reach.measured_from = {r.measured_from}.")
    parts.append("If the source does not state the reach definition, list reach.measured_from/measured_to in "
                 "`estimates` instead of switching endpoints until it passes.")
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# kinematics_match: the model's kinematics vs Spec.chain()
# --------------------------------------------------------------------------- #

KIN_POS_TOL = 1e-6  # m
KIN_ROT_TOL = 1e-6  # rad
KIN_SAMPLES = 20  # home + 19 seeded random configurations


def _rot_angle(Ra: np.ndarray, Rb: np.ndarray) -> float:
    """Geodesic angle between two rotation matrices (accurate for small angles)."""
    s = float(np.linalg.norm(Ra - Rb)) / (2.0 * math.sqrt(2.0))
    return 2.0 * math.asin(min(1.0, s))


def _vec_angle(a: np.ndarray, b: np.ndarray) -> float:
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    return 2.0 * math.asin(min(1.0, float(np.linalg.norm(a - b)) / 2.0))


def kinematic_configs(spec, n: int, seed: int) -> np.ndarray:
    """Home plus ``n - 1`` seeded uniform configurations within the spec limits (SI).
    Unlimited hinges use [-pi, pi], unlimited slides [-0.1, 0.1] m."""
    rng = np.random.default_rng(seed)
    lo = np.array([j.limits.lower if j.limits else (-math.pi if j.type == "hinge" else -0.1) for j in spec.joints])
    hi = np.array([j.limits.upper if j.limits else (math.pi if j.type == "hinge" else 0.1) for j in spec.joints])
    home = np.array([j.home for j in spec.joints], dtype=float)
    return np.vstack([home[None, :], rng.uniform(lo, hi, size=(max(n - 1, 0), len(lo)))])


def check_kinematics_match(ctx: CheckContext, *, seed: int = 0, n_samples: int = KIN_SAMPLES) -> CheckResult:
    """EE site pose and every joint axis (direction and, for hinges, its line) of the model vs
    ``spec.chain()`` on ``n_samples`` configurations."""
    cid = "kinematics_match"
    if not ctx.has_spec:
        return skipped_no_spec(cid)
    m, d, spec = ctx.model, ctx.data, ctx.spec
    assert m is not None and d is not None and spec is not None
    blocked = (any(jid is None for jid in ctx.joint_ids) or m.njnt != spec.dof
               or any(JOINT_TYPE_NAMES.get(int(m.jnt_type[jid]), "?") != j.type
                      for j, jid in zip(spec.joints, ctx.joint_ids) if jid is not None))
    if blocked:
        return result(cid, False, severity="info", message="skipped: the model's joints do not match the spec",
                      fix_hint="Fix the joint_structure failure first; this check runs once every spec joint is in "
                               "the model with the right type and no other joints exist.")
    sid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, spec.ee.name)
    if sid < 0:
        return result(cid, False, severity="info", message=f"skipped: no site '{spec.ee.name}' (see ee_site)",
                      fix_hint="Fix the ee_site failure first.")
    chain = spec.chain()
    jids = [int(j) for j in ctx.joint_ids]  # type: ignore[arg-type]
    qadr = np.array([m.jnt_qposadr[j] for j in jids], dtype=int)
    Q = kinematic_configs(spec, n_samples, seed)
    ee_pos = ee_rot = 0.0
    axis_err = np.zeros(len(jids))   # rad, joint axis direction (sign included)
    line_err = np.zeros(len(jids))   # m, hinge anchor distance from the spec axis line
    worst_q = Q[0]
    for q in Q:
        mujoco.mj_resetData(m, d)
        d.qpos[:] = ctx.home_qpos
        d.qpos[qadr] = q
        mujoco.mj_kinematics(m, d)
        T = chain.fk(q)
        pe = float(np.linalg.norm(d.site_xpos[sid] - T[:3, 3]))
        re = _rot_angle(d.site_xmat[sid].reshape(3, 3), T[:3, :3])
        if pe > ee_pos:
            worst_q = q
        ee_pos, ee_rot = max(ee_pos, pe), max(ee_rot, re)
        for i, (jid, cj) in enumerate(zip(jids, chain.joints)):
            Ti = chain.fk(q, upto=i)
            a_spec = Ti[:3, :3] @ np.asarray(cj.axis, dtype=float)
            a_spec /= np.linalg.norm(a_spec)
            axis_err[i] = max(axis_err[i], _vec_angle(np.array(d.xaxis[jid]), a_spec))
            if cj.type == "hinge":
                v = d.xanchor[jid] - Ti[:3, 3]
                line_err[i] = max(line_err[i], float(np.linalg.norm(v - np.dot(v, a_spec) * a_spec)))
    measured = {"ee_position_m": ee_pos, "ee_orientation_rad": ee_rot,
                "joint_axis_rad": float(np.max(axis_err)), "joint_position_m": float(np.max(line_err))}
    tol = {"position_m": KIN_POS_TOL, "orientation_rad": KIN_ROT_TOL}
    details = {
        "samples": len(Q), "seed": seed,
        "joints": [{"joint": spec.joints[i].name, "axis_error_rad": float(axis_err[i]),
                    "axis_line_offset_m": float(line_err[i])} for i in range(len(jids))],
    }
    ok = (ee_pos <= KIN_POS_TOL and ee_rot <= KIN_ROT_TOL and bool(np.all(axis_err <= KIN_ROT_TOL))
          and bool(np.all(line_err <= KIN_POS_TOL)))
    if ok:
        return result(cid, True, measured=measured, expected=0.0, tolerance=tol,
                      message=f"model kinematics match the spec on {len(Q)} configurations (max EE error "
                              f"{ee_pos:.1e} m, {ee_rot:.1e} rad)", details=details)
    details["worst_q"] = {spec.joints[i].name: float(x) for i, x in enumerate(worst_q)}
    parts = [f"model kinematics differ from the spec: max EE error {ee_pos * 1000:.3f} mm / "
             f"{math.degrees(ee_rot):.3f} deg over {len(Q)} configurations"]
    hints = []
    bad_j = [i for i in range(len(jids)) if axis_err[i] > KIN_ROT_TOL or line_err[i] > KIN_POS_TOL]
    if bad_j:
        i = bad_j[0]
        what = []
        if axis_err[i] > KIN_ROT_TOL:
            what.append(f"its axis is {math.degrees(axis_err[i]):.2f} deg off")
        if line_err[i] > KIN_POS_TOL:
            what.append(f"it sits {line_err[i] * 1000:.2f} mm off the spec's axis line")
        parts.append(f"first mismatching joint '{spec.joints[i].name}' (joints[{i}]): {' and '.join(what)}")
        hints.append(f"The first joint whose placement or axis differs from the spec is joints[{i}] "
                     f"'{spec.joints[i].name}': compare its body pos/quat and joint axis in the MJCF with the "
                     "spec offsets / DH rows leading to it.")
    else:
        hints.append(f"All joint axes match; the pose of site '{spec.ee.name}' differs (compare the site pos/quat "
                     "in the MJCF with ee.origin).")
    hints.append("The MJCF was edited by hand or built from a different spec: rebuild it from this spec "
                 "(`sim-anything build`). If the hand edit is intentional (an exotic mechanism the spec cannot "
                 "express), explain it in the spec's `notes`.")
    return result(cid, False, measured=measured, expected=0.0, tolerance=tol, message="; ".join(parts),
                  fix_hint=" ".join(hints), details=details)
