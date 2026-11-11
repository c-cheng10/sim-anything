"""Build the toy 6-DOF arm, then drive it with simanything.control.Arm.

Run from the repository root: python examples/use_model.py
"""

import tempfile
from pathlib import Path

import numpy as np

from simanything.builder import build_file
from simanything.control import Arm

model = build_file(Path(__file__).parent / "toy_6dof_dh.yaml", Path(tempfile.mkdtemp()) / "toy_6dof_dh.xml")
arm = Arm(model)
print("joints:", arm.joints)

# joint space: command targets through the position actuators and let the servos get there
arm.set_targets([0.5, -1.0, 1.2, -0.3, 0.6, 0.0])
arm.step(1000)  # 2 s
s = arm.state()
print("q:", np.round(s["q"], 3))
print("EE pos [m]:", np.round(s["ee_pos"], 4), "quat (w,x,y,z):", np.round(s["ee_quat"], 4))

# task space: move the EE 10 cm up, keeping its orientation
target = np.array(s["ee_pos"]) + [0.0, 0.0, 0.1]
q, ik_pos_err, ik_rot_err = arm.ik(target, s["ee_quat"])
print(f"IK error: {ik_pos_err * 1e3:.4f} mm, {ik_rot_err:.2e} rad")
pos_err, rot_err = arm.move_to(target, s["ee_quat"], duration=2.0)
print(f"after move_to: {pos_err * 1e3:.2f} mm, {rot_err:.4f} rad")
arm.step(250)  # settle 0.5 s
err = np.linalg.norm(np.array(arm.state()["ee_pos"]) - target)
print(f"after settling: {err * 1e3:.3f} mm")
