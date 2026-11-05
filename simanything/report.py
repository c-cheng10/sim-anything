"""HTML + Markdown report for a loop run directory (docs/CONTRACTS.md section 3).

``write_report(run_dir)`` reads ``spec.yaml``, ``check.json``, ``history.json``,
``renders/*.png`` (rendered first if missing and ``model.xml`` exists) and an
optional ``eval.json``, and writes a self-contained ``report.html`` (images
base64-embedded, inline CSS, no external assets) and ``report.md`` (images
linked relative to the run dir). Every input is optional; missing or
unreadable files are noted in the report instead of raising.
"""

from __future__ import annotations

import base64
import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .schemas import CheckReport, EvalResult, History

log = logging.getLogger(__name__)

TEMPLATES = Path(__file__).resolve().parent / "templates"
VIEWS = ("front", "side", "top")


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #


def fmt(v: Any, digits: int = 4) -> str:
    """Compact human formatting for measured/expected/tolerance values."""
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return str(v)
        if v == 0:
            return "0"
        if 1e-3 <= abs(v) < 1e5:
            return f"{v:.{digits}g}"
        return f"{v:.3e}"
    if isinstance(v, (list, tuple)):
        if len(v) > 8:
            return "[" + ", ".join(fmt(x, digits) for x in v[:8]) + f", … ({len(v)} items)]"
        return "[" + ", ".join(fmt(x, digits) for x in v) + "]"
    if isinstance(v, dict):
        return ", ".join(f"{k}: {fmt(x, digits)}" for k, x in v.items())
    return str(v)


def _md_cell(v: Any) -> str:
    s = v if isinstance(v, str) else fmt(v)
    return s.replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", "<br>")


def _is_url(s: Any) -> bool:
    return isinstance(s, str) and s.strip().lower().startswith(("http://", "https://"))


# --------------------------------------------------------------------------- #
# Loading (all tolerant)
# --------------------------------------------------------------------------- #


def _read_json(path: Path, notes: list[str]) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        notes.append(f"{path.name} could not be read: {e}")
        return None


def _load_spec(run_dir: Path, notes: list[str]) -> dict[str, Any] | None:
    path = run_dir / "spec.yaml"
    if not path.is_file():
        notes.append("spec.yaml not found in the run directory.")
        return None
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        notes.append(f"spec.yaml could not be parsed: {e}")
        return None
    if not isinstance(raw, dict):
        notes.append("spec.yaml is not a YAML mapping.")
        return None
    try:
        from .spec import Spec

        Spec.model_validate(raw)
    except Exception as e:  # noqa: BLE001
        first = str(e).strip().splitlines()
        notes.append("spec.yaml does not validate against the schema"
                     + (f": {' '.join(first[:3])}" if first else "."))
    return raw


def _spec_summary(raw: dict[str, Any]) -> dict[str, Any]:
    units = raw.get("units") or {}
    L = units.get("length", "m")
    A = units.get("angle", "deg")
    joints = [j for j in (raw.get("joints") or []) if isinstance(j, dict)]
    reach = raw.get("reach") if isinstance(raw.get("reach"), dict) else None
    key: list[tuple[str, str]] = [("DOF", fmt(raw.get("dof", len(joints) or None)))]
    key.append(("Total mass", f"{fmt(raw['total_mass'])} kg" if raw.get("total_mass") is not None else "—"))
    if reach and reach.get("value") is not None:
        key.append(("Reach", f"{fmt(reach['value'])} {L} ({reach.get('measured_from', 'shoulder')} → "
                             f"{reach.get('measured_to', 'ee_site')})"))
    else:
        key.append(("Reach", "—"))
    key.append(("Payload", f"{fmt(raw['payload'])} kg" if raw.get("payload") is not None else "—"))
    if raw.get("repeatability") is not None:
        key.append(("Repeatability", f"± {fmt(raw['repeatability'])} {L}"))
    key.append(("Convention", str(raw.get("convention", "offset"))))
    key.append(("Units", f"length {L}, angle {A}"))

    jrows = []
    for j in joints:
        jtype = j.get("type", "hinge")
        unit = A if jtype == "hinge" else L
        lim = j.get("limits") if isinstance(j.get("limits"), dict) else None
        vel = j.get("velocity_limit")
        jrows.append({
            "name": j.get("name", "?"), "type": jtype,
            "lower": f"{fmt(lim.get('lower'))} {unit}" if lim else "—",
            "upper": f"{fmt(lim.get('upper'))} {unit}" if lim else "—",
            "effort": f"{fmt(j['effort_limit'])} {'N·m' if jtype == 'hinge' else 'N'}"
            if j.get("effort_limit") is not None else "—",
            "velocity": f"{fmt(vel)} {unit}/s" if vel is not None else "—",
            "home": f"{fmt(j.get('home', 0.0))} {unit}",
        })
    sources = raw.get("sources") if isinstance(raw.get("sources"), dict) else {}
    estimates = raw.get("estimates") if isinstance(raw.get("estimates"), list) else []
    return {
        "name": raw.get("name"), "manufacturer": raw.get("manufacturer"), "model": raw.get("model"),
        "description": raw.get("description"), "notes": raw.get("notes"),
        "key_numbers": key, "joints": jrows,
        "sources": [{"path": str(k), "url": str(v), "is_url": _is_url(v)} for k, v in sources.items()],
        "estimates": [str(e) for e in estimates],
    }


def _check_rows(check: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for c in check.get("checks", []):
        if not isinstance(c, dict):
            continue
        passed = bool(c.get("pass", c.get("passed", False)))
        rows.append({
            "id": str(c.get("id", "?")), "passed": passed, "severity": str(c.get("severity", "error")),
            "measured": fmt(c.get("measured")), "expected": fmt(c.get("expected")),
            "tolerance": fmt(c.get("tolerance")), "message": str(c.get("message") or ""),
            "fix_hint": str(c.get("fix_hint") or ""),
            "status": "pass" if passed else ("fail" if c.get("severity", "error") == "error" else "warn"),
        })
    return rows


def _convention(c: dict[str, Any]) -> str:
    s = "+q" if (c.get("sign", 1) or 1) > 0 else "-q"
    off = c.get("offset") or 0.0
    return s if not off else f"{s} {float(off):+.3f}"


def _eval_summary(ev: dict[str, Any]) -> dict[str, Any]:
    def stats(key: str) -> str:
        s = ev.get(key)
        if not isinstance(s, dict):
            return "—"
        return f"mean {fmt(s.get('mean'), 3)}, p95 {fmt(s.get('p95'), 3)}, max {fmt(s.get('max'), 3)}"

    rows = [
        ("Score", f"{fmt(ev.get('score'), 3)} / 100"),
        ("Robot", fmt(ev.get("robot"))),
        ("Samples", f"{fmt(ev.get('n_samples'))} (seed {fmt(ev.get('seed'))})"),
        ("DOF (candidate / reference)", f"{fmt(ev.get('dof_candidate'))} / {fmt(ev.get('dof_reference'))}"
                                        f" — {'match' if ev.get('dof_match') else 'MISMATCH'}"),
        ("EE position error [mm]", stats("ee_position_error_mm")),
        ("EE orientation error, aligned [deg]", stats("ee_orientation_error_aligned_deg")),
        ("EE orientation error, raw [deg]", stats("ee_orientation_error_deg")),
        ("Joint limit MAE [deg]", fmt(ev.get("joint_limit_mae_deg"), 3)),
        ("Mass candidate / reference [kg]", f"{fmt(ev.get('mass_candidate'))} / {fmt(ev.get('mass_reference'))}"
                                            f" ({fmt(ev.get('mass_rel_diff'), 3)} rel.)"),
        ("Conventions (q_ref =)", ("fitted" if ev.get("conventions_fitted") else "given") + ": "
         + ", ".join(_convention(c) for c in ev.get("conventions", []) if isinstance(c, dict))),
    ]
    breakdown = ev.get("score_breakdown") if isinstance(ev.get("score_breakdown"), dict) else {}
    if breakdown:
        rows.insert(1, ("Score breakdown", ", ".join(f"{k} {fmt(v, 3)}" for k, v in breakdown.items())))
    return {"rows": rows, "notes": [str(n) for n in ev.get("notes", []) or []],
            "candidate": ev.get("candidate"), "reference": ev.get("reference")}


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(("html", "html.j2")),
                      trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
    env.filters["mdcell"] = _md_cell
    env.filters["fmt"] = fmt
    return env


def _ensure_renders(run_dir: Path, notes: list[str]) -> str | None:
    rdir = run_dir / "renders"
    if all((rdir / f"{v}.png").is_file() for v in VIEWS):
        return None
    model = run_dir / "model.xml"
    if not model.is_file():
        notes.append("No renders: renders/*.png and model.xml are both missing.")
        return None
    try:
        from .render import render_views

        return str(render_views(model, rdir)["backend"])
    except Exception as e:  # noqa: BLE001 - the report must still be written
        log.warning("rendering %s failed: %s", model, e)
        notes.append(f"Rendering model.xml failed: {e}")
        return None


def build_context(run_dir: str | Path) -> dict[str, Any]:
    """Everything the templates need (also handy for tests and other front ends)."""
    run_dir = Path(run_dir)
    notes: list[str] = []
    raw_spec = _load_spec(run_dir, notes)
    spec = _spec_summary(raw_spec) if raw_spec else None

    check_raw = _read_json(run_dir / "check.json", notes)
    check = None
    if isinstance(check_raw, dict):
        try:
            CheckReport.model_validate(check_raw)
        except Exception as e:  # noqa: BLE001
            notes.append(f"check.json does not match the CheckReport schema: {str(e).splitlines()[0]}")
        rows = _check_rows(check_raw)
        n_err = check_raw.get("n_errors", sum(r["status"] == "fail" for r in rows))
        check = {"passed": bool(check_raw.get("passed", n_err == 0)), "rows": rows,
                 "n_checks": check_raw.get("n_checks", len(rows)),
                 "n_failed": check_raw.get("n_failed", sum(not r["passed"] for r in rows)), "n_errors": n_err,
                 "mujoco_version": check_raw.get("mujoco_version")}
    elif check_raw is None and not (run_dir / "check.json").exists():
        notes.append("check.json not found: no verification results.")

    hist_raw = _read_json(run_dir / "history.json", notes)
    history = None
    if isinstance(hist_raw, dict):
        try:
            history = History.model_validate(hist_raw).model_dump(mode="json")
        except Exception as e:  # noqa: BLE001
            notes.append(f"history.json does not match the History schema: {str(e).splitlines()[0]}")

    ev_raw = _read_json(run_dir / "eval.json", notes)
    evaluation = None
    if isinstance(ev_raw, dict):
        try:
            EvalResult.model_validate(ev_raw)
        except Exception as e:  # noqa: BLE001
            notes.append(f"eval.json does not fully match the EvalResult schema: {str(e).splitlines()[0]}")
        evaluation = _eval_summary(ev_raw)

    backend = _ensure_renders(run_dir, notes)
    images = []
    for v in VIEWS:
        p = run_dir / "renders" / f"{v}.png"
        if p.is_file():
            images.append({"view": v, "rel": f"renders/{v}.png",
                           "b64": base64.b64encode(p.read_bytes()).decode("ascii")})

    if check is not None:
        status = "passed" if check["passed"] else "failed"
    elif history is not None:
        status = {"passed": "passed", "max_iter_reached": "failed"}.get(history["status"], "unknown")
    else:
        status = "unknown"
    name = (spec or {}).get("name") or (history or {}).get("robot") or run_dir.resolve().name
    return {
        "name": name, "spec": spec, "check": check, "history": history, "evaluation": evaluation,
        "images": images, "render_backend": backend, "status": status, "notes": notes,
        "run_dir": str(run_dir), "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def write_report(run_dir: str | Path) -> tuple[Path, Path]:
    """Write ``run_dir/report.html`` and ``run_dir/report.md``; return their paths."""
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise NotADirectoryError(run_dir)
    ctx = build_context(run_dir)
    env = _env()
    html_path, md_path = run_dir / "report.html", run_dir / "report.md"
    html_path.write_text(env.get_template("report.html.j2").render(**ctx), encoding="utf-8")
    md_path.write_text(env.get_template("report.md.j2").render(**ctx), encoding="utf-8")
    log.info("wrote %s and %s", html_path, md_path)
    return html_path, md_path


__all__ = ["write_report", "build_context", "fmt"]
