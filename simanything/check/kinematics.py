"""Kinematic check: reach (see docs/CONTRACTS.md section 4, reach metric)."""

from __future__ import annotations

import math
from typing import Callable, Optional

import mujoco
import numpy as np

from ..schemas import CheckResult
from .context import HINGE, CheckContext, result, skipped_no_spec

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
        return result("reach", True, severity="info", message="spec has no reach; not checked")
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
    if abs(rel) <= REACH_TOL:
        return result("reach", True, measured=measured, expected=expected, tolerance=REACH_TOL,
                      message=f"max reach {measured:.3f} m within {abs(rel) * 100:.1f}% of rated {expected:.3f} m",
                      details=details)
    too_long = rel > 0
    return result("reach", False, measured=measured, expected=expected, tolerance=REACH_TOL,
                  message=f"max reach {measured:.3f} m is {abs(rel) * 100:.1f}% {'above' if too_long else 'below'} "
                          f"rated {expected:.3f} m",
                  fix_hint=_reach_hint(ctx, too_long), details=details)


def _reach_hint(ctx: CheckContext, too_long: bool) -> str:
    spec = ctx.spec
    assert spec is not None and spec.reach is not None
    # the largest length contributions in the chain, so the agent knows where to look first
    contrib: list[tuple[float, str]] = []
    for i, j in enumerate(spec.joints):
        if j.dh is not None:
            if abs(j.dh.a) > 0:
                contrib.append((abs(j.dh.a), f"joints[{i}].dh.a"))
            if abs(j.dh.d) > 0:
                contrib.append((abs(j.dh.d), f"joints[{i}].dh.d"))
        elif j.origin is not None:
            n = float(np.linalg.norm(j.origin.xyz))
            if n > 0:
                contrib.append((n, f"joints[{i}].origin.xyz"))
    en = float(np.linalg.norm(spec.ee.origin.xyz))
    if en > 0:
        contrib.append((en, "ee.origin.xyz"))
    top = [p for _, p in sorted(contrib, reverse=True)[:4]]
    lengths = ", ".join(top) if top else "the link offsets"
    r = spec.reach
    other_to = "wrist_center" if r.measured_to == "ee_site" else "ee_site"
    if too_long:
        s = (f"Reach is too long: re-check the link lengths ({lengths}) against the datasheet, the EE offset "
             f"(ee.origin.xyz), and whether the rated reach is measured to the {other_to.replace('_', ' ')} "
             f"rather than the {r.measured_to.replace('_', ' ')} (reach.measured_to) or from a different point "
             f"(reach.measured_from = {r.measured_from}). Also check `units.length` (mm vs m).")
    else:
        s = (f"Reach is too short: re-check the link lengths ({lengths}) against the datasheet, a missing EE/flange "
             f"offset (ee.origin.xyz), DH signs/offsets (joints[*].dh.alpha, theta_offset), joint limits that may "
             f"prevent stretching out (joints[*].limits), and the reach definition (reach.measured_from = "
             f"{r.measured_from}, reach.measured_to = {r.measured_to}). Also check `units.length` (mm vs m).")
    return s
