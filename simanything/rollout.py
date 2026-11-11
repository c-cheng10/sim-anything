"""Record random joint-target rollouts of a built model as npz episodes, e.g. as robot-learning data."""

from __future__ import annotations

import mujoco
import numpy as np

from .control import Arm

TRIES = 1000  # random targets drawn before giving up on a collision-free one


def random_path(arm: Arm, rng: np.random.Generator, q0, n: int) -> np.ndarray:
    """``n`` points of a min-jerk joint path from ``q0`` (excluded) to a random in-limit configuration.

    Unlimited joints are drawn within +-pi. Targets are redrawn until no point on the path self-collides
    (checked on a scratch MjData), so the commanded motion stays physically sensible.
    """
    d = mujoco.MjData(arm.model)
    lo, hi = np.maximum(arm.lower, -np.pi), np.minimum(arm.upper, np.pi)
    s = np.arange(1, n + 1)[:, None] / n
    s = s**3 * (10 - 15 * s + 6 * s**2)
    for _ in range(TRIES):
        path = q0 + (rng.uniform(lo, hi) - q0) * s
        for q in path:
            d.qpos[arm.qadr] = q
            mujoco.mj_fwdPosition(arm.model, d)
            if d.ncon:
                break
        else:
            return path
    raise RuntimeError(f"no collision-free random target in {TRIES} tries")
