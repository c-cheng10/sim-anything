from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("gymnasium")

from gymnasium.utils.env_checker import check_env  # noqa: E402

from simanything.builder import build_mjcf  # noqa: E402
from simanything.gym_env import MAX_DELTA, ReachEnv  # noqa: E402
from simanything.spec import load_spec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def model_path(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("gym") / "toy_6dof_dh.xml"
    p.write_text(build_mjcf(load_spec(ROOT / "examples" / "toy_6dof_dh.yaml")))
    return p


@pytest.mark.filterwarnings("ignore::UserWarning")  # infinite observation bounds, no env spec
def test_check_env(model_path):
    check_env(ReachEnv(model_path))


def test_seeded_resets_reproduce(model_path):
    env = ReachEnv(model_path)
    a, _ = env.reset(seed=3)
    env.step(env.action_space.sample())
    b, _ = env.reset(seed=3)
    c, _ = env.reset(seed=4)
    assert np.array_equal(a, b) and not np.array_equal(a[-3:], c[-3:])


def test_ik_driven_actions_reach_the_target(model_path):
    env = ReachEnv(model_path)
    for seed in range(3):
        env.reset(seed=seed)
        goal = env.arm.ik(env.target)[0]
        rewards = []
        for _ in range(env.max_steps):
            _, r, terminated, truncated, info = env.step(np.clip((goal - env.targets) / MAX_DELTA, -1, 1))
            rewards.append(r)
            if terminated or truncated:
                break
        assert terminated and info["is_success"] and info["distance"] < 0.01 and rewards[-1] > rewards[0] + 0.5

