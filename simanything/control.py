"""Drive a built model: read state, command joint targets, inverse kinematics, EE moves."""

from __future__ import annotations

from pathlib import Path

import mujoco
import numpy as np


class Arm:
    """A serial arm in a built MJCF model, driven through its position actuators."""

    def __init__(self, model_path: str | Path, ee_site: str = "ee_site"):
        spec = mujoco.MjSpec.from_file(str(model_path))
        # gravity feedforward through the actuators, as real arm controllers do; the built kp alone sags up to ~20 mm
        for b in spec.bodies:
            b.gravcomp = 1.0
        for j in spec.joints:
            j.actgravcomp = True
        self.model = spec.compile()
        self.data = mujoco.MjData(self.model)
        m = self.model
        ids = [j for j in range(m.njnt) if m.jnt_type[j] in (mujoco.mjtJoint.mjJNT_HINGE, mujoco.mjtJoint.mjJNT_SLIDE)]
        self.joints = [m.joint(j).name for j in ids]
        self.qadr = m.jnt_qposadr[ids]
        self.dadr = m.jnt_dofadr[ids]
        limited = m.jnt_limited[ids].astype(bool)
        self.lower = np.where(limited, m.jnt_range[ids, 0], -np.inf)
        self.upper = np.where(limited, m.jnt_range[ids, 1], np.inf)
        act = {int(m.actuator_trnid[a, 0]): a for a in range(m.nu) if m.actuator_trntype[a] == mujoco.mjtTrn.mjTRN_JOINT}
        missing = [m.joint(j).name for j in ids if j not in act]
        if missing:
            raise ValueError(f"no position actuator for joint(s) {', '.join(missing)}")
        self.act = np.array([act[j] for j in ids])
        self.site = m.site(ee_site).id
        self.reset()

    def reset(self) -> None:
        """Back to the ``home`` keyframe (qpos0 if the model has none), holding that pose."""
        key = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_KEY, "home")
        if key >= 0:
            mujoco.mj_resetDataKeyframe(self.model, self.data, key)
        else:
            mujoco.mj_resetData(self.model, self.data)
        self.data.ctrl[self.act] = self.data.qpos[self.qadr]
        mujoco.mj_forward(self.model, self.data)

    def _ee(self, d: mujoco.MjData) -> tuple[np.ndarray, np.ndarray]:
        quat = np.empty(4)
        mujoco.mju_mat2Quat(quat, d.site_xmat[self.site])
        return d.site_xpos[self.site].copy(), quat

    def state(self) -> dict:
        """Joint positions/velocities and the EE position and quaternion (w, x, y, z), in model units."""
        pos, quat = self._ee(self.data)
        return {"joints": self.joints, "q": self.data.qpos[self.qadr].tolist(), "qd": self.data.qvel[self.dadr].tolist(),
                "ee_pos": pos.tolist(), "ee_quat": quat.tolist(), "time": self.data.time}

    def set_targets(self, q) -> np.ndarray:
        """Set joint position targets (clipped to the joint limits); returns what was set."""
        q = np.clip(np.asarray(q, dtype=float), self.lower, self.upper)
        self.data.ctrl[self.act] = q
        return q

    def step(self, n: int = 1) -> None:
        """Advance the simulation ``n`` timesteps."""
        mujoco.mj_step(self.model, self.data, nstep=n)
