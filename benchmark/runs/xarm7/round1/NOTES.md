# UFactory xArm 7 (no gripper): round 1 notes

**Sources.** UFACTORY support article "Kinematic and dynamic parameters - xArm 7" (modified DH
table), xArm user manual chapter 8 technical specifications (joint ranges, joint speed,
repeatability), xArm5/6/7 comparison support article and product page (mass, payload, reach). All
UFACTORY hosts were blocked from this session, so every value is a web-search extract of the
manufacturer page (primary documents, read through search extracts). No second-hand sources.

**Kinematic source / convention.** Published DH table, `dh_modified` (page section "Modified D-H
parameters", manufacturer, primary). Rows copied verbatim (row i = a_{i-1}, alpha_{i-1}, d_i, theta_i);
theta/offset columns are all 0; -pi/2, pi/2 written as -90 / 90 deg; lengths in mm.

**EE site.** At DH frame 7 (after d7 = 97 mm, a6 = 76 mm), taken to be the tool flange face; the
table has no separate flange row, so this is my interpretation (UFACTORY's default TCP is the
flange centre). At q = 0 the flange is at (206, 0, 120.5) mm pointing straight down, with the upper
arm vertical and the forearm folded back down: the folded xArm zero pose.

**Estimates.** Reach definition (`reach.measured_from` = shoulder, `reach.measured_to` = ee_site):
the 700 mm figure is published without a definition. Link collision radii (50 -> 38 mm) from
product-photo proportions. Joint torques and link masses not found (omitted).

**Conflicts.** Joint ranges: manual J2 -117~116, J4 -6~225 (used) vs comparison article J2 -118~120,
J4 -11~225. Mass: 13.7 kg (product page, used) vs 14.3 kg (manual).

**Iterations.**
1. PASSED (14 checks, 0 errors) on the first iteration; nothing needed fixing.

**Final status.** PASSED with 2 warnings:
- reach: max shoulder-to-flange distance 772 mm is 10.3% above the rated 700 mm (a warning only
  because the definition is an estimate). I did not switch the endpoints to make it fit. 700 mm
  probably uses a different definition (e.g. to the wrist, or a working-range radius).
- collision_exclusions: joint2_link / joint4_link are excluded because their capsules overlap
  around the zero-length joint3 link, so that pair is never collision-checked.

**Doubts.** The DH rows come from search extracts of the page (two queries put together: rows 1, 2, 7
from one, 3-6 from the other), not a direct read. The table's flange/TCP convention was not
confirmed. The capsules join the DH frame origins, so the forearm and wrist look diagonal in the
renders. The real housings follow the a-offsets in steps instead.
