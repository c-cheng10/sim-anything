"""Drive a built model: read state, command joint targets, inverse kinematics, EE moves."""

from __future__ import annotations

from pathlib import Path

import mujoco
import numpy as np

MAX_STEP = 0.3  # rad (or m) per DLS iteration; larger steps overshoot into local minima more often
RESTARTS = 20  # random restarts after a failed start; 200 random toy_6dof_dh poses needed at most 10


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

    def ik(self, target_pos, target_quat=None, q0=None, tol: float = 1e-6, max_iter: int = 200,
           damping: float = 1e-3) -> tuple[np.ndarray, float, float]:
        """Damped least-squares IK for the EE site, within the joint limits.

        Starts from ``q0`` (default: the current joint positions) on a scratch MjData, so the live
        simulation is untouched. A start that ends in a local minimum or in a self-collision is retried
        from seeded random in-limit configurations. Position-only when ``target_quat`` (w, x, y, z) is None.
        Returns the best ``(q, position error [m], orientation error [rad])``.
        """
        d = mujoco.MjData(self.model)
        d.qpos[:] = self.data.qpos
        q = self.data.qpos[self.qadr] if q0 is None else np.asarray(q0, dtype=float)
        rng = np.random.default_rng(0)
        lo, hi = np.maximum(self.lower, -np.pi), np.minimum(self.upper, np.pi)
        best, best_key = None, None
        for _ in range(1 + RESTARTS):
            res = self._dls(d, q, np.asarray(target_pos, dtype=float), target_quat, tol, max_iter, damping)
            mujoco.mj_fwdPosition(self.model, d)  # contacts at the solution
            solved = res[1] < tol and res[2] < tol
            key = (not solved, d.ncon > 0, res[1] + res[2])
            if best is None or key < best_key:
                best, best_key = res, key
            if solved and d.ncon == 0:
                break
            q = rng.uniform(lo, hi)
        return best

    def _dls(self, d, q, target_pos, target_quat, tol, max_iter, damping):
        """One DLS run from ``q``; leaves ``d`` at the returned configuration."""
        m = self.model
        q = np.clip(q, self.lower, self.upper)
        jacp, jacr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
        for it in range(max_iter + 1):
            d.qpos[self.qadr] = q
            mujoco.mj_kinematics(m, d)
            mujoco.mj_comPos(m, d)  # mj_jacSite needs the com-based quantities
            pos, quat = self._ee(d)
            err = target_pos - pos
            err_rot = np.zeros(3) if target_quat is None else _rot_err(quat, target_quat)
            if (np.linalg.norm(err) < tol and np.linalg.norm(err_rot) < tol) or it == max_iter:
                break
            mujoco.mj_jacSite(m, d, jacp, jacr, self.site)
            J, e = (jacp, err) if target_quat is None else (np.vstack([jacp, jacr]), np.concatenate([err, err_rot]))
            J = J[:, self.dadr]
            dq = J.T @ np.linalg.solve(J @ J.T + damping**2 * np.eye(len(e)), e)
            dq *= min(1.0, MAX_STEP / max(np.abs(dq).max(), 1e-12))  # small steps keep DLS out of wild jumps
            q = np.clip(q + dq, self.lower, self.upper)
        return q, float(np.linalg.norm(err)), float(np.linalg.norm(err_rot))

    def move_to(self, target_pos, target_quat=None, duration: float = 2.0) -> tuple[float, float]:
        """IK, then a minimum-jerk joint-space move from the current pose through the actuators.

        Steps the simulation for ``duration`` seconds; returns the final EE (position [m], orientation [rad])
        error, the orientation error being 0 when ``target_quat`` is None.
        """
        q1, _, _ = self.ik(target_pos, target_quat)
        q0 = self.data.qpos[self.qadr].copy()
        n = max(1, round(duration / self.model.opt.timestep))
        for i in range(1, n + 1):
            s = i / n
            self.set_targets(q0 + (q1 - q0) * s**3 * (10 - 15 * s + 6 * s**2))
            self.step()
        pos, quat = self._ee(self.data)
        rot = 0.0 if target_quat is None else float(np.linalg.norm(_rot_err(quat, target_quat)))
        return float(np.linalg.norm(np.asarray(target_pos, dtype=float) - pos)), rot


def _rot_err(quat: np.ndarray, target_quat) -> np.ndarray:
    """World-frame rotation vector taking orientation ``quat`` to ``target_quat`` (both w, x, y, z)."""
    neg, dq, vel, t = np.empty(4), np.empty(4), np.empty(3), np.asarray(target_quat, dtype=float)
    mujoco.mju_negQuat(neg, quat)
    mujoco.mju_mulQuat(dq, t / np.linalg.norm(t), neg)
    mujoco.mju_quat2Vel(vel, dq, 1.0)
    return vel
