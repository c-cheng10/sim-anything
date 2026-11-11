"""Record random joint-target rollouts of a built model as npz episodes, e.g. as robot-learning data."""

from __future__ import annotations

import json
from pathlib import Path

import mujoco
import numpy as np

from .control import Arm

TRIES = 1000  # random targets drawn before giving up on a collision-free one
FPS = 50  # recorded steps per second; the physics runs at the model timestep in between
HOLD = 100  # recorded steps per random target (2 s); faster moves outrun the weak wrist servos
SIZE = 128  # image width and height, pixels


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
        if not any(arm.collides(q, d) for q in path):
            return path
    raise RuntimeError(f"no collision-free random target in {TRIES} tries")


def camera(arm: Arm) -> mujoco.MjvCamera:
    """A fixed free camera above the base, back by about twice the model's extent so the swinging arm stays in view."""
    cam = mujoco.MjvCamera()
    cam.lookat[:] = arm.model.body_pos[1]
    cam.lookat[2] = arm.model.stat.center[2]
    cam.distance = 2.2 * arm.model.stat.extent
    cam.azimuth, cam.elevation = 135.0, -25.0
    return cam


def record(model_path: str | Path, out_dir: str | Path, episodes: int = 10, steps: int = 300, seed: int = 0,
           images: bool = False, ee_site: str = "ee_site") -> Path:
    """Record ``episodes`` random-motion rollouts as ``episode_XXX.npz`` plus ``meta.json`` in ``out_dir``.

    Each episode starts at home and follows a new random target every ``HOLD`` steps along a smooth
    collision-free path. Per step, the state before the step and the joint targets commanded for it:
    ``qpos``, ``qvel``, ``ee_pos``, ``ee_quat`` (w, x, y, z), ``action`` and, with ``images``, a
    ``SIZE``x``SIZE`` RGB ``image`` (headless, MuJoCo needs ``MUJOCO_GL`` set before it is imported).
    Deterministic for a given seed. Returns the meta.json path.
    """
    if episodes < 1:
        raise ValueError(f"episodes must be >= 1, got {episodes}")
    arm, out, rng = Arm(model_path, ee_site), Path(out_dir), np.random.default_rng(seed)
    out.mkdir(parents=True, exist_ok=True)
    sub = max(1, round(1 / (FPS * arm.model.opt.timestep)))
    renderer, cam = (mujoco.Renderer(arm.model, SIZE, SIZE), camera(arm)) if images else (None, None)
    try:
        for e in range(episodes):
            arm.reset()
            q = arm.data.qpos[arm.qadr].copy()
            ep = {k: [] for k in ("qpos", "qvel", "ee_pos", "ee_quat", "action") + (("image",) if images else ())}
            for t in range(steps):
                if t % HOLD == 0:
                    path = random_path(arm, rng, q, HOLD)
                s = arm.state()
                for k, v in (("qpos", s["q"]), ("qvel", s["qd"]), ("ee_pos", s["ee_pos"]), ("ee_quat", s["ee_quat"])):
                    ep[k].append(v)
                if renderer:
                    renderer.update_scene(arm.data, cam)
                    ep["image"].append(renderer.render())
                q = arm.set_targets(path[t % HOLD])
                ep["action"].append(q)
                arm.step(sub)
            arrays = {k: np.array(v) for k, v in ep.items()}
            np.savez_compressed(out / f"episode_{e:03d}.npz", **arrays)
    finally:
        if renderer:
            renderer.close()
    meta = {"model": str(Path(model_path).resolve()), "joints": arm.joints,
            "lower": [None if np.isinf(x) else float(x) for x in arm.lower],  # None: unlimited
            "upper": [None if np.isinf(x) else float(x) for x in arm.upper],
            "timestep": arm.model.opt.timestep, "fps": FPS, "episodes": episodes, "seed": seed,
            "arrays": {k: {"shape": list(a.shape), "dtype": str(a.dtype)} for k, a in arrays.items()}}
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return out / "meta.json"
