"""A Gymnasium reach task over Arm. Needs the optional ``gymnasium`` dependency; nothing is registered."""

from __future__ import annotations

from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np

from .control import Arm
from .rollout import FPS, random_path

MAX_DELTA = 0.05  # joint-target change per step at |action| = 1, rad (or m); 2.5 rad/s at 50 steps/s
SUCCESS = 0.01  # m; EE-to-target distance that ends the episode
BONUS = 1.0  # reward added on success


class ReachEnv(gym.Env):
    """Move the EE site to a random reachable target position.

    Observation: joint positions, joint velocities, EE position, target position (model units).
    Action: [-1, 1] per joint, scaled by ``MAX_DELTA`` and added to the current joint targets.
    Reward: minus the EE-to-target distance [m], plus ``BONUS`` on success (within ``SUCCESS``), which
    terminates; truncated after ``max_steps`` steps of 1/``FPS`` s. Targets are the EE positions of seeded
    random in-limit, collision-free configurations.
    ``env.targets`` holds the current joint targets, ``env.target`` the target position, ``env.arm`` the Arm.
    """

    def __init__(self, model_path: str | Path, max_steps: int = 200,
                 ee_site: str = "ee_site"):
        self.arm = Arm(model_path, ee_site)
        n = len(self.arm.joints)
        self.action_space = gym.spaces.Box(-1.0, 1.0, (n,), np.float32)
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, (2 * n + 6,), np.float64)
        self.max_steps = max_steps
        self._sub = max(1, round(1 / (FPS * self.arm.model.opt.timestep)))

    def _obs(self) -> np.ndarray:
        s = self.arm.state()
        return np.concatenate([s["q"], s["qd"], s["ee_pos"], self.target])

    def _distance(self) -> float:
        return float(np.linalg.norm(self.arm.data.site_xpos[self.arm.site] - self.target))

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.arm.reset()
        self.targets = self.arm.data.qpos[self.arm.qadr].copy()
        d = mujoco.MjData(self.arm.model)
        d.qpos[self.arm.qadr] = random_path(self.arm, self.np_random, self.targets, 1)[-1]
        mujoco.mj_kinematics(self.arm.model, d)
        self.target = d.site_xpos[self.arm.site].copy()
        self._t = 0
        return self._obs(), {"distance": self._distance()}

    def step(self, action):
        self.targets = self.arm.set_targets(self.targets + MAX_DELTA * np.clip(action, -1, 1))
        self.arm.step(self._sub)
        self._t += 1
        dist = self._distance()
        success = dist < SUCCESS
        return (self._obs(), -dist + BONUS * success, success, self._t >= self.max_steps,
                {"distance": dist, "is_success": success})
