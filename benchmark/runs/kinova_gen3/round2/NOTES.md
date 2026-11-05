# Kinova Gen3 (7-DOF) round2 notes

- **Sources:** Gen3 User Guide R07 (geometric-parameter length table, joint limits, reach and its definition, actuator
  speeds/torques), Gen3 spec sheet R01 (large/small actuator per joint; reseller copy), product page (8.2 kg),
  one-pager (payload). All via web-search extracts; the length table came from Scribd/manualslib copies. The guide's
  DH table exists but its values could not be extracted. See `sources.md`.
- **Convention:** `offset`, from the length table (kinematic class: dimension table, with my own joint mapping, so all
  origins/axes are estimates). q = 0 = arm straight up; roll joints 1/3/5/7 about z, bend joints 2/4/6 about +y; all
  frames parallel to the base. Origins along z: 156.4, 128.4, 210.4, 210.4, 208.4, 105.9, 105.9 mm.
- **EE site:** 61.5 mm past actuator 7 along the last axis ("last actuator to end effector"), i.e. the tool interface
  face of actuator 7 (no separate flange, no gripper).
- **Estimates:** joint origins (mapping), axes and their signs, ee.origin mapping, all link radii. The 5.4 / 6.4 mm
  lateral offsets are omitted (could not be assigned), so the model is perfectly in-line.
- **Iterations:** 1. Passed on the first build.
- **Final status:** pass (14 checks, 0 errors). Reach 0.902 m vs rated 0.902 m (shoulder -> EE, as the guide defines
  it). Warning: joint_limits (joints 1/3/5/7 have no limits; they are continuous per the guide).
- **Renders:** straight-up "candle" configuration, consistent with Kinova product images of the arm at zero.
- **Doubts:** the zero pose (straight up) and bend-joint signs are inferred, not stated by a source; the ~1 cm of
  lateral offsets is missing; velocities are exact RPM conversions of unloaded actuator speeds; effort limits use
  peak torque (nominal is 39 / 13 Nm).
