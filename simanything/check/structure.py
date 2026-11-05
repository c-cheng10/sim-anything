"""Structural checks: compiles, joint_structure, ee_site, joint_limits, actuators."""

from __future__ import annotations

import mujoco
import numpy as np

from ..schemas import CheckResult
from .context import HINGE, JOINT_TYPE_NAMES, SLIDE, CheckContext, result, skipped_no_spec

LIMIT_TOL_HINGE = 1e-3  # rad
LIMIT_TOL_SLIDE = 1e-4  # m


def _is_ancestor_or_self(model: mujoco.MjModel, anc: int, bid: int) -> bool:
    while True:
        if bid == anc:
            return True
        if bid == 0:
            return False
        bid = int(model.body_parentid[bid])


# --------------------------------------------------------------------------- #
_COMPILE_HINTS = [
    ("mass and inertia", "Every moving link needs a positive mass and inertia: set joints[*].link.mass (> 0) "
                         "or give link geometry so the builder can derive one."),
    ("inertia must satisfy", "A link inertia violates A+B>=C: check joints[*].link.geometry sizes (no degenerate "
                             "shapes) or the hand-written <inertial>."),
    ("size", "A geom size is invalid: check joints[*].link.geometry radius/half_length/size (> 0) and fromto."),
    ("xml", "The XML is malformed: rebuild it from the spec (`sim-anything build`), or fix the hand edit at the "
            "reported line."),
]


def check_compiles(ctx: CheckContext) -> CheckResult:
    if ctx.model is None:
        err = ctx.compile_error or ""
        specific = next((h for key, h in _COMPILE_HINTS if key in err.lower()), "")
        return result("compiles", False, message=f"MuJoCo failed to load the model: {err}",
                      fix_hint=(specific + " " if specific else "") +
                               "If the MJCF was built from the spec, fix the spec field the error points at and "
                               "rebuild; if it was hand-edited, fix the XML at the reported element/line.",
                      details={"error": err, "mujoco_version": mujoco.__version__})
    m, d = ctx.model, ctx.data
    assert d is not None
    bad = []
    for label, q in (("qpos0", m.qpos0), (ctx.home_source, ctx.home_qpos)):
        mujoco.mj_resetData(m, d)
        d.qpos[:] = q
        mujoco.mj_forward(m, d)
        arrays = {"qpos": d.qpos, "qacc": d.qacc, "xpos": d.xpos, "xquat": d.xquat}
        nonfinite = [k for k, v in arrays.items() if not np.all(np.isfinite(v))]
        if nonfinite:
            bad.append(f"{label}: non-finite {', '.join(nonfinite)}")
    details = {"nq": int(m.nq), "nv": int(m.nv), "nbody": int(m.nbody), "njnt": int(m.njnt),
               "nu": int(m.nu), "timestep": float(m.opt.timestep), "home_source": ctx.home_source}
    if bad:
        return result("compiles", False, message="model loads but mj_forward is not finite (" + "; ".join(bad) + ")",
                      fix_hint="Non-finite forward dynamics usually come from zero/negative masses or inertias or "
                               "degenerate geometry: check joints[*].link.mass, total_mass and "
                               "joints[*].link.geometry sizes.", details=details)
    return result("compiles", True, message=f"loads with MuJoCo {mujoco.__version__}, mj_forward finite",
                  details=details)


# --------------------------------------------------------------------------- #
def check_joint_structure(ctx: CheckContext) -> CheckResult:
    if not ctx.has_spec:
        return skipped_no_spec("joint_structure")
    m, spec = ctx.model, ctx.spec
    assert m is not None and spec is not None
    expected = [[j.name, j.type] for j in spec.joints]
    measured = [[ctx.joint_name(j), JOINT_TYPE_NAMES.get(int(m.jnt_type[j]), "?")] for j in range(m.njnt)]
    spec_names = {j.name for j in spec.joints}
    problems: list[str] = []
    hints: list[str] = []

    missing = [(i, j.name) for i, (j, jid) in enumerate(zip(spec.joints, ctx.joint_ids)) if jid is None]
    extra = [j for j in range(m.njnt) if ctx.joint_name(j) not in spec_names]
    for i, name in missing:
        problems.append(f"spec joint '{name}' (joints[{i}]) not found in the model")
    for jid in extra:
        t = JOINT_TYPE_NAMES.get(int(m.jnt_type[jid]), "?")
        problems.append(f"model joint '{ctx.joint_name(jid)}' ({t}) is not in the spec")
    if missing and extra and len(missing) == len(extra):
        pairs = ", ".join(f"'{ctx.joint_name(e)}' -> joints[{i}].name '{n}'" for (i, n), e in zip(missing, extra))
        hints.append(f"Joint names differ between model and spec (renamed?): {pairs}. Joint names in the MJCF "
                     "must equal joints[i].name; rebuild from the spec.")
    else:
        if missing:
            hints.append("Add the missing joints to the model (rebuild from the spec) or remove "
                         + ", ".join(f"joints[{i}]" for i, _ in missing) + " from the spec if the robot has no such "
                         "joint (and update dof).")
        if extra:
            free = [e for e in extra if int(m.jnt_type[e]) not in (HINGE, SLIDE)]
            if free:
                hints.append("Remove the free/ball joint(s) " + ", ".join(f"'{ctx.joint_name(e)}'" for e in free)
                             + ": the arm base must be fixed and only hinge/slide joints are supported.")
            rest = [e for e in extra if e not in free]
            if rest:
                hints.append("Model joint(s) " + ", ".join(f"'{ctx.joint_name(e)}'" for e in rest)
                             + " are not in the spec: add them to `joints` (and dof) or remove them from the MJCF.")

    for i, (j, jid) in enumerate(zip(spec.joints, ctx.joint_ids)):
        if jid is None:
            continue
        mt = JOINT_TYPE_NAMES.get(int(m.jnt_type[jid]), "?")
        if mt != j.type:
            problems.append(f"joint '{j.name}' is {mt} in the model but {j.type} in the spec (joints[{i}].type)")
            hints.append(f"Make joints[{i}].type and the MJCF joint '{j.name}' agree (spec says {j.type}, "
                         f"model has {mt}).")

    # chain order: each matched joint's body must be the previous one's body or a descendant of it
    matched = [(i, jid) for i, jid in enumerate(ctx.joint_ids) if jid is not None]
    for (i0, a), (i1, b) in zip(matched, matched[1:]):
        ba, bb = int(m.jnt_bodyid[a]), int(m.jnt_bodyid[b])
        if not _is_ancestor_or_self(m, ba, bb) or (ba == bb and b < a):
            problems.append(f"joint '{spec.joints[i1].name}' (joints[{i1}]) is not downstream of "
                            f"'{spec.joints[i0].name}' (joints[{i0}]) in the model's body tree")
            hints.append(f"Order `joints` in chain order from base to tool: joints[{i0}] '{spec.joints[i0].name}' "
                         f"must come before joints[{i1}] '{spec.joints[i1].name}' in the kinematic chain "
                         "(rebuild after reordering).")

    details = {"missing": [n for _, n in missing], "extra": [ctx.joint_name(e) for e in extra]}
    if problems:
        return result("joint_structure", False, message="; ".join(problems), fix_hint=" ".join(hints),
                      measured=measured, expected=expected, details=details)
    return result("joint_structure", True, message=f"{len(expected)} joints match by name, type and chain order",
                  measured=measured, expected=expected, details=details)


# --------------------------------------------------------------------------- #
def _last_body(ctx: CheckContext) -> int:
    m = ctx.model
    assert m is not None
    if ctx.joint_ids and ctx.joint_ids[-1] is not None:
        return int(m.jnt_bodyid[ctx.joint_ids[-1]])
    # last spec joint not in the model (reported by joint_structure): deepest body as fallback
    depth = [0] * m.nbody
    for b in range(1, m.nbody):
        depth[b] = depth[int(m.body_parentid[b])] + 1
    return int(np.argmax(depth))


def check_ee_site(ctx: CheckContext) -> CheckResult:
    if not ctx.has_spec:
        return skipped_no_spec("ee_site")
    m, spec = ctx.model, ctx.spec
    assert m is not None and spec is not None
    name = spec.ee.name
    last = _last_body(ctx)
    sid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, name)
    details = {"site": name, "last_body": ctx.body_name(last)}
    if sid < 0:
        sites = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_SITE, s) for s in range(m.nsite)]
        details["model_sites"] = sites
        return result("ee_site", False, expected=name, measured=None,
                      message=f"no site named '{name}' (ee.name) in the model; sites: {sites}",
                      fix_hint=f"Add a site named '{name}' on the last link '{ctx.body_name(last)}' (the builder does "
                               "this from `ee`), or set ee.name to the model's end-effector site name.",
                      details=details)
    bid = int(m.site_bodyid[sid])
    details["site_body"] = ctx.body_name(bid)
    # accept the last body or a body welded to it (e.g. a fixed flange body)
    if bid == last or (int(m.body_weldid[bid]) == int(m.body_weldid[last]) and _is_ancestor_or_self(m, last, bid)):
        return result("ee_site", True, expected=name, measured=name,
                      message=f"site '{name}' on last body '{ctx.body_name(bid)}'", details=details)
    return result("ee_site", False, expected=name, measured=name,
                  message=f"site '{name}' is on body '{ctx.body_name(bid)}', not on the last body "
                          f"'{ctx.body_name(last)}'",
                  fix_hint=f"Move site '{name}' to the last link '{ctx.body_name(last)}' (ee.origin is relative to the "
                           "frame after the last joint), or check that `joints` lists every joint up to the flange.",
                  details=details)


# --------------------------------------------------------------------------- #
def check_joint_limits(ctx: CheckContext) -> CheckResult:
    if not ctx.has_spec:
        return skipped_no_spec("joint_limits")
    m, spec = ctx.model, ctx.spec
    assert m is not None and spec is not None
    mismatches, no_spec_limits, rows = [], [], []
    measured, expected = {}, {}
    max_diff = 0.0
    for i, (j, jid) in enumerate(zip(spec.joints, ctx.joint_ids)):
        if jid is None:
            continue
        limited = bool(m.jnt_limited[jid])
        mr = [float(x) for x in m.jnt_range[jid]] if limited else None
        measured[j.name] = mr
        if j.limits is None:
            no_spec_limits.append((i, j.name))
            expected[j.name] = None
            continue
        sr = [j.limits.lower, j.limits.upper]
        expected[j.name] = sr
        tol = LIMIT_TOL_HINGE if j.type == "hinge" else LIMIT_TOL_SLIDE
        if mr is None:
            mismatches.append((i, j.name, "model joint is unlimited", sr, None))
            continue
        diff = max(abs(mr[0] - sr[0]), abs(mr[1] - sr[1]))
        unit = "rad" if j.type == "hinge" else "m"
        rows.append({"joint": j.name, "model": mr, "spec": sr, "max_abs_diff": diff, "unit": unit})
        max_diff = max(max_diff, diff)
        if diff > tol:
            mismatches.append((i, j.name, f"model range [{mr[0]:.4f}, {mr[1]:.4f}] {unit} vs spec "
                                          f"[{sr[0]:.4f}, {sr[1]:.4f}] {unit}", sr, mr))
    details = {"joints": rows, "missing_spec_limits": [n for _, n in no_spec_limits]}
    tol = {"hinge_rad": LIMIT_TOL_HINGE, "slide_m": LIMIT_TOL_SLIDE}
    if mismatches:
        msg = "; ".join(f"'{n}' (joints[{i}]): {why}" for i, n, why, _, _ in mismatches)
        paths = ", ".join(f"joints[{i}].limits" for i, *_ in mismatches)
        return result("joint_limits", False, measured=measured, expected=expected, tolerance=tol,
                      message=f"joint ranges differ from the spec: {msg}",
                      fix_hint=f"Rebuild so the MJCF joint ranges equal {paths} (in SI after unit conversion: check "
                               "`units.angle` deg vs rad); if the spec values are wrong, correct them from the "
                               "datasheet.", details=details)
    if no_spec_limits:
        paths = ", ".join(f"joints[{i}].limits" for i, _ in no_spec_limits)
        return result("joint_limits", False, severity="warning", measured=measured, expected=expected,
                      tolerance=tol, message="spec gives no limits for " + ", ".join(f"'{n}'" for _, n in no_spec_limits),
                      fix_hint=f"Add {paths} from the datasheet (with a source) or as an estimate.", details=details)
    return result("joint_limits", True, measured=measured, expected=expected, tolerance=tol,
                  message=f"all joint ranges match the spec (max diff {max_diff:.2e})", details=details)


# --------------------------------------------------------------------------- #
def check_actuators(ctx: CheckContext) -> CheckResult:
    if not ctx.has_spec:
        return skipped_no_spec("actuators")
    m, spec = ctx.model, ctx.spec
    assert m is not None and spec is not None
    by_joint: dict[int, list[str]] = {}
    for a in range(m.nu):
        if int(m.actuator_trntype[a]) in (int(mujoco.mjtTrn.mjTRN_JOINT), int(mujoco.mjtTrn.mjTRN_JOINTINPARENT)):
            jid = int(m.actuator_trnid[a, 0])
            by_joint.setdefault(jid, []).append(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, a) or f"<act {a}>")
    counts, none, many = {}, [], []
    for i, (j, jid) in enumerate(zip(spec.joints, ctx.joint_ids)):
        acts = by_joint.get(jid, []) if jid is not None else []
        counts[j.name] = acts
        if jid is None:
            continue  # reported by joint_structure
        if not acts:
            none.append((i, j.name))
        elif len(acts) > 1:
            many.append((i, j.name, acts))
    details = {"actuators_by_joint": counts, "nu": int(m.nu)}
    if none or many:
        parts, hints = [], []
        if none:
            parts.append("no actuator for " + ", ".join(f"'{n}' (joints[{i}])" for i, n in none))
            hints.append("Add one <position> actuator per joint (named '<joint>_act', the builder does this for every "
                         "spec joint) for " + ", ".join(f"'{n}'" for _, n in none) + "; rebuild if the MJCF was "
                         "hand-edited.")
        if many:
            parts.append("; ".join(f"'{n}' (joints[{i}]) driven by {len(a)} actuators {a}" for i, n, a in many))
            hints.append("Keep exactly one actuator per joint: remove the duplicates "
                         + "; ".join(f"{a[1:]} on '{n}'" for _, n, a in many) + ".")
        return result("actuators", False, measured=sum(len(v) for v in counts.values()), expected=len(spec.joints),
                      message="; ".join(parts), fix_hint=" ".join(hints), details=details)
    return result("actuators", True, measured=sum(len(v) for v in counts.values()), expected=len(spec.joints),
                  message="every spec joint is driven by exactly one actuator", details=details)
