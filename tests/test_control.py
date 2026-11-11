import math
from pathlib import Path

import mujoco
import numpy as np
import pytest

from simanything.builder import build_mjcf
from simanything.control import Arm
from simanything.spec import load_spec

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def model_path(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("control") / "toy_6dof_dh.xml"
    p.write_text(build_mjcf(load_spec(ROOT / "examples" / "toy_6dof_dh.yaml")))
    return p


def test_load(model_path):
    arm = Arm(model_path)
    assert arm.joints == ["j1", "j2", "j3", "j4", "j5", "j6"]
    assert np.allclose(arm.lower[2:4], [-math.pi, -2 * math.pi]) and np.allclose(arm.upper[2:4], [math.pi, 2 * math.pi])
    assert [arm.model.actuator(a).name for a in arm.act] == [f"{j}_act" for j in arm.joints]
    with pytest.raises(KeyError):
        Arm(model_path, ee_site="nope")
