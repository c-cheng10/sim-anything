# Franka Emika Panda (FER, no hand), round0

**Sources.** FCI robot-specifications page (modified DH table, flange row, torque limits), Gaz et al. RA-L 2019
(Panda-specific confirmation of the table, row 7 alpha), Panda datasheet May 2019 (joint limits, speeds, reach,
payload, repeatability, ~17.8 kg), libfranka `generate_joint_position_motion.cpp` (home pose). Franka docs
hosts were unreachable, so the DH values are from web-search extracts (pre-gathered inputs); see `sources.md`.

**Convention.** `dh_modified` (FCI: "following Craig's convention"), each row copied as published (no theta
offsets); units m / deg, alpha pi/2 written as 90.

**EE site.** Tool flange face: the DH "Flange" row, `ee.origin = [0, 0, 0.107]` in frame 7. At q = 0 the
flange is at (0.088, 0, 0.926) m pointing down; at home it is at (0.307, 0, 0.590) m pointing down.

**Home.** [0, -45, 0, -135, 0, 90, 45] deg (libfranka example start pose). Needed because A4 = 0 is outside
its range (-176..-4 deg).

**Estimates.** Only link/base collision radii (0.06 -> 0.04 m, from photos; no housing dimensions published).
Per-link masses omitted (builder distributes 17.8 kg by volume).

**Interpretation.** Reach 855 mm has no stated reference points; `shoulder -> ee_site` gives 0.858 m model reach
(0.3% off), so I kept it.

**Iterations.** 1 iteration, passed all 11 checks (load, joints, EE site, ranges, reach, mass, inertia,
self-collision at home, holds home 2 s, actuators, sources complete). Renders show the familiar Panda
"ready" pose: upper arm tilted back 45 deg, elbow high, forearm sloping forward, flange pointing down in front
of the base.

**Doubts.** DH values not read from the live page (extracts only; the current FCI page labels the table FR3,
Panda equality relies on the old page and Gaz 2019). A5-A7 180 deg/s seen in one datasheet version only.
Mass 17.8 (datasheet) vs approx. 18 kg (handbook). Collision geometry is crude (capsules between frame
origins; zero-length capsules where frames coincide, e.g. links 1, 5).
