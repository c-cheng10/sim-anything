import math
import subprocess
import sys
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


def _random_targets(arm, n, seed=0, collision_free=False):
    """EE poses (pos, quat) from FK of random in-limit configurations."""
    rng, d, out = np.random.default_rng(seed), mujoco.MjData(arm.model), []
    lo, hi = np.maximum(arm.lower, -np.pi), np.minimum(arm.upper, np.pi)
    while len(out) < n:
        d.qpos[arm.qadr] = rng.uniform(lo, hi)
        mujoco.mj_forward(arm.model, d)
        if not (collision_free and d.ncon):
            out.append(arm._ee(d))
    return out


def test_ik_reaches_random_targets_within_limits(model_path):
    arm = Arm(model_path)
    before = arm.data.qpos.copy()
    for pos, quat in _random_targets(arm, 20):
        q, perr, rerr = arm.ik(pos)
        assert perr < 1e-3 and rerr == 0
        assert np.all(q >= arm.lower) and np.all(q <= arm.upper)
        q, perr, rerr = arm.ik(pos, quat)
        assert perr < 1e-3 and rerr < 1e-3
        assert np.all(q >= arm.lower) and np.all(q <= arm.upper)
        d = mujoco.MjData(arm.model)  # the returned q really puts the EE there
        d.qpos[arm.qadr] = q
        mujoco.mj_kinematics(arm.model, d)
        assert np.linalg.norm(d.site_xpos[arm.site] - pos) < 1e-3
    assert np.array_equal(arm.data.qpos, before)  # the live sim is untouched


def test_ik_from_given_start(model_path):
    arm = Arm(model_path)
    q0 = np.array([0.3, -1.0, 1.2, -0.5, 0.7, 0.1])
    d = mujoco.MjData(arm.model)
    d.qpos[arm.qadr] = q0
    mujoco.mj_kinematics(arm.model, d)
    q, perr, rerr = arm.ik(*arm._ee(d), q0=q0)
    assert np.allclose(q, q0) and perr < 1e-9 and rerr < 1e-9


def test_move_to_reaches_target(model_path):
    arm = Arm(model_path)
    for pos, quat in _random_targets(arm, 5, seed=1, collision_free=True):
        arm.reset()
        perr, rerr = arm.move_to(pos, quat)
        assert perr < 0.01 and rerr < 0.05  # measured <= 4 mm / 0.03 rad lag at the end of the 2 s move
        arm.step(250)  # settle 0.5 s
        s = arm.state()
        # measured <= 3 um settled over 50 targets (gravity feedforward); 1 mm still fails any sag
        assert np.linalg.norm(np.array(s["ee_pos"]) - pos) < 1e-3
        assert np.linalg.norm(s["qd"]) < 1e-2


def test_render_writes_png(model_path, tmp_path):
    from simanything import render

    if render.detect_backend() != "mujoco":
        pytest.skip("no offscreen MuJoCo GL renderer available")
    out = tmp_path / "arm.png"
    # a child process: MUJOCO_GL must be set before mujoco is imported
    code = f"from simanything.control import Arm; Arm({str(model_path)!r}).render({str(out)!r})"
    subprocess.run([sys.executable, "-c", code], env=render._child_env(render._gl_cache or ""), check=True, timeout=120)
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
