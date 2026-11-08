"""Verifier checks (see docs/CONTRACTS.md section 4).

``run_checks(model_path, spec_path)`` runs the checks listed in ``CHECK_IDS`` in the documented order and
returns a :class:`simanything.schemas.CheckReport`. It never raises for a bad model or
spec: problems are reported as failed checks with a ``fix_hint``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import mujoco

from ..schemas import CheckReport, CheckResult
from ..spec import (bad_source_values, describe_key, duplicate_keys, estimate_counts, uncovered_fields,
                    unmatched_keys)
from .context import CheckContext, result, skipped_no_spec
from .kinematics import check_drawing, check_kinematics_match, check_reach
from .physics import (check_collision_exclusions, check_inertia_valid, check_mass_plausibility,
                      check_self_collision_home, check_stable_hold, check_total_mass, inertia_problems)
from .structure import check_actuators, check_compiles, check_ee_site, check_joint_limits, check_joint_structure

CHECK_IDS = ["compiles", "joint_structure", "ee_site", "kinematics_match", "joint_limits", "reach", "drawing",
             "total_mass", "mass_plausibility", "inertia_valid", "self_collision_home", "collision_exclusions", "stable_hold", "actuators",
             "sources_complete"]
MAX_ESTIMATE_FRACTION = 0.5  # above this share of estimated numbers, sources_complete warns
SPEC_DEPENDENT = {"joint_structure", "ee_site", "kinematics_match", "joint_limits", "reach", "drawing", "total_mass",
                  "actuators", "sources_complete"}


def check_sources_complete(ctx: CheckContext) -> CheckResult:
    if ctx.spec_raw is None:
        return skipped_no_spec("sources_complete")
    spec = ctx.spec_raw
    missing = uncovered_fields(spec)
    bad = bad_source_values(spec)
    unmatched = unmatched_keys(spec)
    n_est, n_num = estimate_counts(spec)
    frac = n_est / n_num if n_num else 0.0
    dup = duplicate_keys(spec)
    details = {"uncovered": missing, "bad_sources": {k: v for k, v in bad}, "unmatched_keys": unmatched,
               "duplicate_keys": dup, "n_numbers": n_num, "n_estimated": n_est, "estimate_fraction": frac}
    dup_msg = (f"{len(dup)} key(s) are in both `sources` and `estimates`: " + ", ".join(dup[:8])) if dup else ""
    dup_hint = ("Remove " + ", ".join(f"`{k}`" for k in dup[:8]) + " from `estimates` if the source states the "
                "number, or from `sources` if you inferred it (the source wins while both are listed).") if dup else ""
    msgs, hints = [], []
    if missing:
        shown = missing[:8]
        more = f" (and {len(missing) - len(shown)} more)" if len(missing) > len(shown) else ""
        msgs.append(f"{len(missing)} spec number(s) lack a source or estimate: {', '.join(shown)}{more}")
        hints.append("; ".join(f"add a source URL for {p} to `sources` or list it in `estimates`" for p in shown[:3])
                     + (". Same for: " + ", ".join(shown[3:]) if len(shown) > 3 else "") + more
                     + ". A parent path covers its children (e.g. `joints[*].limits`).")
    if bad:
        msgs.append(f"{len(bad)} source value(s) are not URLs or relative doc: paths: "
                    + ", ".join(f"sources[{k!r}] = {v!r}" for k, v in bad[:5]))
        hints.append("Each `sources` value must be an http(s) URL of the document that states the number, or "
                     "`doc:<relative path>` (forward slashes, no `..`) for a local file quoting it; put page numbers or quotes in `notes`, and "
                     "move numbers you inferred rather than read to `estimates`.")
    if unmatched:
        described = [describe_key(spec, k) for k in unmatched[:8]]
        msgs.append(f"{len(unmatched)} sources/estimates key(s) match no field of the spec (typo?): "
                    + ", ".join(described))
        hints.append("Fix or remove " + ", ".join(described) + ": keys are field paths such "
                     "as `joints[2].dh.a`, `joints[*].limits` or `reach.value`, with indices inside the joint list "
                     "and field names of this spec's convention; a vector (`origin.xyz`) is sourced as a whole.")
    if msgs:
        if dup_msg:
            msgs.append(dup_msg)
            hints.append(dup_hint)
        return result("sources_complete", False, measured=len(missing) + len(bad) + len(unmatched), expected=0,
                      message="; ".join(msgs), fix_hint=" ".join(hints), details=details)
    warn_msgs, warn_hints = [], []
    if dup_msg:
        warn_msgs.append(dup_msg)
        warn_hints.append(dup_hint)
    if frac > MAX_ESTIMATE_FRACTION:
        warn_msgs.append(f"every number is covered, but {n_est} of {n_num} ({frac * 100:.0f}%) are estimates")
        warn_hints.append("More than half of the numbers are estimates: look for sources (datasheet, manual, "
                          "DH table) for the ones that matter most, i.e. link lengths / DH rows, joint limits, "
                          "total_mass and reach, and move them from `estimates` to `sources`.")
    if warn_msgs:
        return result("sources_complete", False, severity="warning", measured=frac, expected=0,
                      tolerance=MAX_ESTIMATE_FRACTION, message="; ".join(warn_msgs), fix_hint=" ".join(warn_hints),
                      details=details)
    return result("sources_complete", True, measured=0, expected=0,
                  message=f"every number in the spec has a source or is listed as an estimate ({n_est} of {n_num} "
                          f"estimated)", details=details)


def _not_run(id: str, why: str, hint: str) -> CheckResult:
    """A check that could not run because an earlier problem blocks it (non-blocking itself)."""
    return result(id, False, severity="info", message=f"skipped: {why}", fix_hint=hint)


def _guard(id: str, fn: Callable[[], CheckResult]) -> CheckResult:
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - a crashing check must not take down the report
        return result(id, False, message=f"check crashed: {type(e).__name__}: {e}",
                      fix_hint="The checker could not evaluate this model; inspect the MJCF for unusual "
                               "structure (only serial hinge/slide arms are supported).")


def run_checks(model_path: str | Path, spec_path: str | Path | None = None, *, seed: int = 0,
               n_reach_samples: int = 5000) -> CheckReport:
    ctx = CheckContext.load(model_path, spec_path)
    spec_bad = spec_path is not None and ctx.spec is None

    model_checks: dict[str, Callable[[], CheckResult]] = {
        "compiles": lambda: check_compiles(ctx),
        "joint_structure": lambda: check_joint_structure(ctx),
        "ee_site": lambda: check_ee_site(ctx),
        "kinematics_match": lambda: check_kinematics_match(ctx, seed=seed),
        "joint_limits": lambda: check_joint_limits(ctx),
        "reach": lambda: check_reach(ctx, seed=seed, n_samples=n_reach_samples),
        "drawing": lambda: check_drawing(ctx),
        "total_mass": lambda: check_total_mass(ctx),
        "mass_plausibility": lambda: check_mass_plausibility(ctx),
        "inertia_valid": lambda: check_inertia_valid(ctx),
        "self_collision_home": lambda: check_self_collision_home(ctx),
        "collision_exclusions": lambda: check_collision_exclusions(ctx),
        "stable_hold": lambda: check_stable_hold(ctx),
        "actuators": lambda: check_actuators(ctx),
        "sources_complete": lambda: check_sources_complete(ctx),
    }
    spec_name = str(spec_path) if spec_path is not None else "the spec"
    checks: list[CheckResult] = []
    for cid in CHECK_IDS:
        if spec_bad and cid in SPEC_DEPENDENT:
            checks.append(result(cid, False, message=f"spec could not be loaded: {ctx.spec_error}",
                                 fix_hint=f"Fix {spec_name} so it validates (`sim-anything validate {spec_name}`); "
                                          "the error names the offending field."))
        elif ctx.model is None and cid not in ("compiles", "sources_complete"):
            checks.append(_not_run(cid, "model did not compile",
                                   "Fix the `compiles` failure first; this check runs once the model loads."))
        else:
            checks.append(_guard(cid, model_checks[cid]))
    return CheckReport.from_checks(str(model_path), None if spec_path is None else str(spec_path), checks,
                                   mujoco_version=mujoco.__version__)


__all__ = ["run_checks", "CHECK_IDS", "inertia_problems", "check_sources_complete"]
