"""Shared state for one checker run: the compiled model, the spec (SI) and the joint mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import mujoco
import numpy as np

from ..schemas import CheckResult, Severity
from ..spec import Spec, load_spec

HINGE = int(mujoco.mjtJoint.mjJNT_HINGE)
SLIDE = int(mujoco.mjtJoint.mjJNT_SLIDE)
BALL = int(mujoco.mjtJoint.mjJNT_BALL)
FREE = int(mujoco.mjtJoint.mjJNT_FREE)
JOINT_TYPE_NAMES = {HINGE: "hinge", SLIDE: "slide", BALL: "ball", FREE: "free"}

SKIP_NO_SPEC = "skipped: no spec"


def result(id: str, passed: bool, *, severity: Severity = "error", message: str = "",
           fix_hint: Optional[str] = None, measured: Any = None, expected: Any = None,
           tolerance: Any = None, details: Optional[dict[str, Any]] = None) -> CheckResult:
    return CheckResult(id=id, passed=bool(passed), severity=severity, message=message,
                       fix_hint=None if passed else fix_hint, measured=measured, expected=expected,
                       tolerance=tolerance, details=details or {})


def skipped_no_spec(id: str) -> CheckResult:
    return result(id, True, severity="info", message=SKIP_NO_SPEC)


def _name(model: mujoco.MjModel, obj: mujoco.mjtObj, i: int) -> str:
    return mujoco.mj_id2name(model, obj, i) or f"<{obj.name[6:].lower()} {i}>"


@dataclass
class CheckContext:
    model_path: str
    spec_path: Optional[str]
    model: Optional[mujoco.MjModel] = None
    data: Optional[mujoco.MjData] = None
    compile_error: Optional[str] = None
    spec_raw: Optional[Spec] = None  # as written (units as declared)
    spec: Optional[Spec] = None  # SI copy
    spec_error: Optional[str] = None
    joint_ids: list[Optional[int]] = field(default_factory=list)  # per spec joint: model joint id
    home_qpos: Optional[np.ndarray] = None
    home_source: str = "qpos0"

    # ------------------------------------------------------------------ #
    @classmethod
    def load(cls, model_path: str | Path, spec_path: str | Path | None) -> "CheckContext":
        ctx = cls(model_path=str(model_path), spec_path=None if spec_path is None else str(spec_path))
        if spec_path is not None:
            try:
                ctx.spec_raw = load_spec(spec_path)
                ctx.spec = ctx.spec_raw.to_si()
            except Exception as e:  # noqa: BLE001 - any spec problem is reported, not raised
                ctx.spec_error = f"{type(e).__name__}: {e}"
        try:
            ctx.model = mujoco.MjModel.from_xml_path(str(model_path))
            ctx.data = mujoco.MjData(ctx.model)
        except Exception as e:  # noqa: BLE001
            ctx.compile_error = str(e).strip() or type(e).__name__
            ctx.model = None
            ctx.data = None
        if ctx.model is not None:
            ctx._match_joints()
            ctx._home()
        return ctx

    # ------------------------------------------------------------------ #
    @property
    def has_spec(self) -> bool:
        return self.spec is not None

    def _match_joints(self) -> None:
        m = self.model
        assert m is not None
        if self.spec is None:
            return
        self.joint_ids = []
        for j in self.spec.joints:
            jid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, j.name)
            self.joint_ids.append(jid if jid >= 0 else None)

    def _home(self) -> None:
        m = self.model
        assert m is not None
        q = m.qpos0.copy()
        kid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_KEY, "home")
        if kid >= 0:
            q = m.key_qpos[kid].copy()
            self.home_source = "keyframe 'home'"
        elif self.spec is not None:
            for j, jid in zip(self.spec.joints, self.joint_ids):
                if jid is not None and int(m.jnt_type[jid]) in (HINGE, SLIDE):
                    q[m.jnt_qposadr[jid]] = j.home
            self.home_source = "spec joints[*].home"
        self.home_qpos = q

    # ------------------------------------------------------------------ #
    # Naming helpers
    def joint_name(self, jid: int) -> str:
        assert self.model is not None
        return _name(self.model, mujoco.mjtObj.mjOBJ_JOINT, jid)

    def body_name(self, bid: int) -> str:
        assert self.model is not None
        return _name(self.model, mujoco.mjtObj.mjOBJ_BODY, bid)

    def robot_joint_ids(self) -> list[int]:
        """All hinge/slide joints of the model, in model order."""
        m = self.model
        assert m is not None
        return [j for j in range(m.njnt) if int(m.jnt_type[j]) in (HINGE, SLIDE)]

    def matched(self) -> list[tuple[int, int]]:
        """(spec index, model joint id) for spec joints present in the model as hinge/slide."""
        assert self.model is not None
        return [(i, jid) for i, jid in enumerate(self.joint_ids)
                if jid is not None and int(self.model.jnt_type[jid]) in (HINGE, SLIDE)]

    def body_spec_path(self, bid: int) -> Optional[str]:
        """Spec path of the link a model body represents (``joints[i].link`` / ``base.link``)."""
        m = self.model
        assert m is not None
        if bid <= 0:
            return None
        weld = int(m.body_weldid[bid])
        if weld == 0:
            return "base.link"
        for i, jid in enumerate(self.joint_ids):
            if jid is not None and int(m.jnt_bodyid[jid]) == weld:
                return f"joints[{i}].link"
        return None

    def body_label(self, bid: int) -> str:
        p = self.body_spec_path(bid)
        return f"'{self.body_name(bid)}'" + (f" ({p})" if p else "")

    def spec_index_of_joint(self, jid: int) -> Optional[int]:
        for i, j in enumerate(self.joint_ids):
            if j == jid:
                return i
        return None

    def joint_label(self, jid: int) -> str:
        i = self.spec_index_of_joint(jid)
        return f"'{self.joint_name(jid)}'" + (f" (joints[{i}])" if i is not None else "")
