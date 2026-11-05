---
description: Build a verified MuJoCo model of a real robot arm from its public datasheets (gather -> spec -> loop -> report)
argument-hint: <robot name, e.g. "UR5e" or "Franka Emika Panda">
---

Build a verified MuJoCo simulation of this robot arm: **$ARGUMENTS**

Follow the `robot-to-mujoco` skill exactly (load it now if it is not already loaded). Summary:

1. Pick a slug for the robot (lowercase, underscores, e.g. `ur5e`, `kuka_iiwa14`). All paths are
   relative to the current project root: the robot's files go in `runs/<slug>/` (create it) and the
   loop run directory is `runs/<slug>/run/`. If `runs/<slug>/spec.yaml` already exists, continue
   from it. To start over, delete `runs/<slug>/run/` (or use a new `--run-dir`); iteration
   numbering then restarts at 1.
2. **Gather**: find the manufacturer datasheet, manual and any published DH / kinematic table for
   the exact model variant; prefer the most authoritative primary source. Write
   `runs/<slug>/sources.md` with each URL, access date and the exact quoted values, and mark any
   second-hand source (forum, reseller copy, third-party page, search excerpt) as such. Never use
   URDF/MJCF/SDF/xacro files, MuJoCo Menagerie or ROS description packages as sources, and never
   invent numbers: unknown -> omit, or an estimate listed in `estimates` with the reasoning in
   `notes`. Generated outputs are not sources: while gathering, never read other runs (`runs/`,
   `benchmark/runs/`), HANDOFF/RESULTS files, eval outputs or the git history of this repository;
   sources are external public documents only (your own `runs/<slug>/` files are fine).
3. **Spec**: classify the kinematic source and state it first in `notes`: published DH table
   (`dh_standard`/`dh_modified`, rows copied verbatim) / published screw-axis or "home
   configuration + joint axes" table (converted exactly to `offset` as the skill explains) /
   dimension drawing (`offset`) / inferred (`offset`, all estimates). Write
   `runs/<slug>/spec.yaml`:
   * `sources` values are http(s) URLs (or `doc:<path>` for a local document); `sources` keys and
     `estimates` entries must be exact spec field paths.
   * Anything inferred (unlabelled drawing dimensions mapped to links, axis directions read off
     pictures, letter-to-dimension mappings) goes in `estimates`, not `sources`, even if the raw
     numbers are sourced; explain it in `notes`.
   * Set `reach.measured_from` / `reach.measured_to` only from what the source states; if it does
     not say, pick the most likely definition and list both paths in `estimates`. Never switch
     reach endpoints just to make the check pass.

   Run `sim-anything validate runs/<slug>/spec.yaml` until it exits 0 (`ok: ...`).
4. **Loop**: run
   `sim-anything loop runs/<slug>/spec.yaml --run-dir runs/<slug>/run --max-iter 8 --note "<what changed>"`.
   On exit 1, read every failed check's fix hint (stdout or `runs/<slug>/run/check.json`), fix the
   spec's interpretation (not sourced numbers), and run `loop` again. Stop on exit 0 (passed: a
   one-line summary; details in `check.json`) or exit 2 (max iterations reached, or a changed spec
   the cap kept from being checked). The renders and report are rewritten after every iteration,
   so they always show the latest one.
5. **Inspect**: look at `runs/<slug>/run/renders/front.png`, `side.png`, `top.png` and compare
   with product photos/drawings; fix and loop again if the shape is wrong.
6. **Report** to the user in a few lines: kinematic source class, convention and its source (and
   any second-hand sources), sourced vs estimated values, check status (errors and warnings) and
   iteration count, known gaps, and the paths to `runs/<slug>/spec.yaml`, `runs/<slug>/sources.md`,
   `runs/<slug>/run/report.html` and the renders.

If the `sim-anything` CLI is missing, install it with `pip install git+https://github.com/c-cheng10/sim-anything`
(or `pip install -e .` inside a clone); `python -m simanything.cli` works as a fallback.
