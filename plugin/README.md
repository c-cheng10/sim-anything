# sim-anything Claude Code plugin

Gives Claude Code a `robot-to-mujoco` skill and a `/sim-anything <robot>` command that turn a real
robot arm's public datasheets into a verified MuJoCo model (spec.yaml -> MJCF -> checks -> renders
and report).

## Install

1. Install the Python CLI (the plugin calls `sim-anything`):

   ```bash
   pip install git+https://github.com/c-cheng10/sim-anything
   # or, from a clone:  pip install -e .
   sim-anything --help
   ```

2. In Claude Code, add the marketplace and install the plugin:

   ```
   /plugin marketplace add c-cheng10/sim-anything
   /plugin install sim-anything@sim-anything
   ```

   For local development use the path to your clone instead:
   `/plugin marketplace add ./path/to/sim-anything`.

## Use

```
/sim-anything UR5e
```

Claude gathers sources into `runs/ur5e/sources.md`, writes `runs/ur5e/spec.yaml`, runs
`sim-anything loop` until the checks pass (or 8 iterations), and writes
`runs/ur5e/run/report.html` with front/side/top renders (rewritten after every loop iteration, so
they always show the latest one; delete `runs/ur5e/run/` to start over). You can also just ask
"build a MuJoCo model of the Kinova Gen3"; the skill triggers on its own.

Recent Claude Code versions may list the `/sim-anything` command among the skills (for example in
`/skills` or the skill picker) rather than only under slash commands; it is the same command and works
the same way.

## Layout

```
plugin/
  .claude-plugin/plugin.json      # plugin manifest
  commands/sim-anything.md        # /sim-anything slash command
  skills/robot-to-mujoco/SKILL.md # the workflow the agent follows (skill `robot-to-mujoco`)
.claude-plugin/marketplace.json   # (repo root) marketplace listing this plugin at ./plugin
```
