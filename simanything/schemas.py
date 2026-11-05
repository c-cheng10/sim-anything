"""Shared machine-readable result types (see docs/CONTRACTS.md).

These are the JSON contracts between the checker, evaluator, loop, report and
the agent. Change them only together with docs/CONTRACTS.md.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["error", "warning", "info"]


class CheckResult(BaseModel):
    """One verifier check. ``pass`` is a Python keyword, hence the alias."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    passed: bool = Field(alias="pass")
    measured: Any = None
    expected: Any = None
    tolerance: Any = None
    severity: Severity = "error"
    message: str = ""
    fix_hint: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)


class CheckReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model: str
    spec: Optional[str] = None
    passed: bool  # True iff no check with severity "error" failed
    n_checks: int
    n_failed: int  # failed checks of any severity
    n_errors: int  # failed checks with severity "error"
    checks: list[CheckResult]
    mujoco_version: Optional[str] = None

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)

    @classmethod
    def from_checks(cls, model: str, spec: Optional[str], checks: list[CheckResult],
                    mujoco_version: Optional[str] = None) -> "CheckReport":
        n_failed = sum(not c.passed for c in checks)
        n_errors = sum((not c.passed) and c.severity == "error" for c in checks)
        return cls(model=model, spec=spec, passed=n_errors == 0, n_checks=len(checks), n_failed=n_failed,
                   n_errors=n_errors, checks=checks, mujoco_version=mujoco_version)


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #


class EESpec(BaseModel):
    """End-effector point/frame on one side of a mapping.

    Either ``site`` (a site name) or ``body`` (+ optional ``pos``/``quat`` offset
    in that body's frame) must be given.
    """

    model_config = ConfigDict(extra="forbid")

    site: Optional[str] = None
    body: Optional[str] = None
    pos: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    quat: list[float] = Field(default_factory=lambda: [1.0, 0.0, 0.0, 0.0])


class MappingSide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    joints: list[str]
    ee: EESpec


class JointConvention(BaseModel):
    """q_reference = sign * q_candidate + offset   (offset in rad for hinges, m for slides)."""

    model_config = ConfigDict(extra="forbid")

    sign: Literal[-1, 1] = 1
    offset: float = 0.0


class Mapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    robot: Optional[str] = None
    candidate: MappingSide
    reference: MappingSide
    joint_conventions: Optional[list[JointConvention]] = None
    fit_conventions: bool = True


class ErrorStats(BaseModel):
    mean: float
    p95: float
    max: float


class JointLimitDiff(BaseModel):
    candidate: str
    reference: str
    candidate_range: list[float]  # in reference coordinates (after conventions)
    reference_range: list[float]
    lower_diff: float  # candidate - reference, rad or m
    upper_diff: float


class EvalResult(BaseModel):
    candidate: str
    reference: str
    robot: Optional[str] = None
    n_samples: int
    seed: int
    dof_candidate: int
    dof_reference: int  # number of mapped reference joints
    dof_match: bool
    conventions: list[JointConvention]
    conventions_fitted: bool
    ee_position_error_mm: ErrorStats
    ee_orientation_error_deg: ErrorStats  # raw frames
    ee_orientation_error_aligned_deg: ErrorStats  # after best constant tool-frame rotation
    joint_limits: list[JointLimitDiff]
    joint_limit_mae_deg: float  # mean |diff| over hinge lower+upper bounds, degrees
    mass_candidate: float
    mass_reference: float
    mass_diff: float
    mass_rel_diff: float
    score: float  # 0..100
    score_breakdown: dict[str, float]
    notes: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Loop history
# --------------------------------------------------------------------------- #


class IterationRecord(BaseModel):
    iteration: int
    timestamp: str
    passed: bool
    n_errors: int
    n_failed: int
    failed_ids: list[str]
    note: Optional[str] = None
    build_error: Optional[str] = None


class History(BaseModel):
    robot: Optional[str] = None
    spec: str
    max_iter: int
    iterations: list[IterationRecord] = Field(default_factory=list)
    status: Literal["running", "passed", "max_iter_reached"] = "running"
