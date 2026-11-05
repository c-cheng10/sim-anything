"""Render + report tests on a hand-written MJCF fixture (no dependency on the builder)."""

import base64
import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from simanything import render
from simanything.render import detect_backend, render_views
from simanything.report import build_context, write_report

FIX = Path(__file__).resolve().parent / "fixtures" / "report"
MODEL = FIX / "model.xml"


def _assert_views(result, out_dir: Path, width: int, height: int) -> None:
    assert set(result) == {"front", "side", "top", "backend"}
    imgs = []
    for view in ("front", "side", "top"):
        p = Path(result[view])
        assert p == out_dir / f"{view}.png" and p.is_file()
        img = np.asarray(Image.open(p).convert("RGB")).astype(float)
        assert img.shape == (height, width, 3)
        assert img.std() > 10, f"{view}.png looks blank"
        # something other than background must cover a reasonable area
        bg = np.median(img.reshape(-1, 3), axis=0)
        assert (np.abs(img - bg).sum(axis=2) > 60).mean() > 0.02, f"{view}.png shows (almost) nothing"
        imgs.append(img)
    # the three views differ
    assert np.abs(imgs[0] - imgs[2]).mean() > 1 and np.abs(imgs[1] - imgs[2]).mean() > 1


def test_matplotlib_backend(tmp_path):
    out = tmp_path / "renders"
    res = render_views(MODEL, out, width=400, height=300, backend="matplotlib")
    assert res["backend"] == "matplotlib"
    _assert_views(res, out, 400, 300)


def test_matplotlib_backend_without_keyframe_or_sites(tmp_path):
    xml = """<mujoco><worldbody><body pos="0 0 0.2"><joint type="hinge" axis="0 1 0"/>
      <geom type="capsule" fromto="0 0 0 0.3 0 0" size="0.03"/>
      <geom type="ellipsoid" size="0.05 0.03 0.02" pos="0.3 0 0"/></body></worldbody></mujoco>"""
    model = tmp_path / "m.xml"
    model.write_text(xml)
    res = render_views(model, tmp_path / "r", width=320, height=240, backend="matplotlib")
    _assert_views(res, tmp_path / "r", 320, 240)


def test_mujoco_backend(tmp_path):
    if detect_backend() != "mujoco":
        pytest.skip("no offscreen MuJoCo GL renderer available")
    out = tmp_path / "renders"
    res = render_views(MODEL, out, width=480, height=360, backend="mujoco")
    assert res["backend"] == "mujoco"
    _assert_views(res, out, 480, 360)


def test_auto_backend_matches_detection(tmp_path):
    res = render_views(MODEL, tmp_path, width=200, height=150)
    assert res["backend"] == detect_backend()
    _assert_views(res, tmp_path, 200, 150)


def test_detect_backend_is_cached_and_valid():
    assert detect_backend() in ("mujoco", "matplotlib")
    assert detect_backend() is render._backend_cache


def test_broken_gl_falls_back_to_matplotlib(tmp_path, monkeypatch):
    """A GL platform that cannot work must be detected in the subprocess probe, not crash us."""
    monkeypatch.setattr(render, "_backend_cache", None)
    monkeypatch.setattr(render, "_gl_cache", None)
    monkeypatch.setattr(render, "_gl_candidates", lambda: ["no_such_gl"])
    assert detect_backend() == "matplotlib"
    res = render_views(MODEL, tmp_path, width=160, height=120)
    assert res["backend"] == "matplotlib"
    _assert_views(res, tmp_path, 160, 120)


def test_bad_backend_name(tmp_path):
    with pytest.raises(ValueError):
        render_views(MODEL, tmp_path, backend="povray")


@pytest.fixture
def run_dir(tmp_path):
    d = tmp_path / "run"
    d.mkdir()
    for name in ("spec.yaml", "model.xml", "check.json", "history.json"):
        shutil.copy(FIX / name, d / name)
    return d


def _prerender(run_dir: Path) -> None:
    render_views(run_dir / "model.xml", run_dir / "renders", width=160, height=120, backend="matplotlib")


def test_report_full(run_dir):
    shutil.copy(FIX / "eval.json", run_dir / "eval.json")
    _prerender(run_dir)
    html_path, md_path = write_report(run_dir)
    assert html_path == run_dir / "report.html" and md_path == run_dir / "report.md"
    html, md = html_path.read_text(), md_path.read_text()

    # self-contained: embedded images, no external assets
    assert html.count("data:image/png;base64,") == 3
    b64 = html.split("data:image/png;base64,", 1)[1].split('"', 1)[0]
    assert base64.b64decode(b64)[:8] == b"\x89PNG\r\n\x1a\n"
    assert "<link" not in html and "<script" not in html and "src=\"http" not in html
    assert "prefers-color-scheme: dark" in html

    for text in (html, md):
        assert "fixture_arm" in text and "Example Robotics (fictional)" in text
        for cid in ("compiles", "joint_limits", "reach", "total_mass"):
            assert cid in text
        assert "https://example.com/fa3/datasheet.pdf#page=3" in text
        assert "joints[*].effort_limit" in text  # estimates
        assert "added origin for j3" in text  # history
        assert "84.7" in text  # eval score
        assert "reference includes a gripper" in text
        assert "6.4 kg" in text and "0.6 m" in text and "1 kg" in text  # mass, reach, payload
    assert 'class="badge failed"' in html
    # URLs with query strings stay intact (escaped in HTML)
    assert 'href="https://example.com/fa3/manual.html?section=limits&amp;lang=en"' in html
    assert "<https://example.com/fa3/manual.html?section=limits&lang=en>" in md
    # markdown: relative image links, pipe in a fix hint escaped
    for view in ("front", "side", "top"):
        assert f"](renders/{view}.png)" in md
    assert "joints[0].limits \\| units" in md
    assert "base64" not in md


def test_report_renders_missing_images(run_dir):
    assert not (run_dir / "renders").exists()
    html_path, md_path = write_report(run_dir)
    for view in ("front", "side", "top"):
        assert (run_dir / "renders" / f"{view}.png").is_file()
    assert html_path.read_text().count("data:image/png;base64,") == 3


def test_report_tolerates_missing_optional_files(run_dir):
    (run_dir / "history.json").unlink()
    _prerender(run_dir)
    html_path, md_path = write_report(run_dir)
    html, md = html_path.read_text(), md_path.read_text()
    assert "No iteration history" in html and "No iteration history" in md
    assert "Evaluation against reference" not in html


def test_report_minimal_run_dir(tmp_path):
    """Only a spec: no model, no check, no history, no eval."""
    shutil.copy(FIX / "spec.yaml", tmp_path / "spec.yaml")
    html_path, md_path = write_report(tmp_path)
    html = html_path.read_text()
    assert "fixture_arm" in html and 'class="badge unknown"' in html
    assert "No renders available" in html and "No check report" in html
    assert md_path.is_file()


def test_report_passed_badge_and_bad_json(run_dir):
    _prerender(run_dir)
    import json

    rep = json.loads((run_dir / "check.json").read_text())
    rep.update(passed=True, n_errors=0)
    (run_dir / "check.json").write_text(json.dumps(rep))
    (run_dir / "eval.json").write_text("{not json")
    ctx = build_context(run_dir)
    assert ctx["status"] == "passed" and ctx["evaluation"] is None
    assert any("eval.json" in n for n in ctx["notes"])
    html_path, _ = write_report(run_dir)
    assert 'class="badge passed"' in html_path.read_text()
