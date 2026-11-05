---
description: Build a verified MuJoCo model of a real robot arm from its public datasheets (gather -> spec -> loop -> report)
argument-hint: <robot name, e.g. "UR5e" or "Franka Emika Panda">
---

Build a verified MuJoCo simulation of this robot arm: **$ARGUMENTS**

Follow the `sim-anything` skill exactly (load it now if it is not already loaded). Summary:

1. Pick a slug for the robot (lowercase, underscores, e.g. `ur5e`, `kuka_iiwa14`) and work in
   `runs/<slug>/`. Create the directory. If `runs/<slug>/spec.yaml` already exists, continue
   from it instead of starting over.
2. **Gather**: find the manufacturer datasheet, manual and any published DH / kinematic table for
   the exact model variant. Write `runs/<slug>/sources.md` with each URL, access date and the exact
   quoted values. Never use URDF/MJCF/SDF/xacro files, MuJoCo Menagerie or ROS description
   packages as sources, and never invent numbers: unknown -> omit, or estimate listed in
   `estimates` with the reasoning in `notes`.
3. **Spec**: write `runs/<slug>/spec.yaml` (published DH table -> `dh_standard`/`dh_modified`
   copied verbatim; otherwise an `offset` chain from dimension drawings). Run
   `sim-anything validate runs/<slug>/spec.yaml` until it exits 0.
4. **Loop**: run
   `sim-anything loop runs/<slug>/spec.yaml --run-dir runs/<slug>/run --max-iter 8 --note "<what changed>"`.
   On exit 1, read the fix hints (stdout or `runs/<slug>/run/check.json`), fix the spec's
   interpretation (not sourced numbers), and run `loop` again. Stop on exit 0 (passed) or
   exit 2 (max iterations).
5. **Inspect**: look at `runs/<slug>/run/renders/front.png`, `side.png`, `top.png` and compare
   with product photos/drawings; fix and loop again if the shape is wrong.
6. **Report** to the user in a few lines: convention and its source, sourced vs estimated values,
   check status and iteration count, known gaps, and the paths to `spec.yaml`, `sources.md`,
   `run/report.html` and the renders.

If the `sim-anything` CLI is missing, install it with `pip install git+https://github.com/c-cheng10/sim-anything`
(or `pip install -e .` inside a clone); `python -m simanything.cli` works as a fallback.
