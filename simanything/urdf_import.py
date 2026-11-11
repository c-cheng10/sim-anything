"""Official URDF -> checked MJCF (``sim-anything import-urdf``).

MuJoCo's own URDF importer keeps the kinematics, joint limits and inertials; this module only resolves
and converts the meshes, simplifies collision geometry per link and adds what the checks and
controllers expect (position servos, a ``home`` keyframe, an EE site).
"""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import numpy as np

from .spec import mat_to_quat

MUJOCO_MESH_SUFFIXES = (".stl", ".obj")  # what MuJoCo 3.3 loads; anything else is converted to .stl
BOX_PREFERENCE = 0.8  # a box replaces the capsule only when its volume is below this share of the capsule's
MIN_SIZE = 1e-4       # m; keeps flat or point-like meshes valid primitives


def _prepare_urdf(urdf: Path, mesh_dir: Path, package_root: Optional[Path]) -> str:
    """URDF text whose meshes are copied (or converted to .stl) into ``mesh_dir`` and referenced by
    file name, with the MuJoCo compiler options the import needs (visual geoms kept, meshdir)."""
    import trimesh

    root = ET.parse(urdf).getroot()
    mesh_dir.mkdir(parents=True, exist_ok=True)
    names: dict[Path, str] = {}
    for el in root.iter("mesh"):
        fn = el.get("filename", "")
        if fn.startswith("package://"):
            if package_root is None:
                raise ValueError(f"mesh '{fn}' uses package:// but no --package-root was given")
            src = package_root / fn[len("package://"):]
        else:
            src = urdf.parent / fn
        if not src.is_file():
            raise FileNotFoundError(f"mesh '{fn}' not found (looked for {src})")
        src = src.resolve()
        if src not in names:
            ext = src.suffix.lower()
            out_ext = ext if ext in MUJOCO_MESH_SUFFIXES else ".stl"
            stem, n = src.stem, 1
            while any(Path(v).stem == stem for v in names.values()):  # MuJoCo names mesh assets by file stem
                stem, n = f"{src.stem}_{n}", n + 1
            names[src] = stem + out_ext
            if out_ext == ext:
                shutil.copyfile(src, mesh_dir / names[src])
            else:
                trimesh.load(src, force="mesh").export(mesh_dir / names[src])
        el.set("filename", names[src])
    mj = root.find("mujoco")
    if mj is None:
        mj = ET.SubElement(root, "mujoco")
    comp = mj.find("compiler")
    if comp is None:
        comp = ET.SubElement(mj, "compiler")
    comp.set("meshdir", str(mesh_dir.resolve()))
    comp.set("discardvisual", "false")
    return ET.tostring(root, encoding="unicode")


def fit_primitive(verts: np.ndarray) -> dict:
    """A capsule bounding ``verts`` (n x 3, link frame), or an oriented box when that is clearly smaller,
    as MjSpec geom attributes. The capsule axis is the principal axis through the mesh's bounding-box
    centre, its radius the largest vertex distance from that axis and its total length the mesh's extent
    along it."""
    import mujoco

    c = verts.mean(axis=0)
    R = np.linalg.eigh(np.cov((verts - c).T))[1][:, ::-1]  # principal axes, largest variance first
    if np.linalg.det(R) < 0:
        R[:, 2] *= -1
    local = (verts - c) @ R
    lo, hi = local.min(axis=0), local.max(axis=0)
    mid_local = (lo + hi) / 2
    mid = c + R @ mid_local
    half = np.maximum((hi - lo) / 2, MIN_SIZE)
    r = max(float(np.max(np.linalg.norm(local[:, 1:] - mid_local[1:], axis=1))), MIN_SIZE)
    h = max(half[0] - r, MIN_SIZE)
    if 8 * np.prod(half) < BOX_PREFERENCE * (np.pi * r ** 2 * 2 * h + 4 / 3 * np.pi * r ** 3):
        return {"type": mujoco.mjtGeom.mjGEOM_BOX, "pos": mid, "quat": mat_to_quat(R), "size": half}
    a = R[:, 0] * h
    return {"type": mujoco.mjtGeom.mjGEOM_CAPSULE, "fromto": np.concatenate([mid - a, mid + a]), "size": [r, 0, 0]}


def _is_collision_mesh(geom_type, contype, conaffinity) -> bool:
    import mujoco

    return int(geom_type) == int(mujoco.mjtGeom.mjGEOM_MESH) and bool(contype or conaffinity)


def _collision_mesh(model, body: int) -> tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """Vertices (in the body frame) and faces of all colliding mesh geoms of ``body``, merged."""
    import mujoco

    verts, faces, n = [], [], 0
    for g in range(model.ngeom):
        if model.geom_bodyid[g] != body or not _is_collision_mesh(model.geom_type[g], model.geom_contype[g],
                                                                 model.geom_conaffinity[g]):
            continue
        m = model.geom_dataid[g]
        v = model.mesh_vert[model.mesh_vertadr[m]:model.mesh_vertadr[m] + model.mesh_vertnum[m]]
        R = np.zeros(9)
        mujoco.mju_quat2Mat(R, model.geom_quat[g])
        verts.append(v @ R.reshape(3, 3).T + model.geom_pos[g])
        faces.append(model.mesh_face[model.mesh_faceadr[m]:model.mesh_faceadr[m] + model.mesh_facenum[m]] + n)
        n += len(v)
    return (np.vstack(verts), np.vstack(faces)) if verts else (None, None)


def _full_precision(xml: str, model, meshdir: str) -> str:
    """``xml`` from MjSpec.to_xml (which rounds to 6 digits) with the body frames, joints, inertials and sites of
    ``model`` written exactly, so the kinematics match MuJoCo's own URDF import, and with ``meshdir``."""
    def f(v) -> str:
        return " ".join(repr(float(x)) for x in np.atleast_1d(v))

    root = ET.fromstring(xml)
    root.find("compiler").set("meshdir", meshdir)  # type: ignore[union-attr]
    for el in root.iter("body"):
        b = model.body(el.get("name"))
        el.attrib.update(pos=f(b.pos), quat=f(b.quat))
        inertial = el.find("inertial")
        if inertial is not None:
            inertial.attrib.pop("fullinertia", None)
            inertial.attrib.update(pos=f(b.ipos), quat=f(b.iquat), mass=f(b.mass), diaginertia=f(b.inertia))
    for el in root.iter("joint"):
        j = model.joint(el.get("name"))
        el.attrib.update(pos=f(j.pos), axis=f(j.axis))
    for el in root.iter("site"):
        s = model.site(el.get("name"))
        el.attrib.update(pos=f(s.pos), quat=f(s.quat))
    return ET.tostring(root, encoding="unicode")

