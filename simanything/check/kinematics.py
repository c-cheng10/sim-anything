"""Kinematic checks: kinematics_match and reach (see docs/CONTRACTS.md section 4)."""

from __future__ import annotations

import math
from typing import Callable, Optional

import mujoco
import numpy as np

from ..schemas import CheckResult
from ..spec import is_estimate, make_tf, rpy_to_mat, sample_configs
from .context import HINGE, JOINT_TYPE_NAMES, CheckContext, result, skipped_no_spec

REACH_TOL = 0.05  # relative
REFINE_TOP = 8  # best samples refined by local search
REFINE_ITERS = 60
WRIST_MIN_DOF = 3  # below this, reach.measured_to = wrist_center falls back to the EE site


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


REACH_GROSS_TOL = 0.30  # beyond this a reach mismatch is always an error


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
    to_ee = reach.measured_to == "ee_site" or spec.dof < WRIST_MIN_DOF
    if to_ee and reach.measured_to == "wrist_center":
        notes.append(f"wrist_center needs at least {WRIST_MIN_DOF} joints (the body of joint dof-2 would be at or "
                     f"before the shoulder); with dof={spec.dof} the EE site is used instead")
    if to_ee:
        sid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, spec.ee.name)
        if sid < 0:
            return result("reach", False, expected=reach.value, tolerance=REACH_TOL,
                          message=f"cannot measure reach: no site '{spec.ee.name}' (see ee_site)",
                          fix_hint="Fix the ee_site failure first: the model needs a site named ee.name.")
        point = lambda: d.site_xpos[sid]
        to_desc = f"site '{spec.ee.name}'"
    else:
        k = spec.dof - 2
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
    def_fields = ("reach.measured_from", "reach.measured_to")
    # a definition field left at its default (not written in the spec) is assumed, like an estimate
    written = raw.reach.model_fields_set if raw.reach is not None else set()
    unstated = [f for f in def_fields if f.split(".")[1] not in written]
    listed = [f for f in def_fields if f not in unstated and is_estimate(raw, f)]
    def_est = unstated + listed
    value_est = is_estimate(raw, "reach.value")
    details["definition_estimated"] = bool(def_est)
    details["definition_unstated"] = unstated
    details["value_estimated"] = value_est
    assumed = (f"{'reach definition' if len(unstated) == 2 else unstated[0] if unstated else ''} not stated in "
               f"the spec; assumed {reach.measured_from} -> {reach.measured_to}") if unstated else ""
    if abs(rel) <= REACH_TOL:
        return result("reach", True, measured=measured, expected=expected, tolerance=REACH_TOL,
                      message=(f"max reach {_fmt_m(measured)} m within {abs(rel) * 100:.1f}% of rated "
                               f"{_fmt_m(expected)} m" + (f" ({assumed})" if assumed else "")),
                      details=details)
    too_long = rel > 0
    gross = abs(rel) > REACH_GROSS_TOL
    msg = (f"max reach {_fmt_m(measured)} m is {abs(rel) * 100:.1f}% {'above' if too_long else 'below'} "
           f"rated {_fmt_m(expected)} m")
    caveats = []
    if assumed:
        caveats.append(assumed)
    if listed:
        caveats.append(f"the reach definition is assumed ({' and '.join(listed)} listed in estimates)")
    if value_est:
        caveats.append("reach.value is an estimate")
    if gross:
        # no reach definition explains a mismatch this large: units or structure are wrong
        msg += (f"; more than {REACH_GROSS_TOL * 100:.0f}% off, so this stays an error even if the reach "
                "definition or value is estimated (check `units.length` and the link lengths)")
        if caveats:
            msg += " (" + "; ".join(caveats) + ")"
    elif caveats:
        msg += "; warning only: " + "; ".join(caveats)
    try:
        lengths = _reach_sensitivities(spec, reach, shoulder_i, best_q, len(jids))
    except Exception:  # noqa: BLE001 - the hint must not crash the check
        lengths = []
    details["length_sensitivity"] = {p: e for p, e in lengths}
    return result("reach", False, severity="warning" if caveats and not gross else "error", measured=measured,
                  expected=expected, tolerance=REACH_TOL, message=msg,
                  fix_hint=_reach_hint(ctx, too_long, [p for p, _ in lengths[:4]], def_est, value_est, gross),
                  details=details)


def _fmt_m(x: float) -> str:
    """A length in m: 3 decimals, or 3 significant digits below 0.1 m (0.0009, not 0.001)."""
    return f"{x:.3f}" if abs(x) >= 0.1 else f"{x:.3g}"


def _reach_metric_spec(spec, reach, shoulder_i: int, q: np.ndarray, qhome: np.ndarray) -> float:
    """The reach metric of ``spec`` (SI) at configuration ``q``, computed with the spec's own FK."""
    ch = spec.chain()
    if reach.measured_to == "ee_site" or spec.dof < WRIST_MIN_DOF:
        p = ch.fk(q)[:3, 3]
    else:
        p = ch.fk(q, upto=spec.dof - 2)[:3, 3]
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
    """Spec lengths ranked by their effect on the reach metric at the configuration of maximum reach
    (to first order the argmax does not move); see ``_length_sensitivities``."""
    if n_matched != spec.dof:
        return []
    qhome = np.array([j.home for j in spec.joints], dtype=float)
    q = np.asarray(best_q, dtype=float)
    return _length_sensitivities(spec, lambda s: _reach_metric_spec(s, reach, shoulder_i, q, qhome))


def _length_sensitivities(spec, metric: Callable) -> list[tuple[str, float]]:
    """(spec length path, effect), largest |effect| first, where effect = d(metric)/d(ln length) and
    ``metric(spec_si) -> float``. Lengths that do not change the metric (e.g. an offset along the
    first axis for a horizontal distance, or anything before the shoulder) are left out."""
    base = metric(spec)
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
        eff = (metric(s2) - base) / h
        if abs(eff) > 1e-3 * max(abs(base), 1e-9):
            out.append((path, float(eff)))
    out.sort(key=lambda pe: -abs(pe[1]))
    return out


def _reach_hint(ctx: CheckContext, too_long: bool, lengths: list[str], def_est: list[str], value_est: bool,
                gross: bool = False) -> str:
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
                     f"assumed ({', '.join(def_est)} not stated in the spec or listed in estimates), "
                     + ("but no reach definition explains a mismatch this large, so this stays an error."
                        if gross else "so this is only a warning."))
    else:
        parts.append(f"Confirm the source's reach definition: reach.measured_to = {r.measured_to} (vs {other_to}), "
                     f"reach.measured_from = {r.measured_from}.")
    parts.append("If the source does not state the reach definition, leave reach.measured_from/measured_to "
                 "unstated or list them in `estimates` instead of switching endpoints until it passes; if it "
                 "does, write them in the spec and source them.")
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
    Q = sample_configs(spec, n_samples, seed)
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


# --------------------------------------------------------------------------- #
# drawing: the model at a drawn pose vs dimensions read off a published drawing
# --------------------------------------------------------------------------- #

DRAWING_TOL = 0.002  # m, default per dimension


def _drawing_measure(measure: str, p: np.ndarray, T_base: np.ndarray, anchor: np.ndarray, axis: np.ndarray
                     ) -> float:
    if measure == "height":
        return float((T_base[:3, :3].T @ (p - T_base[:3, 3]))[2])
    v = p - anchor
    return float(np.linalg.norm(v - np.dot(v, axis) * axis))


def check_drawing(ctx: CheckContext) -> CheckResult:
    """The model's EE site (or wrist centre) at each drawn pose vs ``spec.drawing``."""
    cid = "drawing"
    if not ctx.has_spec:
        return skipped_no_spec(cid)
    m, d, spec = ctx.model, ctx.data, ctx.spec
    assert m is not None and d is not None and spec is not None
    if not spec.drawing:
        return result(cid, True, severity="info",
                      message="no drawing dimensions in the spec; the zero pose is not checked against a drawing")
    if any(jid is None for jid in ctx.joint_ids):
        return result(cid, False, severity="info", message="skipped: not every spec joint is in the model",
                      fix_hint="Fix the joint_structure failure first.")
    sid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, spec.ee.name)
    qadr = np.array([m.jnt_qposadr[j] for j in ctx.joint_ids], dtype=int)  # type: ignore[misc]
    jw = ctx.joint_ids[spec.dof - 2] if spec.dof >= WRIST_MIN_DOF else None
    T_base = make_tf(rpy_to_mat(spec.base.origin.rpy), spec.base.origin.xyz)
    raw = ctx.spec_raw if ctx.spec_raw is not None else spec
    rows, failed = [], []
    for i, dim in enumerate(spec.drawing):
        q = np.zeros(spec.dof) if dim.q is None else np.asarray(dim.q, dtype=float)
        mujoco.mj_resetData(m, d)
        d.qpos[:] = ctx.home_qpos
        d.qpos[qadr] = q
        mujoco.mj_kinematics(m, d)
        if dim.point == "wrist_center" and jw is not None:
            p = d.xpos[int(m.jnt_bodyid[jw])].copy()
        elif sid >= 0:
            p = d.site_xpos[sid].copy()
        else:
            return result(cid, False, severity="info", message=f"skipped: no site '{spec.ee.name}' (see ee_site)",
                          fix_hint="Fix the ee_site failure first.")
        j0 = int(ctx.joint_ids[0])  # type: ignore[arg-type]
        measured = _drawing_measure(dim.measure, p, T_base, d.xanchor[j0].copy(), d.xaxis[j0].copy())
        tol = dim.tolerance or DRAWING_TOL
        estimated = is_estimate(raw, f"drawing[{i}].value")
        row = {"index": i, "measure": dim.measure, "point": dim.point, "measured": measured, "expected": dim.value,
               "tolerance": tol, "estimated": estimated}
        rows.append(row)
        if abs(measured - dim.value) > tol:
            failed.append(row)
    details = {"dimensions": rows}
    if not failed:
        return result(cid, True, measured=[r["measured"] for r in rows], expected=[r["expected"] for r in rows],
                      message=f"{len(rows)} drawing dimension(s) match within tolerance", details=details)
    msgs, hints = [], []
    for r in failed:
        dim = spec.drawing[r["index"]]
        msgs.append(f"drawing[{r['index']}] {r['measure']} of {r['point']}: model {r['measured'] * 1000:.1f} mm vs "
                    f"drawing {r['expected'] * 1000:.1f} mm (tolerance {r['tolerance'] * 1000:.1f} mm)")
        q = np.zeros(spec.dof) if dim.q is None else np.asarray(dim.q, dtype=float)

        def metric(s, dim=dim, q=q) -> float:
            ch = s.chain()
            T = ch.fk(q, upto=s.dof - 2) if dim.point == "wrist_center" and s.dof >= WRIST_MIN_DOF else ch.fk(q)
            T0 = ch.fk(q, upto=0)
            ax = T0[:3, :3] @ np.asarray(ch.joints[0].axis, dtype=float)
            return _drawing_measure(dim.measure, T[:3, 3], T_base, T0[:3, 3], ax / np.linalg.norm(ax))

        try:
            lengths = [p for p, _ in _length_sensitivities(spec, metric)[:4]]
        except Exception:  # noqa: BLE001 - the hint must not crash the check
            lengths = []
        r["length_sensitivity"] = lengths
        hints.append(f"drawing[{r['index']}]: re-check the lengths that set it ({', '.join(lengths) or 'link offsets'};"
                     " largest effect first)")
    hint = ("; ".join(hints) + ". A mismatch here with a passing reach usually means a misread table row (row shift "
            "a_{i-1} vs a_i, a missing offset, a wrong sign or theta offset) or a drawing pose that is not q = 0 "
            "(set drawing[i].q to the drawn pose). Check `units.length` too. Never change a sourced number to pass: "
            "fix the interpretation, or list the dimension in `estimates` if its mapping to the arm was your "
            "inference.")
    severity = "warning" if all(r["estimated"] for r in failed) else "error"
    return result(cid, False, severity=severity, measured=[r["measured"] for r in rows],
                  expected=[r["expected"] for r in rows], message="; ".join(msgs)
                  + ("; warning only: the dimension(s) are estimates" if severity == "warning" else ""),
                  fix_hint=hint, details=details)
