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
COLLISION_MODES = ("primitives", "hull", "coacd")
COACD_MAX_PIECES = 8  # "a few" convex pieces per link
EE_SITE = "ee_site"


def _prepare_urdf(urdf: Path, mesh_dir: Path, package_root: Optional[Path]) -> str:
    """URDF text whose meshes are copied (or converted to .stl) into ``mesh_dir`` and referenced by
    file name, with the MuJoCo compiler options the import needs (visual geoms kept, meshdir)."""
    import trimesh

    root = ET.parse(urdf).getroot()
    mimic = [j.get("name") for j in root.iter("joint") if j.find("mimic") is not None]
    if mimic:  # MuJoCo's importer drops <mimic>: the joint would move on its own
        raise ValueError(f"mimic joint(s) {', '.join(mimic)} are not supported (e.g. coupled gripper fingers); "
                         "remove them or the links they drive from the URDF")
    mesh_dir.mkdir(parents=True, exist_ok=True)
    names: dict[Path, str] = {}
    for el in root.iter("mesh"):
        fn = el.get("filename", "").removeprefix("file://")  # xacro output often uses file:///abs/path
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
                mesh = trimesh.load(src, force="mesh")
                if mesh.units:  # e.g. a .dae in millimetres: trimesh records the unit but keeps the numbers
                    mesh.convert_units("meters")
                mesh.export(mesh_dir / names[src])
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


def _convex_pieces(verts: np.ndarray, faces: np.ndarray, mesh_dir: Path, name: str) -> list[str]:
    """Convex decomposition of a link mesh with coacd, written as ``<name>_cvx<k>.stl`` in ``mesh_dir``."""
    import coacd
    import trimesh

    coacd.set_log_level("error")
    files = []
    for k, (v, f) in enumerate(coacd.run_coacd(coacd.Mesh(verts, faces), max_convex_hull=COACD_MAX_PIECES)):
        files.append(f"{name}_cvx{k}.stl")
        trimesh.Trimesh(v, f).export(mesh_dir / files[-1])
    return files


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


def import_urdf(urdf: str | Path, out: str | Path, collision: str = "hull", ee_link: Optional[str] = None,
                package_root: str | Path | None = None) -> Path:
    """Import ``urdf`` with MuJoCo's URDF importer and write a checked MJCF to ``out`` (meshes go to
    ``<out stem>_meshes/`` next to it). ``collision``: "primitives" (one capsule or box per link), "hull"
    (MuJoCo's convex hull of each collision mesh) or "coacd" (a few convex pieces per link). The EE site
    goes at ``ee_link``'s origin (default: the last link)."""
    import mujoco

    from .builder import servo_gains
    from .check.context import HINGE, SLIDE

    if collision not in COLLISION_MODES:
        raise ValueError(f"unknown collision mode '{collision}'; use one of {', '.join(COLLISION_MODES)}")
    urdf, out = Path(urdf), Path(out)
    mesh_dir = out.parent / f"{out.stem}_meshes"
    spec = mujoco.MjSpec.from_string(_prepare_urdf(urdf, mesh_dir, None if package_root is None else Path(package_root)))
    links = [b.name for b in spec.bodies[1:]]
    ee = ee_link or links[-1]  # shortcut: the last link in tree order; branched trees need --ee-link
    if ee not in links:
        raise ValueError(f"EE link '{ee}' is not a link of {urdf.name}; links: {', '.join(links)}")
    spec.body(ee).add_site(name=EE_SITE)
    spec.compiler.fusestatic = True  # links on fixed joints merge into their parent; the EE site moves with them
    model = spec.compile()
    # after fusing, the MjSpec's own state is stale (MuJoCo 3.3): continue from the fused MJCF
    spec = mujoco.MjSpec.from_string(_full_precision(spec.to_xml(), model, str(mesh_dir.resolve())))
    model = spec.compile()
    bad = [model.joint(j).name for j in range(model.njnt) if model.jnt_type[j] not in (HINGE, SLIDE)]
    if bad:
        raise ValueError(f"unsupported joint(s) {', '.join(bad)}: only revolute, continuous and prismatic joints "
                         "of a fixed-base arm are supported")

    if collision != "hull":
        for b in range(model.nbody):
            verts, faces = _collision_mesh(model, b)
            if verts is None:
                continue
            sb = spec.body(model.body(b).name)
            for g in sb.geoms:
                if _is_collision_mesh(g.type, g.contype, g.conaffinity):
                    g.delete()
            if collision == "primitives":
                sb.add_geom(**fit_primitive(verts))
                continue
            for fn in _convex_pieces(verts, faces, mesh_dir, sb.name):
                spec.add_mesh(name=Path(fn).stem, file=fn)
                sb.add_geom(type=mujoco.mjtGeom.mjGEOM_MESH, meshname=Path(fn).stem)

    # One position servo per joint with the builder's gains, holding home = zero clipped into the limits
    home = [float(np.clip(0.0, *model.jnt_range[j])) if model.jnt_limited[j] else 0.0 for j in range(model.njnt)]
    efforts = [float(model.jnt_actfrcrange[j, 1]) if model.jnt_actfrclimited[j] and model.jnt_actfrcrange[j, 1] > 0
               else None for j in range(model.njnt)]
    armature = [float(a) for a in model.dof_armature]
    kp, kv = servo_gains(model, home, ["hinge" if t == HINGE else "slide" for t in model.jnt_type], efforts, armature)
    for j in range(model.njnt):
        name = model.joint(j).name
        spec.joint(name).armature = armature[j]
        act = spec.add_actuator(name=f"{name}_act", target=name, trntype=mujoco.mjtTrn.mjTRN_JOINT,
                                biastype=mujoco.mjtBias.mjBIAS_AFFINE)
        act.gainprm[0], act.biasprm[1], act.biasprm[2] = kp[j], -kp[j], -kv[j]  # what <position kp kv> sets
        if model.jnt_limited[j]:
            act.ctrlrange = model.jnt_range[j]
        if efforts[j] is not None:
            act.forcerange = [-efforts[j], efforts[j]]
    spec.add_key(name="home", qpos=home, ctrl=home)
    # MuJoCo filters parent/child contacts except when the parent is welded to the world (the fused base)
    for b in range(1, model.nbody):
        p = model.body_parentid[b]
        if model.body_weldid[p] == 0 and model.body_jntnum[b]:
            spec.add_exclude(bodyname1=model.body(p).name, bodyname2=model.body(b).name)
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST

    model = spec.compile()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_full_precision(spec.to_xml(), model, mesh_dir.name), encoding="utf-8")
    return out
