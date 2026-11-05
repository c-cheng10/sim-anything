"""Build the static gallery site from benchmark runs.

Usage: python gallery/build.py [--out gallery/site]

For every robot in benchmark/robots.yaml (dev and holdout) it takes the latest
round directory under benchmark/runs/<id>/ that has a run/ with renders and
writes one card: front/side/top renders, check summary, iterations used, eval
error vs the reference model (if eval.json exists) and a link to the sources.
Everything is static (HTML + copied PNGs); no external assets.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/c-cheng10/sim-anything"


def _round_key(p: Path) -> tuple[int, str]:
    m = re.fullmatch(r"round(\d+)", p.name)
    return (int(m.group(1)) if m else -1, p.name)


def latest_round(robot_id: str) -> Path | None:
    base = ROOT / "benchmark" / "runs" / robot_id
    if not base.is_dir():
        return None
    rounds = sorted((d for d in base.iterdir() if d.is_dir() and (d / "run" / "renders").is_dir()), key=_round_key)
    return rounds[-1] if rounds else None


def card_data(robot: dict, split: str) -> dict | None:
    rd = latest_round(robot["id"])
    if rd is None:
        return None
    run = rd / "run"
    d: dict = {"id": robot["id"], "name": robot["name"], "manufacturer": robot.get("manufacturer", ""),
               "split": split, "round": rd.name, "renders": {},
               "kinematic_source": robot.get("kinematic_source", "unknown")}
    for v in ("front", "side", "top"):
        if (run / "renders" / f"{v}.png").exists():
            d["renders"][v] = run / "renders" / f"{v}.png"
    if (run / "check.json").exists():
        cj = json.loads((run / "check.json").read_text())
        d["checks_passed"] = cj["passed"]
        d["n_checks"] = cj["n_checks"]
        d["n_ok"] = cj["n_checks"] - cj["n_failed"]
        d["failed"] = [c["id"] for c in cj["checks"] if not c["pass"] and c["severity"] == "error"]
        d["n_warn"] = sum(1 for c in cj["checks"] if not c["pass"] and c["severity"] != "error")
    if (run / "history.json").exists():
        d["iterations"] = len(json.loads((run / "history.json").read_text()).get("iterations", []))
    if (rd / "eval.json").exists():
        ej = json.loads((rd / "eval.json").read_text())
        d["eval"] = {"p95": ej["ee_position_error_mm"]["p95"], "mean": ej["ee_position_error_mm"]["mean"],
                     "max": ej["ee_position_error_mm"]["max"], "score": ej["score"],
                     "limit_mae": ej["joint_limit_mae_deg"], "orient": ej["ee_orientation_error_aligned_deg"]["p95"]}
    d["sources_url"] = f"{REPO_URL}/blob/main/benchmark/runs/{robot['id']}/{rd.name}/sources.md"
    d["spec_url"] = f"{REPO_URL}/blob/main/benchmark/runs/{robot['id']}/{rd.name}/spec.yaml"
    d["report_rel"] = f"reports/{robot['id']}.html" if (run / "report.html").exists() else None
    d["report_src"] = run / "report.html"
    return d


CSS = """
:root { --bg:#f7f7f8; --card:#fff; --text:#1c1c1f; --muted:#666a73; --border:#e2e3e7; --ok:#1a7f37; --ok-bg:#dcf5e3;
        --fail:#b42318; --fail-bg:#fde4e1; --link:#2357c6; }
@media (prefers-color-scheme: dark) { :root { --bg:#141518; --card:#1d1f23; --text:#e8e8ea; --muted:#a0a3ab;
        --border:#2d3036; --ok:#56d17a; --ok-bg:#16351f; --fail:#ff8a80; --fail-bg:#3a1714; --link:#8fb0ff; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--text); font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
main { max-width:1200px; margin:0 auto; padding:24px 16px 48px; }
h1 { margin:0 0 4px; font-size:1.7rem; } h2 { margin:32px 0 12px; font-size:1.2rem; }
p.lead { color:var(--muted); margin:0 0 8px; max-width:70ch; }
a { color:var(--link); }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:16px; }
.card { background:var(--card); border:1px solid var(--border); border-radius:10px; overflow:hidden; display:flex; flex-direction:column; }
.card .views { display:grid; grid-template-columns:2fr 1fr; grid-template-rows:1fr 1fr; gap:2px; background:var(--border); }
.card .views img { width:100%; height:100%; object-fit:cover; display:block; }
.card .views img.main { grid-row:1 / span 2; }
.card .body { padding:12px 14px 14px; display:flex; flex-direction:column; gap:6px; }
.card h3 { margin:0; font-size:1.05rem; } .muted { color:var(--muted); font-size:.85rem; }
.badge { display:inline-block; padding:1px 8px; border-radius:999px; font-size:.8rem; font-weight:600; }
.ok { background:var(--ok-bg); color:var(--ok); } .fail { background:var(--fail-bg); color:var(--fail); }
dl { display:grid; grid-template-columns:auto 1fr; gap:2px 12px; margin:4px 0; font-size:.9rem; }
dt { color:var(--muted); } dd { margin:0; font-variant-numeric:tabular-nums; }
.links { display:flex; gap:14px; flex-wrap:wrap; font-size:.9rem; margin-top:4px; }
footer { margin-top:40px; color:var(--muted); font-size:.85rem; }
"""


def render_card(d: dict) -> str:
    e = html.escape
    imgs = d["renders"]
    views = ""
    if imgs:
        order = [v for v in ("front", "side", "top") if v in imgs]
        views = '<div class="views">' + "".join(
            f'<img class="{"main" if i == 0 else ""}" src="img/{e(d["id"])}_{v}.png" alt="{e(d["name"])} {v} view">'
            for i, v in enumerate(order)) + "</div>"
    if "checks_passed" in d:
        badge = (f'<span class="badge ok">all checks pass</span>' if d["checks_passed"]
                 else f'<span class="badge fail">fails: {e(", ".join(d["failed"]))}</span>')
        checks = f'{d["n_ok"]}/{d["n_checks"]} passed' + (f', {d["n_warn"]} warning(s)' if d["n_warn"] else "")
    else:
        badge, checks = '<span class="badge fail">no check report</span>', "-"
    rows = [("Checks", checks), ("Iterations", str(d.get("iterations", "-")))]
    if "eval" in d:
        ev = d["eval"]
        rows += [("EE error vs official model", f'{ev["mean"]:.1f} mean / {ev["p95"]:.1f} p95 / {ev["max"]:.1f} max mm'),
                 ("Joint-limit MAE", f'{ev["limit_mae"]:.1f}°'), ("Score", f'{ev["score"]:.1f} / 100')]
    else:
        rows.append(("EE error vs official model", "not evaluated"))
    rows.append(("Public kinematic source", d["kinematic_source"]))
    dl = "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in rows)
    links = [f'<a href="{e(d["sources_url"])}">sources</a>', f'<a href="{e(d["spec_url"])}">spec.yaml</a>']
    if d.get("report_rel"):
        links.insert(0, f'<a href="{e(d["report_rel"])}">full report</a>')
    return (f'<article class="card">{views}<div class="body"><h3>{e(d["name"])}</h3>'
            f'<div class="muted">{e(d["manufacturer"])} · {e(d["split"])} set · {e(d["round"])}</div>'
            f'<div>{badge}</div><dl>{dl}</dl><div class="links">{" ".join(links)}</div></div></article>')


def build(out: Path) -> Path:
    robots = yaml.safe_load((ROOT / "benchmark" / "robots.yaml").read_text())
    if out.exists():
        shutil.rmtree(out)
    (out / "img").mkdir(parents=True)
    (out / "reports").mkdir()
    sections = []
    for split in ("dev", "holdout"):
        cards = []
        for r in robots.get(split, []):
            d = card_data(r, split)
            if d is None:
                continue
            for v, p in d["renders"].items():
                shutil.copy(p, out / "img" / f"{d['id']}_{v}.png")
            if d.get("report_rel"):
                shutil.copy(d["report_src"], out / d["report_rel"])
            cards.append(render_card(d))
        title = "Development set" if split == "dev" else "Holdout set (evaluated once, with the final tool)"
        body = "".join(cards) if cards else '<p class="muted">Not run yet.</p>'
        sections.append(f'<h2>{title}</h2><div class="grid">{body}</div>')
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>sim-anything gallery</title><style>{CSS}</style></head>
<body><main>
<h1>sim-anything gallery</h1>
<p class="lead">Robot arms reverse-engineered into MuJoCo models from public datasheets, generated blind by an agent
and scored against MuJoCo Menagerie reference models. Primitive geometry only; errors are end-effector position
differences over 2,000 random configurations after discrete convention alignment.
<a href="{REPO_URL}">Source and methodology</a> · <a href="{REPO_URL}/blob/main/benchmark/RESULTS.md">full results</a>.</p>
{''.join(sections)}
<footer>Menagerie models are used only as an external evaluation reference and are not redistributed.</footer>
</main></body></html>
"""
    (out / "index.html").write_text(page, encoding="utf-8")
    return out / "index.html"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "gallery" / "site"))
    args = ap.parse_args()
    print(build(Path(args.out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
