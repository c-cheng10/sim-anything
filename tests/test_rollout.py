import json
import subprocess
import sys
from pathlib import Path

import mujoco
import numpy as np
import pytest

from simanything.builder import build_mjcf
from simanything.control import Arm
from simanything.rollout import random_path, record
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


def test_record_shapes_determinism_limits_and_no_collisions(model_path, tmp_path):
    meta = json.loads(record(model_path, tmp_path / "a", episodes=2, steps=120, seed=7).read_text())
    record(model_path, tmp_path / "b", episodes=2, steps=120, seed=7)
    assert meta["joints"] == ["j1", "j2", "j3", "j4", "j5", "j6"] and meta["seed"] == 7 and meta["fps"] == 50
    assert {k: v["shape"] for k, v in meta["arrays"].items()} == {
        "qpos": [120, 6], "qvel": [120, 6], "ee_pos": [120, 3], "ee_quat": [120, 4], "action": [120, 6]}
    arm = Arm(model_path)
    for e in range(2):
        a, b = np.load(tmp_path / "a" / f"episode_{e:03d}.npz"), np.load(tmp_path / "b" / f"episode_{e:03d}.npz")
        assert sorted(a.files) == sorted(meta["arrays"]) and all(np.array_equal(a[k], b[k]) for k in a.files)
        assert np.all(a["action"] >= arm.lower) and np.all(a["action"] <= arm.upper)
        assert not any(_ncon(arm, q) for q in a["qpos"])
    first, other = np.load(tmp_path / "a" / "episode_000.npz"), np.load(tmp_path / "a" / "episode_001.npz")
    assert not np.array_equal(first["action"], other["action"])


def test_cli_records_images_only_with_the_flag(model_path, tmp_path):
    from simanything import render

    if render.detect_backend() != "mujoco":
        pytest.skip("no offscreen MuJoCo GL renderer available")
    cmd = [sys.executable, "-m", "simanything", "rollouts", str(model_path), "-n", "1", "--steps", "3"]
    env = render._child_env(render._gl_cache or "")
    subprocess.run(cmd + ["-o", str(tmp_path / "plain")], env=env, check=True, timeout=120)
    subprocess.run(cmd + ["-o", str(tmp_path / "img"), "--images"], env=env, check=True, timeout=120)
    assert "image" not in np.load(tmp_path / "plain" / "episode_000.npz").files
    img = np.load(tmp_path / "img" / "episode_000.npz")["image"]
    assert img.shape == (3, 128, 128, 3) and img.dtype == np.uint8 and img.any()
    assert json.loads((tmp_path / "img" / "meta.json").read_text())["arrays"]["image"]["shape"] == [3, 128, 128, 3]
