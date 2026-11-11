from pathlib import Path

import pytest

trimesh = pytest.importorskip("trimesh")

from simanything.urdf_import import _prepare_urdf  # noqa: E402

_INERTIA = '<inertia ixx="{i}" iyy="{i}" izz="{iz}" ixy="0" ixz="0" iyz="0"/>'


def _link(name, mass, i, iz, mesh, z, visual=None):
    vis = visual or mesh
    return (f'<link name="{name}"><inertial><origin xyz="0 0 {z}"/><mass value="{mass}"/>{_INERTIA.format(i=i, iz=iz)}'
            f'</inertial><visual><origin xyz="0 0 {z}"/><geometry><mesh filename="{vis}"/></geometry></visual>'
            f'<collision><origin xyz="0 0 {z}"/><geometry><mesh filename="{mesh}"/></geometry></collision></link>')


def _joint(name, parent, child, z, axis):
    return (f'<joint name="{name}" type="revolute"><parent link="{parent}"/><child link="{child}"/>'
            f'<origin xyz="0 0 {z}" rpy="0 0 0.3"/><axis xyz="{axis}"/>'
            f'<limit lower="-2" upper="2" effort="50" velocity="1"/></joint>')


@pytest.fixture
def arm(tmp_path) -> Path:
    """A 3-link arm in a ROS-like package: package:// and relative mesh paths, one .ply (MuJoCo can't load)."""
    pkg = tmp_path / "pkgs" / "arm_description"
    (pkg / "meshes").mkdir(parents=True)
    (pkg / "urdf").mkdir()
    trimesh.creation.cylinder(0.06, 0.1).export(pkg / "meshes" / "base.stl")
    trimesh.creation.box([0.12, 0.12, 0.1]).export(pkg / "meshes" / "base_visual.ply")
    trimesh.creation.cylinder(0.04, 0.2).export(pkg / "meshes" / "link1.stl")
    trimesh.creation.cylinder(0.035, 0.25).export(pkg / "meshes" / "link2.obj")
    trimesh.creation.box([0.06, 0.04, 0.15]).export(pkg / "meshes" / "link3.stl")
    m = "package://arm_description/meshes/"
    urdf = pkg / "urdf" / "arm.urdf"
    urdf.write_text(
        '<robot name="arm">'
        + _link("base", 2.0, 0.006, 0.0036, m + "base.stl", 0.05, visual=m + "base_visual.ply")
        + _link("link1", 1.5, 0.006, 0.0012, m + "link1.stl", 0.1)
        + _link("link2", 1.0, 0.006, 0.0006, "../meshes/link2.obj", 0.125)
        + _link("link3", 0.5, 0.001, 0.0002, m + "link3.stl", 0.075)
        + '<link name="tool"/>'
        + _joint("j1", "base", "link1", 0.1, "0 0 1") + _joint("j2", "link1", "link2", 0.2, "0 1 0")
        + _joint("j3", "link2", "link3", 0.25, "0 1 0")
        + '<joint name="tool_fixed" type="fixed"><parent link="link3"/><child link="tool"/>'
          '<origin xyz="0 0 0.15"/></joint>'
        + "</robot>")
    return urdf


def test_prepare_resolves_package_and_relative_paths_and_converts(arm, tmp_path):
    mesh_dir = tmp_path / "out" / "m"
    text = _prepare_urdf(arm, mesh_dir, tmp_path / "pkgs")
    assert sorted(p.name for p in mesh_dir.iterdir()) == ["base.stl", "base_visual.stl", "link1.stl", "link2.obj",
                                                          "link3.stl"]
    assert "package://" not in text and 'discardvisual="false"' in text
    with pytest.raises(ValueError, match="package-root"):
        _prepare_urdf(arm, mesh_dir, None)
