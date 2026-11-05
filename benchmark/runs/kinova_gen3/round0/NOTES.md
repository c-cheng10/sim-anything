# Kinova Gen3 7-DOF (round0): notes

**Sources.** Kinova Gen3 User Guide R07 (Table 9 geometric parameters, Table 35 joint limits, actuator speeds and
torques, reach definition), the Gen3 spec sheet (actuator-to-joint mapping), the product page (8.2 kg) and the 2024
one-pager (4.0 kg payload), all from search extracts (Kinova and manual mirror hosts were blocked). The classic DH
table came from a secondary source: the design notes of a GitHub C++ FK library
(github.com/Sahilnarola-1007/kinova-kinematics, design.md section 5.1). It attributes the table to Kinova's
kinematic parameters but gives no table reference. Quotes are in `sources.md`.

**Convention.** `dh_standard` (classic DH). Rows copied as published: lengths in m, pi/2 and pi written as 90 and
180 deg. The table's fixed base row (alpha = pi) is `base.origin.rpy: [180, 0, 0]`. Rows 2 to 7 have
theta offset 180. q = 0 is the vertical "candle" pose with the flange at z = 1.1873 m and a lateral offset of
-0.0246 m (11.8 + 12.8 mm joint offsets). That matches the [COMPUTED] value in the secondary source.

**EE site.** At DH frame 7, which is the tool interface/flange face. Its d7 = 167.4 mm = second wrist length 105.9
plus "last actuator to end effector" 61.5 (Table 9), so `ee.origin` is zero. I did not use the gripper "tool"
row (+113 mm).

**Cross-check of the DH table against the official Table 9.** d1 284.8 = base to shoulder; d2 11.8 = 5.4 + 6.4
joint offsets; d3 420.8 = 2 x 210.4; d5 314.3 = 208.4 + 105.9; d7 167.4 = 105.9 + 61.5. Only d4 = 12.8 cannot be
checked from the extract.

**Estimates.** Only the link capsule radii are estimated: 45 mm for the large-actuator links and 35 mm for the
small ones. No housing diameters were found.
**Conversions.** velocity_limit is 13 RPM = 78 deg/s for joints 1 to 4 and 25 RPM = 150 deg/s for joints 5 to 7.
effort_limit is peak torque: 54 N·m for the large actuators and 34 N·m for the small ones.
**Continuous joints.** Joints 1, 3, 5 and 7 have no limits, as the guide states.

**Iterations.** There was 1 iteration, and it passed: 11 checks, 0 errors, 1 warning. The warning is joint_limits:
joints 1, 3, 5 and 7 are unlimited, which is intended. Reach is 0.9029 m against the rated 0.902 m measured from
the shoulder. Mass is 8.2 kg. There is no self-collision at home, and the arm holds its pose stably.

**Renders.** The front and side views show the arm straight up. This matches Kinova's documented zero configuration
(all joints at 0 = vertical). Roll joints 1, 3, 5 and 7 are vertical and bend joints 2, 4 and 6 are horizontal, as
in the 7-DOF spherical-wrist layout.

**Doubts.**
- The DH values come from a secondary source, because the official table could not be fetched. They agree with the
  official Table 9, but the axis sign conventions (alpha and theta-offset signs, which determine the joint
  directions) depend on that secondary source alone.
- The joint offsets give a 24.6 mm lateral offset. Its direction (-y at q = 0) follows the table and was not
  checked against a drawing.
- The collision radii are guesses.
- The mass is 8.2 kg (product page) against 8.3 kg (guide, with the vision module).
