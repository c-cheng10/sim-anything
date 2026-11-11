"""Run the reach environment with a random policy and an IK expert, printing episode returns.

Needs gymnasium (no RL library). Run from the repository root: python examples/train_reach.py
"""

import tempfile
from pathlib import Path

import numpy as np

from simanything.builder import build_file
from simanything.gym_env import MAX_DELTA, ReachEnv

model = build_file(Path(__file__).parent / "toy_6dof_dh.yaml", Path(tempfile.mkdtemp()) / "toy_6dof_dh.xml")
env = ReachEnv(model)
env.action_space.seed(0)


def ik_expert(env):
    """Step the joint targets toward an IK solution for the target, at most MAX_DELTA per step."""
    goal = env.arm.ik(env.target)[0]
    return lambda obs: np.clip((goal - env.targets) / MAX_DELTA, -1, 1)


for name in ("random", "ik expert"):
    for episode in range(3):
        obs, info = env.reset(seed=episode)
        policy = ik_expert(env) if name == "ik expert" else lambda obs: env.action_space.sample()
        ret, done = 0.0, False
        while not done:
            obs, reward, terminated, truncated, info = env.step(policy(obs))
            ret, done = ret + reward, terminated or truncated
        print(f"{name:9s} episode {episode}: return {ret:7.2f}, final distance {info['distance'] * 1000:6.1f} mm, "
              f"success {info['is_success']}")
env.close()
