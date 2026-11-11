from pathlib import Path

import mujoco
import numpy as np
import pytest

from simanything.builder import build_mjcf
from simanything.control import Arm
from simanything.rollout import random_path
from simanything.spec import load_spec

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def model_path(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("rollout") / "toy_6dof_dh.xml"
    p.write_text(build_mjcf(load_spec(ROOT / "examples" / "toy_6dof_dh.yaml")))
    return p


def _ncon(arm, q) -> int:
    d = mujoco.MjData(arm.model)
    d.qpos[arm.qadr] = q
    mujoco.mj_fwdPosition(arm.model, d)
    return d.ncon


def test_random_path_is_smooth_in_limits_and_collision_free(model_path):
    arm = Arm(model_path)
    rng, q0 = np.random.default_rng(0), np.zeros(6)
    for _ in range(10):
        path = random_path(arm, rng, q0, 50)
        assert path.shape == (50, 6)
        assert np.all(path >= np.maximum(arm.lower, -np.pi)) and np.all(path <= np.minimum(arm.upper, np.pi))
        steps = np.abs(np.diff(np.vstack([q0, path]), axis=0)).max(axis=0)
        assert np.all(steps <= 1.875 / 50 * np.abs(path[-1] - q0) + 1e-9)  # min-jerk peak speed
        assert not any(_ncon(arm, q) for q in path)
        q0 = path[-1]
