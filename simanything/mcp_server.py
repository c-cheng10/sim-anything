"""An MCP server that lets agents drive an `Arm` (see `sim-anything serve`). Needs the optional `mcp` package."""

from __future__ import annotations

import os
import tempfile

from .control import Arm


def make_server(arm: Arm):
    """An MCP server whose tools call ``arm``'s methods. Raises ImportError if `mcp` is missing."""
    try:
        from mcp.server.mcpserver import MCPServer
        from mcp.server.mcpserver.exceptions import ToolError  # its message reaches the agent; other errors do not
    except ImportError as e:
        raise ImportError("the MCP server needs the `mcp` package (>= 2): pip install 'mcp>=2'") from e

    server = MCPServer("sim-anything", instructions=(
        f"A simulated robot arm with joints {arm.joints} (radians or metres, in this order). "
        "Positions are in metres in the world frame; quaternions are (w, x, y, z). "
        f"The simulation advances only when you call step or move_ee (timestep {arm.model.opt.timestep} s)."))

    async def get_state() -> dict:
        """Joint positions q and velocities qd, EE position and quaternion, simulation time."""
        return arm.state()

    async def set_joint_targets(q: list[float]) -> dict:
        """Set position targets for all joints (clipped to their limits); returns the targets set. Call step to move."""
        if len(q) != len(arm.joints):
            raise ToolError(f"expected {len(arm.joints)} targets, one per joint {arm.joints}")
        return {"targets": arm.set_targets(q).tolist()}

    async def step(n: int = 1) -> dict:
        """Advance the simulation n timesteps; returns the new state."""
        if n < 1:
            raise ToolError("n must be >= 1")
        arm.step(n)
        return arm.state()

    async def move_ee(position: list[float], quaternion: list[float] | None = None, duration: float = 2.0) -> dict:
        """Move the end effector to a world position (and orientation, if a quaternion w, x, y, z is given)
        with IK and a smooth joint move over `duration` seconds; returns the remaining errors and the state."""
        if len(position) != 3 or (quaternion is not None and len(quaternion) != 4):
            raise ToolError("position needs 3 numbers and quaternion 4 (w, x, y, z)")
        perr, rerr = arm.move_to(position, quaternion, duration)
        return {"position_error_m": perr, "orientation_error_rad": rerr, "state": arm.state()}

    async def reset() -> dict:
        """Return to the home pose; returns the state."""
        arm.reset()
        return arm.state()

    async def render() -> str:
        """Render the current state to a PNG file; returns its path."""
        fd, path = tempfile.mkstemp(prefix="sim-anything-", suffix=".png")
        os.close(fd)
        try:
            return str(arm.render(path))
        except Exception as e:  # noqa: BLE001 - usually no offscreen GL; tell the agent why
            os.unlink(path)
            raise ToolError(f"render failed: {e}") from e

    # async on purpose: MCP runs plain functions in worker threads, and one MuJoCo state must not be stepped
    # from several threads at once (parallel calls segfaulted)
    for fn in (get_state, set_joint_targets, step, move_ee, reset, render):
        server.add_tool(fn)
    return server
