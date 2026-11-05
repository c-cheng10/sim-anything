"""One build+check iteration of the agent loop (docs/CONTRACTS.md section 3).

``loop_step`` is deliberately a single step: the agent reads the fix hints,
edits ``spec.yaml`` and calls it again. State lives in the run directory::

    run_dir/
      spec.yaml model.xml check.json history.json
      iterations/iter_NN/{spec.yaml, model.xml, check.json}
      renders/{front,side,top}.png  report.html  report.md   (rewritten every iteration)

The renders and the report are rewritten after every new iteration, so they
always describe the same iteration as ``check.json`` (a build failure removes
the renders, since there is no model to draw).

Exit codes: 0 passed, 1 checks failed (edit the spec and loop again), 2 max
iterations reached without passing.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field

from .schemas import CheckReport, CheckResult, History, IterationRecord

Status = Literal["running", "passed", "max_iter_reached"]

_EXIT = {"passed": 0, "running": 1, "max_iter_reached": 2}


class FixHint(BaseModel):
    id: str
    fix_hint: str


class LoopOutcome(BaseModel):
    iteration: int  # number of the latest iteration (0 if none ran)
    status: Status
    passed: bool
    exit_code: int  # 0 passed, 1 fix needed, 2 max iterations reached
    n_errors: int
    failed_ids: list[str]  # failed error-severity checks
    run_dir: str
    summary: str
    fix_hints: list[FixHint] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _iter_dir(run_dir: Path, n: int) -> Path:
    return run_dir / "iterations" / f"iter_{n:02d}"


def _load_history(run_dir: Path) -> Optional[History]:
    p = run_dir / "history.json"
    if not p.exists():
        return None
    return History.model_validate_json(p.read_text(encoding="utf-8"))


def _save_history(run_dir: Path, history: History) -> None:
    (run_dir / "history.json").write_text(
        json.dumps(history.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")


def _write_report_json(path: Path, report: CheckReport) -> None:
    path.write_text(json.dumps(report.to_json_dict(), indent=2) + "\n", encoding="utf-8")


def _robot_name(spec_text: str) -> Optional[str]:
    try:
        data = yaml.safe_load(spec_text)
    except yaml.YAMLError:
        return None
    if isinstance(data, dict) and isinstance(data.get("name"), str):
        return data["name"]
    return None


def _copy(src: Path, dst: Path) -> None:
    if dst.exists() and src.resolve() == dst.resolve():
        return
    shutil.copyfile(src, dst)


def _failed_report(model: Path, spec: Path, message: str, fix_hint: str) -> CheckReport:
    check = CheckResult(id="compiles", passed=False, severity="error", message=message, fix_hint=fix_hint)
    return CheckReport.from_checks(str(model), str(spec), [check])


def _blocking(report: CheckReport) -> list[CheckResult]:
    return [c for c in report.checks if not c.passed and c.severity == "error"]


def _warnings(report: CheckReport) -> list[CheckResult]:
    return [c for c in report.checks if not c.passed and c.severity != "error"]


def _finalize(run_dir: Path) -> list[str]:
    """Render the latest model and write the report. Returns summary lines.

    Old renders are removed first so that neither a build failure (no model)
    nor a render failure leaves images of an earlier iteration behind.
    """
    lines: list[str] = []
    model = run_dir / "model.xml"
    renders = run_dir / "renders"
    if renders.is_dir():
        shutil.rmtree(renders)
    if model.exists():
        try:
            from .render import render_views

            res = render_views(model, run_dir / "renders")
            views = [k for k in ("front", "side", "top") if k in res]
            lines.append(f"renders: {run_dir / 'renders'} ({', '.join(views)}; backend {res.get('backend', '?')})")
        except Exception as e:  # noqa: BLE001 - a render failure must not lose the iteration
            lines.append(f"render failed: {type(e).__name__}: {e}")
    else:
        lines.append("renders: skipped (no model was built)")
    try:
        from .report import write_report

        html, md = write_report(run_dir)
        lines.append(f"report: {html} (also {md})")
    except Exception as e:  # noqa: BLE001
        lines.append(f"report failed: {type(e).__name__}: {e}")
    return lines


def _outcome(history: History, report: Optional[CheckReport], run_dir: Path,
             head: str, extra: list[str]) -> LoopOutcome:
    status: Status = history.status
    n = len(history.iterations)
    blocking = _blocking(report) if report is not None else []
    hints = [FixHint(id=c.id, fix_hint=c.fix_hint or c.message or "(no hint)") for c in blocking]
    lines = [head]
    for c in blocking:
        lines.append(f"- {c.id}: {c.message}".rstrip())
        if c.fix_hint:
            lines.append(f"  fix: {c.fix_hint}")
    warns = _warnings(report) if report is not None else []
    if warns:
        lines.append("warnings (non-blocking):")
        lines.extend(f"- {c.id}: {c.message}".rstrip() for c in warns)
    lines.extend(extra)
    if report is not None:
        lines.append(f"check report: {run_dir / 'check.json'}")
    if status == "running":
        lines.append("next: edit spec.yaml per the fix hints, then run `sim-anything loop` again with --note.")
    elif status == "max_iter_reached" and not (report is not None and report.passed):
        lines.append("next: stop; report the remaining failures (max iterations reached).")
    return LoopOutcome(
        iteration=n,
        status=status,
        passed=status == "passed",
        exit_code=_EXIT[status],
        n_errors=report.n_errors if report is not None else 0,
        failed_ids=[c.id for c in blocking],
        run_dir=str(run_dir),
        summary="\n".join(lines),
        fix_hints=hints,
    )


def _head(n: int, max_iter: int, report: CheckReport, status: Status) -> str:
    if report.passed:
        nw = len(_warnings(report))
        return (f"iteration {n}/{max_iter}: PASSED ({report.n_checks} checks, 0 errors"
                + (f", {nw} warning(s))" if nw else ")"))
    tail = " -- max iterations reached" if status == "max_iter_reached" else ""
    return f"iteration {n}/{max_iter}: FAILED ({report.n_errors} error(s) of {report.n_checks} checks){tail}"


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #


def loop_step(spec_path: str | Path, run_dir: str | Path, *, max_iter: int = 8,
              note: Optional[str] = None) -> LoopOutcome:
    """Run one build+check iteration for ``spec_path`` recorded in ``run_dir``.

    No new iteration starts when the spec is byte-identical to the one used by
    the latest iteration (the result would be the same), or when ``max_iter``
    iterations have already run; the latest result is returned instead.
    """
    spec_path = Path(spec_path)
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    spec_bytes = spec_path.read_bytes()
    spec_text = spec_bytes.decode("utf-8", errors="replace")

    history = _load_history(run_dir)
    if history is None:
        history = History(robot=_robot_name(spec_text), spec=str(spec_path), max_iter=max_iter)
    history.max_iter = max_iter
    history.spec = str(spec_path)

    n_done = len(history.iterations)
    latest_report: Optional[CheckReport] = None
    if n_done and (run_dir / "check.json").exists():
        latest_report = CheckReport.model_validate_json((run_dir / "check.json").read_text(encoding="utf-8"))

    # --- no new iteration: spec unchanged since the latest iteration -------- #
    last_spec = _iter_dir(run_dir, n_done) / "spec.yaml" if n_done else None
    if last_spec is not None and last_spec.exists() and last_spec.read_bytes() == spec_bytes:
        head = (f"spec unchanged since iteration {n_done}; no new iteration "
                f"(status: {history.status}).")
        if latest_report is not None:
            head += "\n" + _head(n_done, max_iter, latest_report, history.status)
        _save_history(run_dir, history)
        return _outcome(history, latest_report, run_dir, head, [])

    # --- no new iteration: cap reached -------------------------------------- #
    if n_done >= max_iter:
        extra: list[str] = []
        if history.status != "max_iter_reached" and not (latest_report and latest_report.passed):
            history.status = "max_iter_reached"
            _save_history(run_dir, history)
            extra = _finalize(run_dir)
        else:
            _save_history(run_dir, history)
        head = (f"max iterations ({max_iter}) already used; the changed spec was NOT built or checked "
                f"(raise --max-iter to continue).")
        if latest_report is not None:
            head += "\nlatest checked " + _head(n_done, max_iter, latest_report, history.status)
        return _outcome(history, latest_report, run_dir, head, extra)

    # --- new iteration ------------------------------------------------------ #
    n = n_done + 1
    it_dir = _iter_dir(run_dir, n)
    if it_dir.exists():
        shutil.rmtree(it_dir)  # leftovers of an interrupted run
    it_dir.mkdir(parents=True)
    it_spec = it_dir / "spec.yaml"
    it_spec.write_bytes(spec_bytes)
    _copy(spec_path, run_dir / "spec.yaml")
    it_model = it_dir / "model.xml"
    run_model = run_dir / "model.xml"

    build_error: Optional[str] = None
    try:
        from .builder import build_file

        build_file(it_spec, it_model)
        if not it_model.exists():
            raise RuntimeError(f"builder did not write {it_model}")
    except Exception as e:  # noqa: BLE001 - any build failure is a failed `compiles` check
        build_error = f"{type(e).__name__}: {e}"

    if build_error is not None:
        it_model.unlink(missing_ok=True)
        run_model.unlink(missing_ok=True)
        report = _failed_report(
            it_model, it_spec, f"build failed: {build_error}",
            "The spec could not be built into MJCF. Run `sim-anything validate spec.yaml`, fix the field "
            "named in the error message (schema errors name the field path), and loop again.")
    else:
        _copy(it_model, run_model)
        try:
            from .check import run_checks

            report = run_checks(it_model, it_spec)
        except Exception as e:  # noqa: BLE001
            report = _failed_report(
                it_model, it_spec, f"checks could not run on the built model: {type(e).__name__}: {e}",
                "The built MJCF could not be checked. Run `sim-anything check model.xml --spec spec.yaml` "
                "to see the error; it usually points at a degenerate value in the spec (zero-size geometry, "
                "non-finite numbers).")

    _write_report_json(it_dir / "check.json", report)
    _write_report_json(run_dir / "check.json", report)

    blocking = _blocking(report)
    history.iterations.append(IterationRecord(
        iteration=n,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        passed=report.passed,
        n_errors=report.n_errors,
        n_failed=report.n_failed,
        failed_ids=[c.id for c in blocking],
        note=note,
        build_error=build_error,
    ))
    if report.passed:
        history.status = "passed"
    elif n >= max_iter:
        history.status = "max_iter_reached"
    else:
        history.status = "running"
    _save_history(run_dir, history)

    extra = _finalize(run_dir)  # every iteration: report and renders always match check.json
    return _outcome(history, report, run_dir, _head(n, max_iter, report, history.status), extra)


__all__ = ["LoopOutcome", "FixHint", "loop_step"]
