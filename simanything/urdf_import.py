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

MUJOCO_MESH_SUFFIXES = (".stl", ".obj")  # what MuJoCo 3.3 loads; anything else is converted to .stl


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
