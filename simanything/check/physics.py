"""Physical checks: total_mass, mass_plausibility, inertia_valid, self_collision_home, collision_exclusions,
stable_hold."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Optional

import mujoco
import numpy as np

from ..schemas import CheckResult
from .context import HINGE, SLIDE, CheckContext, result, skipped_no_spec

MASS_TOL = 0.05  # relative
INERTIA_SLACK = 1e-9
PENETRATION_TOL = 1e-3  # m
ZERO_LEN = 1e-6  # m; body offsets shorter than this count as zero-length links
DENSITY_MIN, DENSITY_MAX = 100.0, 20000.0  # kg/m^3, plausible apparent link density
MIN_LINK_FRACTION = 0.005  # a moving link below 0.5% of the total mass is suspicious
MIN_KG_PER_M_REACH = 0.1  # kg of total mass per metre of rated reach
HOLD_SECONDS = 2.0
DRIFT_TOL_HINGE = 0.05  # rad
DRIFT_TOL_SLIDE = 0.005  # m
SPEED_TOL = 0.1  # rad/s or m/s
INSTABILITY_WARNINGS = ("mjWARN_BADQACC", "mjWARN_BADQPOS", "mjWARN_BADQVEL", "mjWARN_BADCTRL")


# --------------------------------------------------------------------------- #
def check_total_mass(ctx: CheckContext) -> CheckResult:
    if not ctx.has_spec:
        return skipped_no_spec("total_mass")
    m, spec = ctx.model, ctx.spec
    assert m is not None and spec is not None
    measured = float(np.sum(m.body_mass))
    if spec.total_mass is None:
        return result("total_mass", True, severity="info", measured=measured,
                      message=f"spec has no total_mass; model mass is {measured:.3f} kg")
    expected = float(spec.total_mass)
    rel = (measured - expected) / expected
    details = {"relative_error": rel,
               "body_masses": {ctx.body_name(b): float(m.body_mass[b]) for b in range(1, m.nbody)}}
    link_masses = [spec.base.link.mass] + [j.link.mass for j in spec.joints]
    if all(x is not None for x in link_masses):
        details["spec_link_mass_sum"] = float(sum(link_masses))  # type: ignore[arg-type]
    if abs(rel) <= MASS_TOL:
        return result("total_mass", True, measured=measured, expected=expected, tolerance=MASS_TOL,
                      message=f"model mass {measured:.3f} kg within {abs(rel) * 100:.1f}% of {expected:.3f} kg",
                      details=details)
    word = "above" if rel > 0 else "below"
    hint = (f"Model is {'too heavy' if rel > 0 else 'too light'}: make the link masses "
            "(base.link.mass, joints[*].link.mass) consistent with total_mass, or re-check total_mass against the "
            "datasheet (with or without controller/cables/tool?).")
    # per-link comparison: which model bodies disagree with the spec link masses?
    per_link: dict[str, float] = {}
    for b in range(1, m.nbody):
        p = ctx.body_spec_path(b)
        if p:
            per_link[p] = per_link.get(p, 0.0) + float(m.body_mass[b])
    spec_mass = {"base.link": spec.base.link.mass}
    spec_mass.update({f"joints[{i}].link": j.link.mass for i, j in enumerate(spec.joints)})
    off = [(p, mm, spec_mass[p]) for p, mm in per_link.items()
           if spec_mass.get(p) and abs(mm - spec_mass[p]) > MASS_TOL * spec_mass[p]]  # type: ignore[operator]
    if off:
        details["link_mass_mismatch"] = {p: {"model": mm, "spec": sm} for p, mm, sm in off}
    if "spec_link_mass_sum" in details and abs(details["spec_link_mass_sum"] - expected) <= MASS_TOL * expected and off:
        hint = ("The spec is self-consistent but the model's body masses do not follow it: "
                + ", ".join(f"{p}.mass is {sm:.3f} kg in the spec but {mm:.3f} kg in the model" for p, mm, sm in off)
                + ". Rebuild from the spec, or fix the hand-edited <inertial> masses.")
    elif "spec_link_mass_sum" in details:
        s = details["spec_link_mass_sum"]
        hint += (f" The spec's link masses sum to {s:.3f} kg vs total_mass {expected:.3f} kg; fix whichever is "
                 "unsupported by a source.")
    else:
        hint += " Links without a mass get one from their geometry volume, so also check joints[*].link.geometry sizes."
    return result("total_mass", False, measured=measured, expected=expected, tolerance=MASS_TOL,
                  message=f"model mass {measured:.3f} kg is {abs(rel) * 100:.1f}% {word} spec {expected:.3f} kg",
                  fix_hint=hint, details=details)


# --------------------------------------------------------------------------- #
def geom_volume(m: mujoco.MjModel, g: int) -> Optional[float]:
    """Volume of a primitive geom (m^3); None for meshes, planes and height fields."""
    t, s = int(m.geom_type[g]), m.geom_size[g]
    G = mujoco.mjtGeom
    if t == int(G.mjGEOM_SPHERE):
        return 4.0 / 3.0 * np.pi * s[0] ** 3
    if t == int(G.mjGEOM_CAPSULE):
        return np.pi * s[0] ** 2 * 2 * s[1] + 4.0 / 3.0 * np.pi * s[0] ** 3
    if t == int(G.mjGEOM_CYLINDER):
        return np.pi * s[0] ** 2 * 2 * s[1]
    if t == int(G.mjGEOM_BOX):
        return 8.0 * s[0] * s[1] * s[2]
    if t == int(G.mjGEOM_ELLIPSOID):
        return 4.0 / 3.0 * np.pi * s[0] * s[1] * s[2]
    return None


def _link_paths(ctx: CheckContext, bodies) -> str:
    paths = sorted({ctx.body_spec_path(b) or f"body '{ctx.body_name(b)}'" for b in bodies})
    return ", ".join(paths)


def check_mass_plausibility(ctx: CheckContext) -> CheckResult:
    cid = "mass_plausibility"
    m = ctx.model
    assert m is not None
    total = float(np.sum(m.body_mass))
    problems, hints = [], []
    details: dict = {"density_range_kg_m3": [DENSITY_MIN, DENSITY_MAX], "min_link_fraction": MIN_LINK_FRACTION,
                     "min_kg_per_m_reach": MIN_KG_PER_M_REACH, "total_mass": total}
    # 1. apparent density of each body: mass / volume of its primitives
    dens, odd = {}, []
    for b in range(1, m.nbody):
        geoms = [g for g in range(m.ngeom) if int(m.geom_bodyid[g]) == b]
        vols = [geom_volume(m, g) for g in geoms]
        if not geoms or any(v is None for v in vols) or float(m.body_mass[b]) <= 0:
            continue
        rho = float(m.body_mass[b]) / max(float(sum(vols)), 1e-12)  # type: ignore[arg-type]
        dens[ctx.body_name(b)] = rho
        if not DENSITY_MIN <= rho <= DENSITY_MAX:
            odd.append((b, rho))
    details["density"] = dens
    if odd:
        problems.append("implausible density (mass / geometry volume): " + ", ".join(
            f"{ctx.body_label(b)} {rho:.0f} kg/m^3" for b, rho in odd))
        hints.append(f"Bodies {_link_paths(ctx, [b for b, _ in odd])} have a density outside "
                     f"[{DENSITY_MIN:g}, {DENSITY_MAX:g}] kg/m^3 (aluminium ~2700, steel ~7800; hollow arm links "
                     "are lighter): check that link.mass belongs to that link and that link.geometry sizes are in "
                     "`units.length` and roughly match the real link.")
    # 2. moving links (grouped by weld) with a negligible share of the total mass
    if total > 0:
        groups: dict[int, float] = {}
        for b in range(1, m.nbody):
            w = int(m.body_weldid[b])
            if w != 0:
                groups[w] = groups.get(w, 0.0) + float(m.body_mass[b])
        light = [(w, mw) for w, mw in groups.items() if mw < MIN_LINK_FRACTION * total]
        details["link_fraction"] = {ctx.body_name(w): mw / total for w, mw in groups.items()}
        if light:
            problems.append("moving link(s) with < {:.1f}% of the total mass: ".format(MIN_LINK_FRACTION * 100)
                            + ", ".join(f"{ctx.body_label(w)} {mw / total * 100:.2f}%" for w, mw in light))
            hints.append(f"Links {_link_paths(ctx, [w for w, _ in light])} are almost massless next to the rest of "
                         "the arm: give them a realistic link.mass (an estimate is fine) or check whether a heavy "
                         "neighbour carries mass that belongs to them.")
    # 3. total mass vs reach
    spec = ctx.spec
    if spec is not None and spec.reach is not None and total > 0:
        per_m = total / float(spec.reach.value)
        details["kg_per_m_reach"] = per_m
        if per_m < MIN_KG_PER_M_REACH:
            problems.append(f"total mass {total:.3f} kg is only {per_m:.3f} kg per metre of reach")
            hints.append("The arm is implausibly light for its reach: check total_mass / joints[*].link.mass "
                         "(kg, not g?) and reach.value / `units.length` (mm vs m).")
    if not problems:
        return result(cid, True, severity="warning", message="link densities, mass shares and mass per reach are "
                                                               "plausible", details=details)
    return result(cid, False, severity="warning", measured=len(problems), expected=0, message="; ".join(problems),
                  fix_hint=" ".join(hints), details=details)


# --------------------------------------------------------------------------- #
def inertia_problems(masses: np.ndarray, inertias: np.ndarray, slack: float = INERTIA_SLACK
                     ) -> list[tuple[int, str]]:
    """Return (row index, reason) for every row with mass <= 0, a non-positive principal
    inertia, or principal inertias violating the triangle inequality A + B >= C."""
    masses = np.asarray(masses, dtype=float).reshape(-1)
    inertias = np.asarray(inertias, dtype=float).reshape(-1, 3)
    out = []
    for i, (mass, I) in enumerate(zip(masses, inertias)):
        if not np.isfinite(mass) or mass <= 0:
            out.append((i, f"mass {mass:g} <= 0"))
            continue
        if not np.all(np.isfinite(I)) or np.any(I <= 0):
            out.append((i, f"principal inertia {I.tolist()} not all > 0"))
            continue
        s = np.sort(I)
        if s[0] + s[1] < s[2] - slack:
            out.append((i, f"principal inertia {I.tolist()} violates A+B>=C ({s[0]:.3g}+{s[1]:.3g} < {s[2]:.3g})"))
    return out


def check_inertia_valid(ctx: CheckContext) -> CheckResult:
    m = ctx.model
    assert m is not None
    probs = inertia_problems(m.body_mass[1:], m.body_inertia[1:])
    details = {"bodies_checked": int(m.nbody - 1)}
    if not probs:
        return result("inertia_valid", True, message=f"{m.nbody - 1} bodies have positive mass and valid inertia",
                      details=details)
    items = [(i + 1, why) for i, why in probs]
    details["invalid"] = {ctx.body_name(b): why for b, why in items}
    paths = sorted({ctx.body_spec_path(b) or f"body '{ctx.body_name(b)}'" for b, _ in items})
    return result("inertia_valid", False, measured=len(items), expected=0,
                  message="; ".join(f"{ctx.body_label(b)}: {why}" for b, why in items),
                  fix_hint="Give each listed link a positive mass and a physically valid inertia: set "
                           + ", ".join(f"{p}.mass" if p.endswith("link") else p for p in paths)
                           + " and non-degenerate geometry (positive radius/half_length/size) so the builder derives "
                           "a valid inertia; a hand-written <inertial> must satisfy A+B>=C.",
                  details=details)


# --------------------------------------------------------------------------- #
def _set_home(ctx: CheckContext) -> None:
    m, d = ctx.model, ctx.data
    assert m is not None and d is not None
    mujoco.mj_resetData(m, d)
    d.qpos[:] = ctx.home_qpos
    mujoco.mj_forward(m, d)


def _related(m: mujoco.MjModel, b1: int, b2: int, *, count_world_parent: bool = False) -> bool:
    """True if MuJoCo filters contacts between the bodies: same rigid body, or parent/child where the
    parent is not welded to the world (MuJoCo still collides a world-fixed base with its child).
    ``count_world_parent`` also counts that world-fixed parent/child pair (structural relation)."""
    w1, w2 = int(m.body_weldid[b1]), int(m.body_weldid[b2])
    if w1 == w2:
        return True
    p1 = int(m.body_weldid[int(m.body_parentid[w1])])
    p2 = int(m.body_weldid[int(m.body_parentid[w2])])
    return (p1 == w2 and (w2 != 0 or count_world_parent)) or (p2 == w1 and (w1 != 0 or count_world_parent))


def _excluded(m: mujoco.MjModel, b1: int, b2: int) -> bool:
    if m.nexclude == 0:
        return False
    sigs = set(int(s) for s in m.exclude_signature)
    lo, hi = min(b1, b2), max(b1, b2)
    return ((lo << 16) + hi) in sigs or ((hi << 16) + lo) in sigs


def check_self_collision_home(ctx: CheckContext) -> CheckResult:
    m, d = ctx.model, ctx.data
    assert m is not None and d is not None
    _set_home(ctx)
    pairs: dict[tuple[int, int], dict] = {}
    for c in d.contact[: d.ncon]:
        b1, b2 = int(m.geom_bodyid[c.geom1]), int(m.geom_bodyid[c.geom2])
        if b1 == 0 or b2 == 0:  # environment (floor etc.), not self-collision
            continue
        if _related(m, b1, b2) or _excluded(m, b1, b2):
            continue
        depth = float(-c.dist)
        key = (min(b1, b2), max(b1, b2))
        g = (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, c.geom1) or f"geom {c.geom1}",
             mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, c.geom2) or f"geom {c.geom2}")
        prev = pairs.get(key)
        if prev is None or depth > prev["penetration"]:
            pairs[key] = {"body1": ctx.body_name(key[0]), "body2": ctx.body_name(key[1]),
                          "spec1": ctx.body_spec_path(key[0]), "spec2": ctx.body_spec_path(key[1]),
                          "geoms": list(g), "penetration": depth}
    bad = {k: v for k, v in pairs.items() if v["penetration"] > PENETRATION_TOL}
    worst = max((v["penetration"] for v in pairs.values()), default=0.0)
    details = {"home_source": ctx.home_source, "contacts": list(pairs.values())}
    if not bad:
        return result("self_collision_home", True, measured=worst, expected=0.0, tolerance=PENETRATION_TOL,
                      message=f"no self-collision deeper than {PENETRATION_TOL * 1000:.0f} mm at home "
                              f"({len(pairs)} touching pairs)", details=details)
    msgs, hints = [], []
    for (b1, b2), v in sorted(bad.items(), key=lambda kv: -kv[1]["penetration"]):
        msgs.append(f"{ctx.body_label(b1)} and {ctx.body_label(b2)} penetrate by {v['penetration'] * 1000:.1f} mm")
        geo = " / ".join(f"{p}.geometry[*].radius" for p in (v["spec1"], v["spec2"]) if p) or "the link geometry"
        hints.append(f"Links '{v['body1']}' and '{v['body2']}' overlap at home: reduce {geo} (or box size), give "
                     "explicit geometry (fromto/pos) that follows the real link shape, or check the home pose "
                     "(joints[*].home) and link offsets.")
    return result("self_collision_home", False, measured=worst, expected=0.0, tolerance=PENETRATION_TOL,
                  message="; ".join(msgs), fix_hint=" ".join(hints), details=details)


# --------------------------------------------------------------------------- #
_REASON = re.compile(r"^\s*(\S+)\s*/\s*(\S+)\s*:\s*(.+?)\s*$", re.S)


def exclusion_reasons(model_path: str) -> dict[frozenset, str]:
    """Reasons for ``<exclude>`` pairs from ``<!-- body1 / body2: reason -->`` comments (as the builder
    writes them). Returns {} if the file cannot be parsed."""
    try:
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        root = ET.parse(model_path, parser=parser).getroot()
    except Exception:  # noqa: BLE001 - reasons are optional
        return {}
    out: dict[frozenset, str] = {}
    for contact in root.iter("contact"):
        for el in contact:
            if el.tag is ET.Comment and el.text:
                mt = _REASON.match(el.text)
                if mt:
                    out[frozenset((mt.group(1), mt.group(2)))] = mt.group(3)
    return out


def _zero_length_between(m: mujoco.MjModel, anc: int, desc: int) -> bool:
    """True if ``desc`` descends from ``anc`` and every body after ``anc``'s child on the path sits at its
    parent's origin, i.e. the bodies are separated only by zero-length links."""
    path = []
    b = desc
    while b != anc:
        if b == 0:
            return False
        path.append(b)
        b = int(m.body_parentid[b])
    # path = [desc, ..., child of anc]; all but the child of anc must have zero offset
    return all(float(np.linalg.norm(m.body_pos[x])) < ZERO_LEN for x in path[:-1])


def check_collision_exclusions(ctx: CheckContext) -> CheckResult:
    cid = "collision_exclusions"
    m = ctx.model
    assert m is not None
    if m.nexclude == 0:
        return result(cid, True, severity="warning", measured=0, expected=0,
                      message="no contact exclusions besides MuJoCo's parent/child filter")
    reasons = exclusion_reasons(ctx.model_path)
    rows, unexplained = [], []
    for sig in (int(s) for s in m.exclude_signature):
        b1, b2 = sorted((sig >> 16, sig & 0xFFFF))
        n1, n2 = ctx.body_name(b1), ctx.body_name(b2)
        if _related(m, b1, b2, count_world_parent=True):
            kind = "parent/child"
        elif _zero_length_between(m, b1, b2):
            kind = "zero-length links between"
        else:
            kind = "other"
            unexplained.append((b1, b2))
        why = reasons.get(frozenset((n1, n2)), "no reason given")
        rows.append({"body1": n1, "body2": n2, "spec1": ctx.body_spec_path(b1), "spec2": ctx.body_spec_path(b2),
                     "kind": kind, "reason": why})
    listing = "; ".join(f"{r['body1']} / {r['body2']} ({r['reason']})" for r in rows)
    details = {"excluded": rows}
    if not unexplained:
        return result(cid, True, severity="warning", measured=0, expected=0,
                      message=f"{len(rows)} excluded pair(s), all parent/child or separated only by zero-length "
                              f"links: {listing}", details=details)
    bad = [r for r in rows if r["kind"] == "other"]
    names = ", ".join(f"'{r['body1']}' / '{r['body2']}'" for r in bad)
    paths = sorted({p for r in bad for p in (r["spec1"], r["spec2"]) if p})
    geo = ", ".join(f"{p}.geometry" for p in paths) or "the link geometry"
    return result(cid, False, severity="warning", measured=len(bad), expected=0,
                  message=f"{len(bad)} of {len(rows)} excluded pair(s) are neither parent/child nor separated only "
                          f"by zero-length links, so contacts between them are never checked: {listing}",
                  fix_hint=f"Review the exclusions of {names}: they hide any collision between those links. If they "
                           f"are there because the primitives overlap, make the geometry fit ({geo}: smaller radius, "
                           "explicit fromto/pos) so the exclusion is no longer needed; if the MJCF was hand-edited, "
                           "remove the <exclude> or explain it in the spec's `notes`.",
                  details=details)


# --------------------------------------------------------------------------- #
def _home_ctrl(m: mujoco.MjModel, d: mujoco.MjData, qhome: np.ndarray) -> list[str]:
    """Command position-type actuators to the home configuration. Returns kinds per actuator."""
    kinds = []
    for a in range(m.nu):
        kind = "other"
        target: Optional[float] = None
        if int(m.actuator_trntype[a]) in (int(mujoco.mjtTrn.mjTRN_JOINT), int(mujoco.mjtTrn.mjTRN_JOINTINPARENT)):
            jid = int(m.actuator_trnid[a, 0])
            if int(m.jnt_type[jid]) in (HINGE, SLIDE):
                target = float(m.actuator_gear[a, 0]) * float(qhome[m.jnt_qposadr[jid]])
        position_like = (int(m.actuator_biastype[a]) == int(mujoco.mjtBias.mjBIAS_AFFINE)
                         and m.actuator_biasprm[a, 1] < 0)
        if position_like and target is not None:
            kind = "position"
            if int(m.actuator_dyntype[a]) == int(mujoco.mjtDyn.mjDYN_INTEGRATOR):
                kind = "intvelocity"
                if m.actuator_actadr[a] >= 0:
                    d.act[m.actuator_actadr[a]] = target
                d.ctrl[a] = 0.0
            else:
                c = target
                if m.actuator_ctrllimited[a]:
                    c = float(np.clip(c, *m.actuator_ctrlrange[a]))
                d.ctrl[a] = c
        else:
            d.ctrl[a] = 0.0
        kinds.append(kind)
    return kinds


def check_stable_hold(ctx: CheckContext) -> CheckResult:
    m, d = ctx.model, ctx.data
    assert m is not None and d is not None
    qhome = np.asarray(ctx.home_qpos, dtype=float)
    joints = ctx.robot_joint_ids()
    mujoco.mj_resetData(m, d)
    d.qpos[:] = qhome
    kinds = _home_ctrl(m, d, qhome)
    mujoco.mj_forward(m, d)
    qadr = np.array([m.jnt_qposadr[j] for j in joints], dtype=int)
    vadr = np.array([m.jnt_dofadr[j] for j in joints], dtype=int)
    is_hinge = np.array([int(m.jnt_type[j]) == HINGE for j in joints], dtype=bool)
    tol = np.where(is_hinge, DRIFT_TOL_HINGE, DRIFT_TOL_SLIDE)
    q0 = qhome[qadr]
    nsteps = int(round(HOLD_SECONDS / m.opt.timestep))
    max_drift = np.zeros(len(joints))
    nan_step: Optional[int] = None
    warn_ids = {name: int(getattr(mujoco.mjtWarning, name)) for name in INSTABILITY_WARNINGS}
    for step in range(nsteps):
        mujoco.mj_step(m, d)
        if any(d.warning[w].number > 0 for w in warn_ids.values()):
            nan_step = step
            break
        q = d.qpos[qadr]
        if not np.all(np.isfinite(q)) or not np.all(np.isfinite(d.qvel)):
            nan_step = step
            break
        np.maximum(max_drift, np.abs(q - q0), out=max_drift)
    warnings = {mujoco.mjtWarning(i).name: int(d.warning[i].number)
                for i in range(int(mujoco.mjtWarning.mjNWARNING)) if d.warning[i].number > 0}
    speeds = np.abs(d.qvel[vadr]) if len(vadr) else np.zeros(0)
    final_speed = float(np.max(speeds)) if len(speeds) and np.all(np.isfinite(speeds)) else float("nan")
    drift_ratio = max_drift / tol if len(joints) else np.zeros(0)
    details = {
        "seconds": HOLD_SECONDS, "timestep": float(m.opt.timestep), "home_source": ctx.home_source,
        "warnings": warnings, "actuator_kinds": kinds,
        "max_drift": {ctx.joint_name(j): float(x) for j, x in zip(joints, max_drift)},
        "final_speed": {ctx.joint_name(j): float(x) for j, x in zip(joints, speeds)},
        "tolerance": {"drift_hinge_rad": DRIFT_TOL_HINGE, "drift_slide_m": DRIFT_TOL_SLIDE, "speed": SPEED_TOL},
    }
    # actuators at their force limit at the end of the run (cannot hold against gravity)
    saturated = []
    for a in range(m.nu):
        if m.actuator_forcelimited[a] and np.isfinite(d.actuator_force[a]):
            lo, hi = m.actuator_forcerange[a]
            f = float(d.actuator_force[a])
            if (hi > 0 and f >= hi * 0.999) or (lo < 0 and f <= lo * 0.999):
                jid = int(m.actuator_trnid[a, 0])
                saturated.append(jid)
    details["saturated_joints"] = [ctx.joint_name(j) for j in saturated]
    tol_out = {"drift_hinge_rad": DRIFT_TOL_HINGE, "drift_slide_m": DRIFT_TOL_SLIDE, "final_speed": SPEED_TOL}

    unstable = nan_step is not None
    drift_bad = bool(len(joints)) and bool(np.any(drift_ratio > 1.0))
    speed_bad = not np.isfinite(final_speed) or final_speed > SPEED_TOL
    if not (unstable or drift_bad or speed_bad):
        worst = float(np.max(max_drift)) if len(joints) else 0.0
        return result("stable_hold", True, measured=worst, expected=0.0, tolerance=tol_out,
                      message=f"holds home for {HOLD_SECONDS:g} s: max drift {worst:.4f}, final speed "
                              f"{final_speed:.4f}", details=details)

    parts = []
    if unstable:
        t = (nan_step + 1) * m.opt.timestep  # type: ignore[operator]
        parts.append(f"simulation became unstable after {t:.3f} s (warnings: {warnings or 'non-finite state'})")
    worst_j = int(np.argmax(drift_ratio)) if len(joints) else None
    if drift_bad and worst_j is not None and not unstable:
        unit = "rad" if is_hinge[worst_j] else "m"
        parts.append(f"joint {ctx.joint_label(joints[worst_j])} drifted {max_drift[worst_j]:.4f} {unit} from home")
    if speed_bad and not unstable:
        parts.append(f"final max joint speed {final_speed:.4f} > {SPEED_TOL}")

    no_act = [j for j in joints if not any(int(m.actuator_trnid[a, 0]) == j and int(m.actuator_trntype[a]) in
                                           (int(mujoco.mjtTrn.mjTRN_JOINT), int(mujoco.mjtTrn.mjTRN_JOINTINPARENT))
                                           for a in range(m.nu))]
    hints = []
    if no_act:
        hints.append("Joints " + ", ".join(ctx.joint_label(j) for j in no_act) + " have no actuator to hold them "
                     "(see the `actuators` check).")
    if saturated:
        paths = ", ".join(f"joints[{i}].effort_limit" for i in
                          (ctx.spec_index_of_joint(j) for j in saturated) if i is not None)
        hints.append("Actuators of " + ", ".join(ctx.joint_label(j) for j in saturated) + " are at their force limit: "
                     f"check {paths or 'joints[*].effort_limit'} against the datasheet (peak vs rated torque) and "
                     "whether link masses are too high.")
    if worst_j is not None:
        i = ctx.spec_index_of_joint(joints[worst_j])
        jp = f"joints[{i}]" if i is not None else f"joint '{ctx.joint_name(joints[worst_j])}'"
        ep = f"joints[{i}].effort_limit" if i is not None else "joints[*].effort_limit"
        hints.append(f"Worst joint: {jp}. Check that masses are realistic (joints[*].link.mass, total_mass), the "
                     f"effort limit ({ep}) can hold the arm against gravity, and the link geometry "
                     "(joints[*].link.geometry, link.com) does not put mass far from the axes.")
    if unstable:
        hints.append("Instability usually means tiny masses/inertias next to large ones or very stiff actuators: "
                     "avoid near-zero joints[*].link.mass and degenerate geometry.")
    return result("stable_hold", False, measured=float(np.max(max_drift)) if len(joints) else None, expected=0.0,
                  tolerance=tol_out, message="; ".join(parts), fix_hint=" ".join(hints), details=details)
