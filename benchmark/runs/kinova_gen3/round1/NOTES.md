# Kinova Gen3 7-DoF (spherical wrist, no gripper): round 1 notes

**Sources.** Kinova Gen3 User Guide R07 (limits, speeds, torques, reach definition; search extracts),
User Guide Table 9 geometric parameters (search extract via manualslib/Scribd copies), Gen3 spec sheet
R01 (large/small actuator mapping; reseller-hosted copy), product page + 2024 one-pager (mass, payload).
Every manufacturer host and manual mirror was blocked from this session (network policy), so I could
not read the guide's DH page myself.

**Kinematic source / convention.** Published DH table, classical (`dh_standard`), from the guide's
"DH parameters - 7 DoF spherical wrist" section, but **second-hand**: copied from a third-party
transcription (github.com/Sahilnarola-1007/kinova-kinematics, design.md section 5.1, a C++ FK library,
no page reference). Source quality: second-hand. It is consistent with the guide's own (primary)
Table 9 lengths: d1 = -(156.4+128.4), d2 = -(5.4+6.4), d3 = -(210.4+210.4), d4 = -(6.4+6.4),
d5 = -(208.4+105.9), d7 = -(105.9+61.5) mm, so I trust it. Row 0 (alpha = pi) is a fixed
base -> frame-0 rotation, written as `base.origin.rpy: [180, 0, 0]`. theta_i = q_i + pi for rows 2..7.
Lengths kept in metres as transcribed; pi/2, pi written as 90 / 180 deg.

**EE site.** DH frame 7 = actuator 7's tool interface (flange face); no extra offset. At q = 0 the arm
stands straight up and the flange is at (0, -0.0246, 1.1873) m, matching the sum of the Table 9
lengths (1187.3 mm) and the -11.8 - 12.8 mm lateral joint offsets.

**Other values.** Limits: Table 35 software limits ±128.9 / ±147.8 / ±120.3 deg for joints 2/4/6;
joints 1/3/5/7 continuous (no limits). velocity_limit 78 / 150 deg/s = 13 / 25 RPM (exact
conversion). effort_limit 54 / 34 N m (R07 peak). Mass 8.2 kg, payload 4.0 kg (mid-range
continuous), reach 902 mm shoulder -> end-effector frame (stated by the guide per the extract).

**Estimates.** Only link collision geometry (radii 45 -> 32 mm, from product-photo proportions; no
housing diameters found). Link masses omitted (builder distributes total mass by volume).

**Iterations.**
1. Reach error: reach written as 902 in a metre-unit spec (units slip).
2. Reach written as 0.902 m -> PASSED (14 checks, 0 errors).

**Final status.** PASSED. Warnings: no limits on the 4 continuous joints (by design);
collision_exclusions lists two non-adjacent pairs (actuator_1/3 and 3/5 links) excluded because their
capsules overlap around the 11.8 / 12.8 mm offset links, so those pairs are never collision-checked.

**Doubts.** The DH rows are a second-hand transcription (not read from the guide); they match every
primary length, but the signs of d and the theta offsets (positive joint directions) rest on the
transcription alone. Physical actuator 3 sits mid upper arm and actuator 5 mid forearm; the capsules
just span the DH links. Home is q = 0 (straight-up, singular); Kinova's own "Home" pose was not used.
