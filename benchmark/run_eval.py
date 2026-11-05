"""Evaluate one benchmark round and print a markdown results table.

Usage:
    python benchmark/run_eval.py round0 [--set dev|holdout] [--samples 2000]

For each robot in the chosen set this reads
    benchmark/runs/<id>/<round>/run/model.xml      (candidate, written by the blind agent)
    benchmark/runs/<id>/<round>/map.yaml           (joint mapping, written by the orchestrator)
    benchmark/runs/<id>/<round>/run/check.json     (checker report)
    benchmark/runs/<id>/<round>/run/history.json   (loop history)
writes benchmark/runs/<id>/<round>/eval.json and prints one table row per robot.
The reference model path comes from benchmark/robots.yaml (third_party/, not redistributed).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simanything.evaluate import evaluate, load_mapping  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("round")
    ap.add_argument("--set", default="dev", choices=["dev", "holdout"])
    ap.add_argument("--samples", type=int, default=2000)
    args = ap.parse_args()

    robots = yaml.safe_load((ROOT / "benchmark/robots.yaml").read_text())[args.set]
    header = ("| Robot | Kinematic source | Checks | Iterations | EE pos mean / p95 / max (mm) | "
              "Orient p95 aligned (deg) | Limit MAE (deg) | Mass cand / ref (kg) | Conventions fitted | Score |")
    print(header)
    print("|" + "---|" * 10)
    p95s_dh = []
    for r in robots:
        rd = ROOT / "benchmark/runs" / r["id"] / args.round
        model = rd / "run" / "model.xml"
        mp = rd / "map.yaml"
        checks = "missing"
        iters = "-"
        if (rd / "run/check.json").exists():
            cj = json.loads((rd / "run/check.json").read_text())
            failed = [c["id"] for c in cj["checks"] if not c["pass"] and c["severity"] == "error"]
            checks = "all pass" if cj["passed"] else "fail: " + ", ".join(failed)
        if (rd / "run/history.json").exists():
            hj = json.loads((rd / "run/history.json").read_text())
            iters = str(len(hj.get("iterations", [])))
        if not model.exists() or not mp.exists():
            print(f"| {r['name']} | {r.get('kinematic_source', '?')} | {checks} | {iters} | no model or map | - | - | - | - | - |")
            continue
        res = evaluate(model, ROOT / r["reference"], load_mapping(mp), n_samples=args.samples, seed=0)
        (rd / "eval.json").write_text(json.dumps(res.model_dump(mode="json"), indent=2) + "\n")
        p = res.ee_position_error_mm
        flips = sum(c.sign == -1 for c in res.conventions)
        offs = sum(c.offset != 0.0 for c in res.conventions)
        conv = f"yaw {res.base_yaw_deg:+.0f}°, {flips} sign flip(s), {offs} offset(s)"
        if r.get("publishes_dh"):
            p95s_dh.append(p.p95)
        print(f"| {r['name']} | {r.get('kinematic_source', '?')} | {checks} | {iters} | "
              f"{p.mean:.1f} / {p.p95:.1f} / {p.max:.1f} | {res.ee_orientation_error_aligned_deg.p95:.1f} | "
              f"{res.joint_limit_mae_deg:.1f} | {res.mass_candidate:.2f} / {res.mass_reference:.2f} | "
              f"{conv} | {res.score:.1f} |")
    if p95s_dh:
        print(f"\nMedian p95 EE position error, robots with published DH: {statistics.median(p95s_dh):.1f} mm "
              f"(n={len(p95s_dh)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
