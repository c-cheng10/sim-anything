import math
from pathlib import Path

import mujoco
import numpy as np
import pytest

from simanything.builder import build_mjcf
from simanything.control import Arm
from simanything.spec import load_spec

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def model_path(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("control") / "toy_6dof_dh.xml"
    p.write_text(build_mjcf(load_spec(ROOT / "examples" / "toy_6dof_dh.yaml")))
    return p


def test_load(model_path):
    arm = Arm(model_path)
    assert arm.joints == ["j1", "j2", "j3", "j4", "j5", "j6"]
    assert np.allclose(arm.lower[2:4], [-math.pi, -2 * math.pi]) and np.allclose(arm.upper[2:4], [math.pi, 2 * math.pi])
    assert [arm.model.actuator(a).name for a in arm.act] == [f"{j}_act" for j in arm.joints]
    with pytest.raises(KeyError):
        Arm(model_path, ee_site="nope")


def test_reset_goes_home(model_path):
    arm = Arm(model_path)
    arm.data.qpos[:] = 0.3
    arm.data.ctrl[:] = 0.3
    arm.reset()
    home = arm.model.key("home").qpos
    assert np.allclose(arm.data.qpos, home) and np.allclose(arm.data.ctrl, home) and not arm.data.qvel.any()


def test_state_at_home(model_path):
    s = Arm(model_path).state()
    # home is the stretched UR-like pose: EE at x = -(a2 + a3), y = -(d4 + d6), z = d1 - d5 (DH, metres)
    assert np.allclose(s["ee_pos"], [-0.75, -0.22, 0.05]) and np.allclose(s["q"], 0) and np.allclose(s["qd"], 0)
    assert np.isclose(np.linalg.norm(s["ee_quat"]), 1)


def test_set_targets_clips_to_limits(model_path):
    arm = Arm(model_path)
    got = arm.set_targets([0.1, 0.2, 4.0, -7.0, 0.0, 0.0])
    assert np.allclose(got, [0.1, 0.2, math.pi, -2 * math.pi, 0, 0]) and np.allclose(arm.data.ctrl[arm.act], got)


def test_step_tracks_targets(model_path):
    arm = Arm(model_path)
    q = arm.set_targets([0.5, -0.4, 0.8, 0.3, -0.6, 0.2])
    arm.step(1000)  # 2 s
    assert np.isclose(arm.data.time, 2.0) and np.abs(arm.data.qpos[arm.qadr] - q).max() < 1e-3
