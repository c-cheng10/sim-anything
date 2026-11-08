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

Claude leads a four-agent team: `source-scout` gathers sources into `runs/ur5e/sources.md`,
`spec-writer` writes `runs/ur5e/spec.yaml`, `loop-fixer` runs `sim-anything loop` until the checks
pass (or 8 iterations), and `source-auditor` reviews the result read-only (one rework round if it
says "not ready"). The run leaves `runs/ur5e/run/report.html` with front/side/top renders (rewritten after every loop iteration, so
they always show the latest one; delete `runs/ur5e/run/` to start over). You can also just ask
"build a MuJoCo model of the Kinova Gen3"; the skill triggers on its own.

`/sim-anything-audit ur5e` runs only the auditor on an existing `runs/ur5e/`. A team run costs
roughly 2-3x a single-agent run (one measured run: 7 minutes, about $2.20) in exchange for the
independent audit.

Recent Claude Code versions may list the `/sim-anything` command among the skills (for example in
`/skills` or the skill picker) rather than only under slash commands; it is the same command and works
the same way.

## Layout

```
plugin/
  .claude-plugin/plugin.json      # plugin manifest
  commands/sim-anything.md        # /sim-anything: the lead, runs the four agents in order
  commands/sim-anything-audit.md  # /sim-anything-audit: auditor only, on an existing run
  agents/source-scout.md          # finds and quotes public sources -> sources.md
  agents/spec-writer.md           # sources.md -> spec.yaml, validated
  agents/loop-fixer.md            # build/check loop + render inspection
  agents/source-auditor.md        # read-only audit and verdict
  skills/robot-to-mujoco/SKILL.md # the workflow the agent follows (skill `robot-to-mujoco`)
.claude-plugin/marketplace.json   # (repo root) marketplace listing this plugin at ./plugin
```
