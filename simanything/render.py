"""Front / side / top renders of a MuJoCo model at its home pose.

Two backends:

* ``mujoco``: MuJoCo's own offscreen OpenGL renderer (OSMesa or EGL). It runs
  in a child process, so a broken GL stack can neither crash nor hang the
  caller, and the caller's ``import mujoco`` is never tied to a GL platform.
* ``matplotlib``: works everywhere. Geom silhouettes (convex hulls of the
  primitives) are drawn from MuJoCo-computed world poses with an orthographic
  projection per view, plus joint anchors and the end-effector site(s).

``detect_backend()`` probes the MuJoCo renderer once (in a subprocess, with a
timeout) and caches the answer.
"""

from __future__ import annotations

import json
import logging
import math
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

VIEWS = ("front", "side", "top")

# Camera orientation per view as MuJoCo free-camera (azimuth, elevation) in degrees.
# Robots conventionally face +x with z up:
#   front: camera between +x and -y, 3/4 view (an arm reaching along +x would be
#          fully foreshortened in a straight-on +x view; the matplotlib
#          fallback keeps the orthographic +x projection)
#   side : camera on -y looking toward +y  (image right = +x, up = +z)
#   top  : camera above looking down       (image right = +x, up = +y)
_MJ_CAMERAS = {"front": (135.0, -20.0), "side": (90.0, -15.0), "top": (90.0, -90.0)}
_PERSPECTIVE_FOVY = 30.0  # degrees, front/side MuJoCo views
_ORTHO_CAMERAS = {"front": (180.0, 0.0), "side": (90.0, 0.0), "top": (90.0, -90.0)}
_VIEW_LABELS = {
    "front": ("front (from +X)", "y [m]", "z [m]"),
    "side": ("side (from -Y)", "x [m]", "z [m]"),
    "top": ("top (from +Z)", "x [m]", "y [m]"),
}

_PROBE_TIMEOUT_S = 30.0
_WORKER_TIMEOUT_S = 180.0
_backend_cache: str | None = None
_gl_cache: str | None = None

_EE_HINTS = ("ee", "tool", "flange", "tcp", "attach", "grip", "end")


# --------------------------------------------------------------------------- #
# Backend detection
# --------------------------------------------------------------------------- #


def _gl_candidates() -> list[str]:
    preset = os.environ.get("MUJOCO_GL", "").strip().lower()
    if preset:
        return [preset]
    if platform.system() == "Linux":
        return ["osmesa", "egl"]
    return [""]  # macOS / Windows: MuJoCo's default (GLFW / CGL / WGL)


def _child_env(gl: str) -> dict[str, str]:
    env = dict(os.environ)
    if gl:
        env["MUJOCO_GL"] = gl
        if gl in ("osmesa", "egl"):
            env.setdefault("PYOPENGL_PLATFORM", gl)
    pkg_root = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = pkg_root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


_PROBE_CODE = """
import mujoco
m = mujoco.MjModel.from_xml_string(
    "<mujoco><worldbody><light pos='0 0 1'/><geom type='sphere' size='0.1'/></worldbody></mujoco>")
d = mujoco.MjData(m)
mujoco.mj_forward(m, d)
r = mujoco.Renderer(m, 32, 32)
r.update_scene(d)
img = r.render()
assert img.shape == (32, 32, 3) and int(img.max()) > 0, "blank probe image"
print("ok")
"""


def _probe(gl: str) -> bool:
    try:
        res = subprocess.run([sys.executable, "-c", _PROBE_CODE], env=_child_env(gl), capture_output=True,
                             text=True, timeout=_PROBE_TIMEOUT_S)
    except (subprocess.TimeoutExpired, OSError) as e:
        log.debug("MuJoCo GL probe (%s) failed: %s", gl or "default", e)
        return False
    ok = res.returncode == 0 and "ok" in res.stdout
    if not ok:
        log.debug("MuJoCo GL probe (%s) failed: %s", gl or "default", res.stderr.strip()[-500:])
    return ok


def detect_backend() -> str:
    """'mujoco' if an offscreen MuJoCo renderer works here, else 'matplotlib' (cached)."""
    global _backend_cache, _gl_cache
    if _backend_cache is None:
        _backend_cache = "matplotlib"
        if os.environ.get("MUJOCO_GL", "").strip().lower() not in ("disable", "disabled", "off", "false", "0"):
            for gl in _gl_candidates():
                if _probe(gl):
                    _backend_cache, _gl_cache = "mujoco", gl
                    break
        if _backend_cache == "mujoco":
            log.info("render backend: mujoco (MUJOCO_GL=%s)", _gl_cache or "default")
        else:
            log.info("render backend: matplotlib (no working offscreen MuJoCo GL)")
    return _backend_cache


# --------------------------------------------------------------------------- #
# Shared model helpers
# --------------------------------------------------------------------------- #


def _load_home(model_path: Path):
    import mujoco

    m = mujoco.MjModel.from_xml_path(str(model_path))
    d = mujoco.MjData(m)
    _reset_home(m, d)
    return m, d


def _reset_home(m, d) -> None:
    import mujoco

    key = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_KEY, "home")
    if key >= 0:
        mujoco.mj_resetDataKeyframe(m, d, key)
    else:
        mujoco.mj_resetData(m, d)
    mujoco.mj_forward(m, d)


def _visible_geoms(m) -> list[int]:
    import mujoco

    out = []
    for g in range(m.ngeom):
        if m.geom_type[g] in (mujoco.mjtGeom.mjGEOM_PLANE, mujoco.mjtGeom.mjGEOM_HFIELD):
            continue
        if m.geom_group[g] > 2 or _geom_rgba(m, g)[3] <= 0.0:
            continue
        out.append(g)
    return out


def _geom_rgba(m, g: int) -> np.ndarray:
    mat = int(m.geom_matid[g])
    rgba = np.array(m.mat_rgba[mat] if mat >= 0 else m.geom_rgba[g], dtype=float)
    return rgba


def _ee_sites(m) -> list[int]:
    import mujoco

    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_SITE, i) or "" for i in range(m.nsite)]
    hits = [i for i, n in enumerate(names) if any(h in n.lower() for h in _EE_HINTS)]
    return hits or list(range(m.nsite))


def _bbox(m, d) -> tuple[np.ndarray, np.ndarray]:
    """World AABB of visible geoms, sites and body origins at the current pose."""
    pts = [d.xpos[b] for b in range(1, m.nbody)] + [d.site_xpos[s] for s in range(m.nsite)]
    signs = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)], dtype=float)
    for g in _visible_geoms(m):
        c, h = m.geom_aabb[g, :3], m.geom_aabb[g, 3:]
        local = c + signs * h
        pts.extend(d.geom_xpos[g] + local @ d.geom_xmat[g].reshape(3, 3).T)
    if not pts:
        pts = [np.zeros(3)]
    P = np.asarray(pts, dtype=float)
    lo, hi = P.min(axis=0), P.max(axis=0)
    # never frame a degenerate box
    pad = np.maximum(0.05 - (hi - lo), 0) / 2
    return lo - pad, hi + pad


def _cam_axes(azimuth: float, elevation: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(forward, right, up) unit vectors of a MuJoCo free camera."""
    a, e = math.radians(azimuth), math.radians(elevation)
    fwd = np.array([math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)])
    up = np.array([-math.sin(e) * math.cos(a), -math.sin(e) * math.sin(a), math.cos(e)])
    right = np.cross(fwd, up)
    return fwd, right / np.linalg.norm(right), up


def _corners(lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    return np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])


# --------------------------------------------------------------------------- #
# MuJoCo backend (runs in a child process)
# --------------------------------------------------------------------------- #


def _decorated_model(model_path: Path, floor_z: float, extent: float, width: int, height: int):
    """The model plus a checker floor, lights and an offscreen buffer large enough."""
    import mujoco

    try:
        spec = mujoco.MjSpec.from_file(str(model_path))
        sky = spec.add_texture()
        sky.name = "_sa_sky"
        sky.type = mujoco.mjtTexture.mjTEXTURE_SKYBOX
        sky.builtin = mujoco.mjtBuiltin.mjBUILTIN_GRADIENT
        sky.rgb1 = [0.97, 0.98, 1.0]
        sky.rgb2 = [0.80, 0.83, 0.88]
        sky.width = sky.height = 256
        tex = spec.add_texture()
        tex.name = "_sa_floor_tex"
        tex.type = mujoco.mjtTexture.mjTEXTURE_2D
        tex.builtin = mujoco.mjtBuiltin.mjBUILTIN_CHECKER
        tex.mark = mujoco.mjtMark.mjMARK_EDGE
        tex.rgb1 = [0.86, 0.87, 0.89]
        tex.rgb2 = [0.78, 0.79, 0.82]
        tex.markrgb = [0.55, 0.57, 0.62]
        tex.width = tex.height = 512
        mat = spec.add_material()
        mat.name = "_sa_floor_mat"
        mat.texuniform = True
        cell = 10 ** math.floor(math.log10(max(extent, 1e-3) / 4))  # grid cell: power of ten
        mat.texrepeat = [1.0 / cell, 1.0 / cell]
        mat.reflectance = 0.0
        mat.specular = 0.1
        textures = list(mat.textures)
        textures[int(mujoco.mjtTextureRole.mjTEXROLE_RGB)] = "_sa_floor_tex"
        mat.textures = textures
        floor = spec.worldbody.add_geom()
        floor.name = "_sa_floor"
        floor.type = mujoco.mjtGeom.mjGEOM_PLANE
        floor.size = [extent * 4, extent * 4, 0.05]
        floor.pos = [0.0, 0.0, floor_z]
        floor.material = "_sa_floor_mat"
        floor.contype = floor.conaffinity = 0
        floor.group = 0
        for pos, direction, diffuse in (([1.0, -1.0, 3.0], [-0.25, 0.3, -1.0], 0.5),
                                        ([-1.5, 1.5, 2.5], [0.5, -0.5, -0.8], 0.2)):
            light = spec.worldbody.add_light()
            light.directional = True
            light.pos = [p * extent for p in pos]
            light.dir = direction
            light.diffuse = [diffuse] * 3
            light.specular = [0.15] * 3
            light.castshadow = diffuse > 0.5
        m = spec.compile()
    except Exception as e:  # noqa: BLE001 - fall back to the undecorated model
        log.warning("could not add floor/lights to the model (%s); rendering it as is", e)
        m = mujoco.MjModel.from_xml_path(str(model_path))
    m.vis.global_.offwidth = max(int(m.vis.global_.offwidth), width)
    m.vis.global_.offheight = max(int(m.vis.global_.offheight), height)
    m.vis.headlight.ambient = [0.3, 0.3, 0.3]
    m.vis.headlight.diffuse = [0.3, 0.3, 0.3]
    m.vis.headlight.specular = [0.1, 0.1, 0.1]
    m.vis.quality.shadowsize = 4096
    m.vis.map.znear = 0.001
    m.vis.map.zfar = 1000.0
    return m


def _render_mujoco_inproc(model_path: Path, out_dir: Path, width: int, height: int) -> dict[str, str]:
    import mujoco
    from PIL import Image

    m0, d0 = _load_home(model_path)
    lo, hi = _bbox(m0, d0)
    ee = [d0.site_xpos[s].copy() for s in _ee_sites(m0)]
    extent = float(np.linalg.norm(hi - lo))
    m = _decorated_model(model_path, float(lo[2]), extent, width, height)
    d = mujoco.MjData(m)
    _reset_home(m, d)
    renderer = mujoco.Renderer(m, height=height, width=width)
    opt = mujoco.MjvOption()
    aspect = width / height
    corners = _corners(lo, hi)
    margin = 1.25
    out = {}
    for view in VIEWS:
        az, el = _MJ_CAMERAS[view]
        fwd, right, up = _cam_axes(az, el)
        u, v = corners @ right, corners @ up
        cu, cv = (u.min() + u.max()) / 2, (v.min() + v.max()) / 2
        centre = (lo + hi) / 2
        centre = centre - right * (centre @ right) - up * (centre @ up) + right * cu + up * cv
        cam = mujoco.MjvCamera()
        cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        cam.lookat[:] = centre
        cam.azimuth, cam.elevation = az, el
        if view == "top":  # orthographic plan view; fovy is then the frame height in metres
            m.vis.global_.orthographic = 1
            span = max(v.max() - v.min(), (u.max() - u.min()) / aspect) * margin
            m.vis.global_.fovy = span
            cam.distance = extent * 3 + 1.0
        else:  # perspective, distance chosen so every bbox corner fits in the frustum
            m.vis.global_.orthographic = 0
            m.vis.global_.fovy = _PERSPECTIVE_FOVY
            t = math.tan(math.radians(_PERSPECTIVE_FOVY) / 2)
            rel = corners - centre
            du, dv, w = np.abs(rel @ right), np.abs(rel @ up), rel @ fwd
            # bbox corners overstate the silhouette, so a smaller margin suffices here
            dist = np.maximum(1.08 * dv / t, 1.08 * du / (t * aspect)) - w
            cam.distance = float(max(dist.max(), extent * 0.5))
            span = 2 * t * cam.distance
        renderer.update_scene(d, camera=cam, scene_option=opt)
        scn = renderer.scene
        r_mark = max(0.01, 0.02 * span)
        for p in ee:  # bright EE marker on top of the (small) site
            if scn.ngeom >= scn.maxgeom:
                break
            mujoco.mjv_initGeom(scn.geoms[scn.ngeom], mujoco.mjtGeom.mjGEOM_SPHERE, np.array([r_mark, 0, 0]),
                                np.asarray(p, dtype=float), np.eye(3).ravel(),
                                np.array([0.95, 0.1, 0.1, 1.0], dtype=np.float32))
            scn.ngeom += 1
        img = renderer.render()
        path = out_dir / f"{view}.png"
        Image.fromarray(img).save(path)
        out[view] = str(path)
    renderer.close()
    return out


def _render_mujoco(model_path: Path, out_dir: Path, width: int, height: int) -> dict[str, str]:
    """Run the MuJoCo renderer in a child process (crash/hang safe)."""
    detect_backend()
    args = json.dumps({"model": str(model_path), "out": str(out_dir), "width": width, "height": height})
    res = subprocess.run([sys.executable, "-m", "simanything.render", "--worker", args],
                         env=_child_env(_gl_cache or ""), capture_output=True, text=True,
                         timeout=_WORKER_TIMEOUT_S)
    if res.returncode != 0:
        raise RuntimeError(f"MuJoCo render worker failed (exit {res.returncode}): {res.stderr.strip()[-2000:]}")
    return json.loads(res.stdout.strip().splitlines()[-1])


# --------------------------------------------------------------------------- #
# Matplotlib backend
# --------------------------------------------------------------------------- #

_PALETTE = [(0.20, 0.50, 0.85), (0.95, 0.55, 0.15), (0.35, 0.70, 0.40), (0.60, 0.40, 0.80),
            (0.85, 0.30, 0.35), (0.25, 0.70, 0.75)]


def _sphere_pts(n: int = 160) -> np.ndarray:
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = math.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], axis=1)


_SPHERE = _sphere_pts()
_CIRCLE = np.stack([np.cos(np.linspace(0, 2 * math.pi, 49)), np.sin(np.linspace(0, 2 * math.pi, 49))], axis=1)
_BOX_EDGES = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]


def _geom_local(m, g: int) -> tuple[np.ndarray, list[np.ndarray]]:
    """Surface sample points (local frame) and feature polylines for a geom."""
    import mujoco

    t, s = int(m.geom_type[g]), m.geom_size[g]
    T = mujoco.mjtGeom
    if t == T.mjGEOM_SPHERE:
        return _SPHERE * s[0], []
    if t == T.mjGEOM_ELLIPSOID:
        return _SPHERE * s[:3], []
    if t == T.mjGEOM_CAPSULE:
        r, h = s[0], s[1]
        pts = np.vstack([_SPHERE * r + [0, 0, h], _SPHERE * r - [0, 0, h]])
        rims = [np.column_stack([_CIRCLE * r, np.full(len(_CIRCLE), z)]) for z in (-h, h)]
        return pts, rims
    if t == T.mjGEOM_CYLINDER:
        r, h = s[0], s[1]
        rims = [np.column_stack([_CIRCLE * r, np.full(len(_CIRCLE), z)]) for z in (-h, h)]
        return np.vstack(rims), rims
    if t == T.mjGEOM_BOX:
        c = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], dtype=float) * s[:3]
        return c, [np.array([c[a], c[b]]) for a, b in _BOX_EDGES]
    # mesh / sdf / anything else: its local AABB
    c = m.geom_aabb[g, :3] + np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]) \
        * m.geom_aabb[g, 3:]
    return c, [np.array([c[a], c[b]]) for a, b in _BOX_EDGES]


def _hull(P: np.ndarray) -> np.ndarray:
    """2-D convex hull (Andrew's monotone chain), counter-clockwise."""
    P = np.unique(np.round(P, 9), axis=0)
    if len(P) < 3:
        return P
    P = P[np.lexsort((P[:, 1], P[:, 0]))]

    def half(points):
        h: list[np.ndarray] = []
        for p in points:
            while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (p[1] - h[-2][1])
                                   - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0])) <= 0:
                h.pop()
            h.append(p)
        return h

    lower, upper = half(P), half(P[::-1])
    return np.array(lower[:-1] + upper[:-1])


def _render_matplotlib(model_path: Path, out_dir: Path, width: int, height: int) -> dict[str, str]:
    import matplotlib

    matplotlib.use("Agg", force=False)
    import mujoco
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.patches import Polygon, Rectangle

    m, d = _load_home(model_path)
    lo, hi = _bbox(m, d)
    floor_z = float(lo[2])
    geoms = []
    for g in _visible_geoms(m):
        local, lines = _geom_local(m, g)
        R, p = d.geom_xmat[g].reshape(3, 3), d.geom_xpos[g]
        rgba = _geom_rgba(m, g)
        if np.allclose(rgba[:3], 0.5):  # MuJoCo default grey: colour by body instead
            rgba = np.array([*_PALETTE[int(m.geom_bodyid[g]) % len(_PALETTE)], rgba[3]])
        geoms.append((p + local @ R.T, [p + ln @ R.T for ln in lines], p.copy(), rgba))
    anchors = [d.xanchor[j].copy() for j in range(m.njnt) if m.jnt_type[j] in (2, 3)]
    ee = [(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_SITE, s) or f"site{s}", d.site_xpos[s].copy())
          for s in _ee_sites(m)]
    corners = _corners(lo, hi)
    model_name = bytes(m.names).split(b"\0", 1)[0].decode(errors="replace") or model_path.stem
    scale = min(width / 640, height / 480)
    fs = max(6.0, 9.0 * scale)
    out = {}
    for view in VIEWS:
        fwd, right, up = _cam_axes(*_ORTHO_CAMERAS[view])
        proj = lambda X: np.column_stack([np.asarray(X) @ right, np.asarray(X) @ up])  # noqa: E731
        fig = Figure(figsize=(width / 100, height / 100), dpi=100, facecolor="white")
        FigureCanvasAgg(fig)
        left_m, bot_m = 0.11, 0.10
        ax = fig.add_axes((left_m, bot_m, 1 - left_m - 0.03, 1 - bot_m - 0.08))
        ax.set_facecolor("#f4f5f7")
        # limits: projected bbox + margin, stretched to the axes' pixel aspect (equal scale)
        c2 = proj(corners)
        (u0, v0), (u1, v1) = c2.min(axis=0), c2.max(axis=0)
        if view != "top":
            v0 = min(v0, floor_z)
        du, dv = (u1 - u0) * 1.15 + 1e-3, (v1 - v0) * 1.15 + 1e-3
        ax_px_w = width * (1 - left_m - 0.03)
        ax_px_h = height * (1 - bot_m - 0.08)
        if du / dv < ax_px_w / ax_px_h:
            du = dv * ax_px_w / ax_px_h
        else:
            dv = du * ax_px_h / ax_px_w
        cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
        ax.set_xlim(cu - du / 2, cu + du / 2)
        ax.set_ylim(cv - dv / 2, cv + dv / 2)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, color="#d0d3d9", linewidth=0.6, zorder=0)
        ax.set_axisbelow(True)
        if view != "top":  # ground
            ax.add_patch(Rectangle((cu - du, floor_z - dv), 2 * du, dv, facecolor="#dfe1e5", edgecolor="none",
                                   hatch="//", zorder=0.5))
            ax.axhline(floor_z, color="#7a7f88", linewidth=1.2, zorder=0.6)
        # painter's algorithm: far geoms first ("toward the viewer" = -forward)
        for pts, lines, centre, rgba in sorted(geoms, key=lambda gm: float(-(gm[2] @ fwd))):
            hull = _hull(proj(pts))
            if len(hull) < 3:
                continue
            col = np.clip(rgba[:3], 0, 1)
            ax.add_patch(Polygon(hull, closed=True, facecolor=(*col, max(0.35, float(rgba[3])) * 0.92),
                                 edgecolor=tuple(col * 0.55), linewidth=1.1 * scale, zorder=2))
            for ln in lines:
                q = proj(ln)
                ax.plot(q[:, 0], q[:, 1], color=tuple(col * 0.5), linewidth=0.6 * scale, alpha=0.6, zorder=2)
        for a in anchors:
            q = proj([a])[0]
            ax.plot(q[0], q[1], "o", markersize=4.5 * scale, markerfacecolor="white", markeredgecolor="#222",
                    markeredgewidth=1.0, zorder=5)
        for name, p in ee:
            q = proj([p])[0]
            ax.plot(q[0], q[1], marker="o", markersize=9 * scale, markerfacecolor="none",
                    markeredgecolor="#d62728", markeredgewidth=1.6, zorder=6)
            ax.plot(q[0], q[1], marker="+", markersize=13 * scale, color="#d62728", markeredgewidth=1.4, zorder=6)
            ax.annotate(name, q, xytext=(6 * scale, 6 * scale), textcoords="offset points", color="#d62728",
                        fontsize=fs, zorder=7)
        title, xl, yl = _VIEW_LABELS[view]
        ax.set_title(f"{model_name}: {title}", fontsize=fs + 1)
        ax.set_xlabel(xl, fontsize=fs)
        ax.set_ylabel(yl, fontsize=fs)
        ax.tick_params(labelsize=fs - 1)
        path = out_dir / f"{view}.png"
        fig.savefig(path, dpi=100, facecolor="white")
        out[view] = str(path)
    return out


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def render_views(model_path: str | Path, out_dir: str | Path, *, width: int = 640, height: int = 480,
                 backend: str = "auto") -> dict[str, Path | str]:
    """Write front.png, side.png and top.png of the model at its home pose.

    Returns ``{"front": Path, "side": Path, "top": Path, "backend": str}``.
    ``backend`` is ``"auto"`` (MuJoCo if it works, else matplotlib), ``"mujoco"``
    or ``"matplotlib"``. With ``"auto"`` a MuJoCo failure falls back to matplotlib.
    """
    model_path, out_dir = Path(model_path), Path(out_dir)
    if backend not in ("auto", "mujoco", "matplotlib"):
        raise ValueError(f"unknown render backend {backend!r} (auto | mujoco | matplotlib)")
    if not model_path.is_file():
        raise FileNotFoundError(model_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    chosen = detect_backend() if backend == "auto" else backend
    paths: dict[str, str] | None = None
    if chosen == "mujoco":
        try:
            paths = _render_mujoco(model_path, out_dir, width, height)
        except Exception as e:  # noqa: BLE001
            if backend == "mujoco":
                raise
            log.warning("MuJoCo rendering failed, falling back to matplotlib: %s", e)
            chosen = "matplotlib"
    if paths is None:
        paths = _render_matplotlib(model_path, out_dir, width, height)
    log.info("rendered %s views of %s with %s", ", ".join(VIEWS), model_path, chosen)
    result: dict[str, Path | str] = {v: Path(paths[v]) for v in VIEWS}
    result["backend"] = chosen
    return result


def _worker_main(argv: list[str]) -> int:
    args: dict[str, Any] = json.loads(argv[0])
    out = _render_mujoco_inproc(Path(args["model"]), Path(args["out"]), int(args["width"]), int(args["height"]))
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--worker":
        raise SystemExit(_worker_main(sys.argv[2:]))
    raise SystemExit("usage: python -m simanything.render --worker '<json args>' (internal)")
