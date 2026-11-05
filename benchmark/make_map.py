"""Write benchmark/runs/<id>/<round>/map.yaml from the candidate spec and reference_sides.yaml.

Usage: python benchmark/make_map.py <round> [ids...]
Candidate side: the spec's joints in chain order and its EE site, in world coordinates
(the spec's base.origin places the arm's mounting frame in the world; the builder's
`base` body may carry a rotation used to orient DH frame 0, so it is not the mount).
Reference side: its mounting base body (removes pedestals such as xArm's).
Orchestrator-only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from simanything.spec import load_spec  # noqa: E402


def main() -> int:
    rnd, ids = sys.argv[1], sys.argv[2:]
    refs = yaml.safe_load((ROOT / "benchmark/reference_sides.yaml").read_text())
    for rid in ids or refs:
        rd = ROOT / "benchmark/runs" / rid / rnd
        sp = rd / "run" / "spec.yaml"
        if not sp.exists():
            print(f"{rid}: no {sp}")
            continue
        spec = load_spec(sp)
        ref = refs[rid]
        n = min(len(spec.joints), len(ref["joints"]))
        m = {"robot": rid,
             "candidate": {"joints": [j.name for j in spec.joints][:n], "ee": {"site": spec.ee.name}},
             "reference": {"joints": ref["joints"][:n], "ee": ref["ee"], "base_body": ref["base_body"]},
             "fit_conventions": True}
        (rd / "map.yaml").write_text(yaml.safe_dump(m, sort_keys=False))
        print(f"{rid}: wrote {rd / 'map.yaml'} ({len(spec.joints)} cand joints, {len(ref['joints'])} ref joints)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
