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
from ..spec import uncovered_fields
from .context import CheckContext, result, skipped_no_spec
from .kinematics import check_kinematics_match, check_reach
from .physics import (check_inertia_valid, check_self_collision_home, check_stable_hold, check_total_mass,
                      inertia_problems)
from .structure import check_actuators, check_compiles, check_ee_site, check_joint_limits, check_joint_structure

CHECK_IDS = ["compiles", "joint_structure", "ee_site", "kinematics_match", "joint_limits", "reach", "total_mass",
             "inertia_valid", "self_collision_home", "stable_hold", "actuators", "sources_complete"]
SPEC_DEPENDENT = {"joint_structure", "ee_site", "kinematics_match", "joint_limits", "reach", "total_mass",
                  "actuators", "sources_complete"}


def check_sources_complete(ctx: CheckContext) -> CheckResult:
    if ctx.spec_raw is None:
        return skipped_no_spec("sources_complete")
    missing = uncovered_fields(ctx.spec_raw)
    if not missing:
        return result("sources_complete", True, measured=0, expected=0,
                      message="every number in the spec has a source or is listed as an estimate")
    shown = missing[:8]
    more = f" (and {len(missing) - len(shown)} more)" if len(missing) > len(shown) else ""
    hint = ("; ".join(f"add a source URL for {p} to `sources` or list it in `estimates`" for p in shown[:3])
            + (". Same for: " + ", ".join(shown[3:]) if len(shown) > 3 else "") + more
            + ". A parent path covers its children (e.g. `joints[*].limits`).")
    return result("sources_complete", False, measured=len(missing), expected=0,
                  message=f"{len(missing)} spec number(s) lack a source or estimate: {', '.join(shown)}{more}",
                  fix_hint=hint, details={"uncovered": missing})


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
        "total_mass": lambda: check_total_mass(ctx),
        "inertia_valid": lambda: check_inertia_valid(ctx),
        "self_collision_home": lambda: check_self_collision_home(ctx),
        "stable_hold": lambda: check_stable_hold(ctx),
        "actuators": lambda: check_actuators(ctx),
        "sources_complete": lambda: check_sources_complete(ctx),
    }
    checks: list[CheckResult] = []
    for cid in CHECK_IDS:
        if spec_bad and cid in SPEC_DEPENDENT:
            checks.append(result(cid, False, message=f"spec could not be loaded: {ctx.spec_error}",
                                 fix_hint="Fix spec.yaml so it validates (`sim-anything validate spec.yaml`); "
                                          "the error names the offending field."))
        elif ctx.model is None and cid not in ("compiles", "sources_complete"):
            checks.append(_not_run(cid, "model did not compile",
                                   "Fix the `compiles` failure first; this check runs once the model loads."))
        else:
            checks.append(_guard(cid, model_checks[cid]))
    return CheckReport.from_checks(str(model_path), None if spec_path is None else str(spec_path), checks,
                                   mujoco_version=mujoco.__version__)


__all__ = ["run_checks", "CHECK_IDS", "inertia_problems", "check_sources_complete"]
