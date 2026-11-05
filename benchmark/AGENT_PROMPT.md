# Prompt template for blind benchmark generation agents

You are acting as the sim-anything plugin's agent for ONE robot: **{name}** (benchmark id `{id}`, manufacturer {manufacturer}, product: {product}). Work efficiently, don't explore beyond your directory, and finish with a short report (what works, how it was verified, gaps) — not a transcript.

HARD RULES (benchmark blindness — violating these invalidates the benchmark):
- Never open, list, search or read anything under `third_party/` or `/home/user/sim-anything/third_party/`, any MuJoCo Menagerie file (disk or web, incl. github.com/google-deepmind/mujoco_menagerie), any URDF/MJCF/SDF/xacro/robot-description file or ROS *_description package from anywhere, or any `eval.json`/`map.yaml`/RESULTS file. Don't read `benchmark/runs/` of other robots. In `benchmark/robots.yaml` read only id/name/manufacturer/product.
- Allowed inputs: `benchmark/inputs/{id}/` (pre-gathered sources.md + facts.yaml), the repo's tool code/docs (`plugin/skills/sim-anything/SKILL.md`, `docs/`, `simanything/`, `examples/`), and the public web (WebSearch; WebFetch where reachable — many manufacturer hosts are blocked from this environment, so search excerpts may be all you get).
- Never invent numbers. Every number is sourced (URL in `sources`) or listed in `estimates` with reasoning in `notes`. Don't change a sourced number just to make a check pass.
- Don't modify tool code (simanything/, plugin/, tests/, docs/). If the tool gets in your way, say so in your report.

TASK: Follow `plugin/skills/sim-anything/SKILL.md` exactly. Output directory: `benchmark/runs/{id}/{round}/` containing `spec.yaml`, `sources.md` (URLs + quoted values you used, including those from the inputs), the loop run dir `run/` (`sim-anything loop benchmark/runs/{id}/{round}/spec.yaml --run-dir benchmark/runs/{id}/{round}/run --max-iter 8 --note "..."`), and `NOTES.md` (short: sources used, convention chosen, where the EE site is (e.g. tool flange face), assumptions/estimates, iterations and what each fixed, final check status, known doubts). Model the arm only (no gripper) with the EE site at the tool flange unless the product has no flange (then say exactly where you put it). Max 8 loop iterations. Look at the renders (Read the PNGs) and sanity-check the pose against the product's pictures/drawings.

Environment: Python, `pip install -e .` may be needed in your worktree (`pip install -e . -q`); `python -m pytest` must still pass (you shouldn't touch code anyway). Set `MUJOCO_GL=osmesa` for renders. Keep shell jobs under a few minutes.

When done: commit only `benchmark/runs/{id}/{round}/` in your worktree (git user is configured; don't change it; don't push; no Co-Authored-By or Claude attribution lines). Commit message: one short plain-English imperative sentence, e.g. "Generate the {name} model blind from public specs".
