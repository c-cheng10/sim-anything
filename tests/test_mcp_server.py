import asyncio
import json
from pathlib import Path

import pytest

pytest.importorskip("mcp.server.mcpserver")

from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

from simanything.builder import build_mjcf  # noqa: E402
from simanything.control import Arm  # noqa: E402
from simanything.mcp_server import make_server  # noqa: E402
from simanything.spec import load_spec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def test_tools_drive_the_arm(tmp_path):
    model = tmp_path / "arm.xml"
    model.write_text(build_mjcf(load_spec(ROOT / "examples" / "toy_6dof_dh.yaml")))
    server = make_server(Arm(model))

    def call(name, **args):
        return json.loads(asyncio.run(server.call_tool(name, args)).content[0].text)

    names = {t.name for t in asyncio.run(server.list_tools())}
    assert names == {"get_state", "set_joint_targets", "step", "move_ee", "reset", "render"}
    assert call("set_joint_targets", q=[0.2, -0.5, 9.0, 0, 0, 0])["targets"][2] == pytest.approx(3.14159265359)
    with pytest.raises(ToolError, match="expected 6 targets"):
        call("set_joint_targets", q=[0.2])
    assert call("step", n=500)["q"][0] == pytest.approx(0.2, abs=1e-2)
    res = call("move_ee", position=[-0.5, -0.2, 0.3])
    assert res["position_error_m"] < 0.01 and res["orientation_error_rad"] == 0
    assert call("reset")["q"] == [0.0] * 6 == call("get_state")["q"]


def test_parallel_tool_calls_do_not_crash(tmp_path):
    # agents send tool calls in parallel; they must not step one simulation from several threads
    import subprocess
    import sys

    model = tmp_path / "arm.xml"
    model.write_text(build_mjcf(load_spec(ROOT / "examples" / "toy_6dof_dh.yaml")))
    code = f"""
import asyncio
from simanything.control import Arm
from simanything.mcp_server import make_server
s = make_server(Arm({str(model)!r}))
async def main():
    await asyncio.gather(s.call_tool("move_ee", {{"position": [-0.5, -0.2, 0.3]}}), s.call_tool("reset", {{}}),
                         s.call_tool("step", {{"n": 2000}}), s.call_tool("step", {{"n": 2000}}))
asyncio.run(main())
"""
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-500:]
