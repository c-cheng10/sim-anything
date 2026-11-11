"""sim-anything command line interface. See docs/CONTRACTS.md for the contracts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from typer.core import TyperGroup

from .errors import describe_exception

# click's UsageError (typer may vendor its own copy of click, so take it from typer).
_USAGE_ERROR = next(c for c in typer.BadParameter.__mro__ if c.__name__ == "UsageError")


class _Group(TyperGroup):
    """Command group whose usage errors exit 1, not click's 2.

    Bad input (a missing file, ``--max-iter 0``, an unknown option) is exit 1
    on every command (docs/CONTRACTS.md section 2); exit 2 is reserved for
    ``loop``'s "max iterations reached".
    """

    def make_context(self, *args, **kwargs):  # type: ignore[override]
        try:
            return super().make_context(*args, **kwargs)
        except _USAGE_ERROR as e:
            e.exit_code = 1
            raise

    def invoke(self, ctx):  # type: ignore[override]
        try:
            return super().invoke(ctx)
        except _USAGE_ERROR as e:
            e.exit_code = 1
            raise


app = typer.Typer(cls=_Group, add_completion=False, no_args_is_help=True, pretty_exceptions_enable=False,
                  help="Reverse-engineer a robot arm into a verified MuJoCo simulation.")


@app.command()
def build(spec: Path = typer.Argument(..., exists=True, dir_okay=False, help="spec.yaml"),
          output: Path = typer.Option(..., "-o", "--output", help="MJCF file to write")) -> None:
    """Build MJCF from a spec."""
    from .builder import build_file

    try:
        out = build_file(spec, output)
    except Exception as e:  # noqa: BLE001 - report any build failure cleanly
        typer.echo(f"build failed: {describe_exception(e)}", err=True)
        raise typer.Exit(1)
    typer.echo(str(out))


@app.command("import-urdf")
def import_urdf_cmd(urdf: Path = typer.Argument(..., exists=True, dir_okay=False, help="robot.urdf"),
                    output: Path = typer.Option(..., "-o", "--output", help="MJCF file to write"),
                    collision: str = typer.Option("primitives", "--collision", help="primitives | hull | coacd"),
                    ee_link: Optional[str] = typer.Option(None, "--ee-link",
                                                          help="link carrying the EE site (default: the last link)"),
                    package_root: Optional[Path] = typer.Option(None, "--package-root", file_okay=False,
                                                                help="folder holding the packages of package:// paths")
                    ) -> None:
    """Import an official URDF into MJCF with simplified collision, position servos, a home keyframe and an EE site."""
    from .urdf_import import import_urdf

    try:
        out = import_urdf(urdf, output, collision=collision, ee_link=ee_link, package_root=package_root)
    except Exception as e:  # noqa: BLE001 - a clean message instead of a traceback
        typer.echo(f"import-urdf failed: {describe_exception(e)}", err=True)
        raise typer.Exit(1)
    typer.echo(str(out))


@app.command()
def check(model: Path = typer.Argument(..., exists=True, dir_okay=False, help="MJCF model"),
          spec: Optional[Path] = typer.Option(None, "--spec", exists=True, dir_okay=False),
          as_json: bool = typer.Option(False, "--json", help="print the check report as JSON"),
          seed: int = typer.Option(0, "--seed")) -> None:
    """Run kinematic and physical checks. Exit code 0 if no error-severity check failed."""
    from .check import run_checks

    if spec is not None:
        from .spec import load_spec

        try:
            load_spec(spec)
        except Exception as e:  # noqa: BLE001 - explain it here; the checks report it as failures too
            typer.echo(f"{spec}: {describe_exception(e)}", err=True)
    report = run_checks(model, spec, seed=seed)
    if as_json:
        typer.echo(json.dumps(report.to_json_dict(), indent=2))
    else:
        for c in report.checks:
            mark = "PASS" if c.passed else ("FAIL" if c.severity == "error" else c.severity.upper())
            typer.echo(f"[{mark}] {c.id}: {c.message}")
            if not c.passed and c.fix_hint:
                typer.echo(f"        fix: {c.fix_hint}")
        typer.echo(f"{report.n_checks - report.n_failed}/{report.n_checks} passed; errors: {report.n_errors}")
    raise typer.Exit(0 if report.passed else 1)


@app.command()
def render(model: Path = typer.Argument(..., exists=True, dir_okay=False),
           output: Path = typer.Option(..., "-o", "--output", help="directory for PNGs"),
           backend: str = typer.Option("auto", "--backend", help="auto | mujoco | matplotlib")) -> None:
    """Render front/side/top views of the model at its home pose."""
    from .render import render_views

    try:
        result = render_views(model, output, backend=backend)
    except Exception as e:  # noqa: BLE001 - a clean message instead of a traceback
        typer.echo(f"render failed: {describe_exception(e)}", err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps({k: str(v) for k, v in result.items()}, indent=2))


@app.command()
def report(run_dir: Path = typer.Argument(..., exists=True, file_okay=False)) -> None:
    """Write report.html and report.md for a loop run directory."""
    from .report import write_report

    html, md = write_report(run_dir)
    typer.echo(f"{html}\n{md}")


@app.command("eval")
def eval_cmd(candidate: Path = typer.Argument(..., exists=True, dir_okay=False),
             reference: Path = typer.Option(..., "--reference", exists=True, dir_okay=False),
             mapping: Path = typer.Option(..., "--map", exists=True, dir_okay=False),
             as_json: bool = typer.Option(False, "--json"),
             n_samples: int = typer.Option(2000, "--samples"),
             seed: int = typer.Option(0, "--seed"),
             output: Optional[Path] = typer.Option(None, "-o", "--output", help="also write JSON here")) -> None:
    """Score a candidate model against a reference model."""
    from .evaluate import evaluate, load_mapping

    try:
        mp = load_mapping(mapping)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"eval failed: {mapping}: {describe_exception(e, 'mapping')}", err=True)
        raise typer.Exit(1)
    try:
        res = evaluate(candidate, reference, mp, n_samples=n_samples, seed=seed)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"eval failed: {describe_exception(e)}", err=True)
        raise typer.Exit(1)
    data = res.model_dump(mode="json")
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, indent=2) + "\n")
    if as_json:
        typer.echo(json.dumps(data, indent=2))
    else:
        p = res.ee_position_error_mm
        typer.echo(f"kinematics score {res.kinematics_score:.1f}/100  score {res.score:.1f}/100  EE pos err mean {p.mean:.1f} p95 {p.p95:.1f} max {p.max:.1f} mm  "
                   f"orient p95 {res.ee_orientation_error_aligned_deg.p95:.1f} deg (aligned)  "
                   f"mass diff {res.mass_diff:+.2f} kg  dof match {res.dof_match}")
        for line in res.disagreements:
            typer.echo(f"datasheet vs reference: {line}")


@app.command()
def loop(spec: Path = typer.Argument(..., exists=True, dir_okay=False),
         run_dir: Path = typer.Option(..., "--run-dir"),
         max_iter: int = typer.Option(8, "--max-iter", min=1),
         note: Optional[str] = typer.Option(None, "--note", help="what changed since the last iteration"),
         as_json: bool = typer.Option(False, "--json")) -> None:
    """One build+check iteration recorded in RUN_DIR. Exit 0 passed, 1 fix needed, 2 max iterations reached."""
    from .loop import loop_step

    outcome = loop_step(spec, run_dir, max_iter=max_iter, note=note)
    if as_json:
        typer.echo(json.dumps(outcome.model_dump(mode="json"), indent=2))
    else:
        typer.echo(outcome.summary)
    raise typer.Exit(outcome.exit_code)


@app.command()
def schema(output: Optional[Path] = typer.Option(None, "-o", "--output")) -> None:
    """Print (or write) the spec JSON schema."""
    from .spec import json_schema

    text = json.dumps(json_schema(), indent=2)
    if output:
        output.write_text(text + "\n")
    else:
        typer.echo(text)


@app.command()
def validate(spec: Path = typer.Argument(..., exists=True, dir_okay=False)) -> None:
    """Validate a spec: schema, numbers lacking a source/estimate, bad source values and unmatched keys."""
    from .spec import (bad_source_values, describe_key, duplicate_keys, load_spec, uncovered_fields,
                       unmatched_keys)

    try:
        s = load_spec(spec)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"FAILED: {spec}: {describe_exception(e)}", err=True)
        raise typer.Exit(1)
    # the same source hygiene as the sources_complete check
    missing = uncovered_fields(s)
    bad = bad_source_values(s)
    unmatched = unmatched_keys(s)
    for m in missing:
        typer.echo(f"no source/estimate: {m}")
    for k, v in bad:
        typer.echo(f"source is not a URL or relative doc: path: sources[{k!r}] = {v!r}")
    for k in unmatched:
        typer.echo(f"key matches no field: {describe_key(s, k)}")
    for k in duplicate_keys(s):
        typer.echo(f"warning: `{k}` is in both `sources` and `estimates`")
    problems = []
    if missing:
        problems.append(f"{len(missing)} number(s) without a source or estimate (add each path to `sources` "
                        "with a URL, or to `estimates` with the reasoning in `notes`)")
    if bad:
        problems.append(f"{len(bad)} source value(s) that are not an http(s) URL or `doc:<relative path>`")
    if unmatched:
        problems.append(f"{len(unmatched)} sources/estimates key(s) naming no field of the spec")
    if problems:
        typer.echo(f"FAILED: {s.name}, {s.dof} DOF, " + "; ".join(problems))
        raise typer.Exit(1)
    typer.echo(f"ok: {s.name}, {s.dof} DOF, every number has a source or estimate")


@app.command()
def serve(model: Path = typer.Argument(..., exists=True, dir_okay=False, help="MJCF model"),
          ee_site: str = typer.Option("ee_site", "--ee-site", help="end-effector site")) -> None:
    """Serve the model to agents over MCP (stdio): state, joint targets, stepping, EE moves, renders."""
    from . import render

    if render.detect_backend() == "mujoco" and render._gl_cache:  # before mujoco loads, so render works headless
        os.environ.setdefault("MUJOCO_GL", render._gl_cache)
    try:
        from .control import Arm
        from .mcp_server import make_server

        server = make_server(Arm(model, ee_site))
    except Exception as e:  # noqa: BLE001 - a clean message instead of a traceback
        typer.echo(f"serve failed: {describe_exception(e)}", err=True)
        raise typer.Exit(1)
    server.run()  # stdio


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
