# Sources: Kinova Gen3 7-DoF (spherical wrist), bare arm, EE at interface module

Access date for everything below: 2026-11-09.

## Access situation (read this first)

Every WebFetch attempt in this session returned `proxy refused the connection`, for
every host tried, including hosts with no reason to be blocked (the coordinator reports
that curl also gets 403 from the proxy):

- https://www.kinovarobotics.com/uploads/User-Guide-Gen3-R07.pdf (primary user guide)
- https://www.kinovarobotics.com/uploads/Kinova_Onepager_Gen3_2026_EN.pdf (primary one-pager)
- https://csis.pace.edu/robotlab/papers/Gen3Manual.pdf (mirror of the user guide)
- https://www.manualslib.com/manual/1529186/Kinova-Gen3.html (mirror of the user guide)
- https://manualshive.com/en/manual/kinova/gen3/1971410?page=60 (mirror)
- https://manuals.online/kinova/robotics/gen3/user-manual/1sz6k (mirror)
- https://arxiv.org/abs/2102.01217 (control test, also refused)

So **no document was opened**. Everything below is **search excerpt only** (the WebSearch
tool's summary of a page). Where the excerpt reproduced a fragment of the page verbatim,
it is quoted in "double quotes"; everything else is the search tool's paraphrase and is
marked "(paraphrase)". Treat all of it as second-hand until someone can open the user
guide PDF.

## Queries run

Round 1:
1. `Kinova Gen3 user guide pdf DH parameters 7 DOF` (standard)
2. `Kinova Gen3 technical specifications pdf joint range torque mass reach` (standard)
3. `"Gen3" Kinova "Denavit-Hartenberg" "7 DoF" table alpha "0.2848" OR "-(0.1564 + 0.1284)"` (standard)
4. `Kinova Gen3 user guide "Classic DH parameters" 7 DoF spherical wrist` (standard)
5. `Kinova Gen3 7 DoF classic DH parameters table alpha a d theta user guide values ...` (extended)
6. `Kinova Gen3 "7 DoF spherical wrist robot geometric parameters" upper arm forearm wrist mm` (extended)
7. `Kinova Gen3 user guide "Denavit-Hartenberg" "7 DoF spherical wrist" table "d (m)" "theta" "alpha" "a (m)" ...` (extended)
8. `manualslib Kinova Gen3 "Denavit-Hartenberg (DH) Parameters - 7 Dof Spherical Wrist" page 141 alpha a d theta` (extended)
9. `Kinova Gen3 7-DOF DH table paper "π" "-(0.1564+0.1284)" OR "0.2848" ...` (extended)
10. `Kinova Gen3 7-DoF Denavit-Hartenberg table paper d1 0.2848 d3 0.4208 ...` (extended)
11. `Kinova Gen3 7DOF specifications weight 8.2 kg reach 902 mm payload repeatability joint speed ...` (extended)
12. `Kinova Gen3 7 DoF joint range limits actuator 2 4 6 ... degrees user guide` (extended)
13. `Kinova Gen3 actuators large small maximum speed degrees per second peak torque Nm continuous torque user guide` (extended)
14. `"Gen3" Kinova DH parameters "Base to actuator 1" "Actuator 7 to interface module" ...` (extended)
15. `"D.H. parameters for Kinova Gen3 arm" researchgate table` (standard)
16. `Kinova Gen3 one pager specifications "Maximum reach" "Total weight" "Payload" "Repeatability" 7 DoF` (standard)

Round 2 (coordinator-requested focused retry for the DH table and zero-pose axes):
17. `Kinova Gen3 inverse kinematics DH table 7-DOF thesis "0.2104" "0.2084" alpha π/2 d1 -(0.1564+0.1284)` (extended)
18. `Kinova Gen3 7-DOF Denavit-Hartenberg parameters table MDPI OR IEEE OR arXiv "Kinova Gen3" "DH parameters" joint axes zero configuration` (extended)
19. `"Kinematices, Dynamics and Controls of Kinova Gen3 Robotic Arm" DH table alpha a d theta values` (extended)
20. `Kinova Gen3 classic DH parameters "-0.0054" "-0.2104" "-0.0064" "-0.2084" "-0.1059" "-0.1674" table` (extended)
21. `Kinova Gen3 7 DoF zero position arm vertical "all joints at 0" straight up candle configuration joint axes user guide homogeneous transform matrices` (extended)

Note: queries 3, 9, 10, 17 and 20 contain numbers I typed as search bait; they are NOT
evidence. No search result reproduced any of them as a DH entry, and none is recorded
below as a DH value.

---

## 1. Kinova Gen3 User Guide (R07), official PDF

- URL: https://www.kinovarobotics.com/uploads/User-Guide-Gen3-R07.pdf
- Status: primary (manufacturer). **Could not open (proxy refused).** Search excerpts only.
- Excerpts (table-of-contents lines and figure captions only):
  - "Denavit-Hartenberg (DH) parameters - 7 DoF spherical wrist" (page number reported
    differently between copies: 141, 163, 197)
  - "Schematic and dimensions - 7 DoF spherical wrist ... 61"
  - "Homogeneous transform matrices - 7 DoF spherical wrist"
  - Figure caption (via search excerpt): "Figure 70: Frame definitions and dimensions (all
    joints at 0 position, dimensions in mm)"; and a figure that "defines reference frames
    for the base, joints (when all joint angles = 0) and end effector".
- Actuator figures (paraphrase of the search tool, attributed to R07): large actuators
  unloaded max speed 13 RPM, small 25 RPM; nominal torque large 32 N·m (robots built
  before 2022-09) / 39 N·m (later builds), small 13 N·m; peak torque large 54 N·m, small
  34 N·m. **Paraphrase, not a quote; do not use until verified in the PDF.**
- The DH table values, the base-to-frame-0 transform and the frame-7-to-interface transform
  were **not** returned by any search (21 queries).

## 2. Kinova Gen3 User Guide, third-party mirror on Scribd ("Gen 3")

- URL: https://www.scribd.com/document/624143328/gen3
- Status: second-hand (user upload of the Kinova user guide), search excerpt only.
- Table 9 "7 DoF spherical wrist robot geometric parameters", column "Description Length (mm)"
  (paraphrase of the search tool; individual numbers as returned, unit mm):
  - Base to actuator 1: 156.4
  - Base to shoulder (joint 2 axis): 284.8
  - Joint 1-2 offset: 5.4
  - Joint 2-3 offset: 6.4
  - Upper arm: two half-segments, each 210.4
  - Forearm (elbow to wrist): 208.4
  - Wrist: two segments, each 105.9
  - Last actuator to end effector (interface module): 61.5
  - Verbatim fragment: "[the] diagram also indicates the link lengths and lateral offset
    values (measurements in mm)"
- Note: the excerpt did not give row labels verbatim, which segments the offsets apply to
  (sign/direction), or the pose of the drawing. Mapping these to joints needs the drawing.
  Consistency check (my arithmetic, not a source): 284.8 - 156.4 = 128.4 (J1 to J2);
  210.4 + 210.4 + 208.4 + 105.9 + 105.9 + 61.5 = 902.5 mm, which matches the rated reach
  902 mm measured from the actuator 2 frame (section 4), so the length set is plausible.
- Table 10 "Joint limits - 7 DoF spherical wrist" (paraphrase; values as returned, deg):
  - Actuator 1: no limit (continuous)
  - Actuator 2: ±126
  - Actuator 3: no limit (continuous)
  - Actuator 4: ±147
  - Actuator 5: no limit (continuous)
  - Actuator 6: ±117
  - Actuator 7: no limit (continuous)
  - Verbatim fragment: "for joints 2, 4 and 6 there are physical limits to how far the
    joint can turn without the arm shell segments running into each other. The robot
    enforces software joint angle limits to prevent these joints from reaching the
    physical limits."
  - Round 2 query 18 returned the same limits again from this copy ("joints 1, 3, 5, and 7
    are unlimited, and joints 2, 4, and 6 are limited to ±126°, ±147°, and ±117°", paraphrase).

## 3. Kinova Gen3 User Manual, ManualsLib mirror

- URL: https://www.manualslib.com/manual/1529186/Kinova-Gen3.html (page 49:
  https://www.manualslib.com/manual/1529186/Kinova-Gen3.html?page=49)
- Status: second-hand mirror, could not open (proxy refused). Excerpts only:
  - Page 49 title: "Technical Specifications"; contains "Table 9: 7 DoF spherical wrist
    robot geometric parameters".
  - Round 2 (query 20): the page-49 excerpt lists 7 DoF geometric lengths in mm "such as
    156.4, 284.8, and 210.4, with joint offsets of 5.4 and 6.4" (paraphrase). This is a
    second, independent copy agreeing with the Scribd values for those five numbers.
  - "Denavit-Hartenberg (DH) Parameters - 7 Dof Spherical Wrist 141"
  - Page 137: "Standard Robot Frames; Dynamic Parameters Of The 7 Dof Robot"
  - Table 10 joint limits as in section 2 (search tool attributed them to both Scribd and
    ManualsLib copies).

## 4. Kinova Gen3 User Manual, manualmachine mirror

- URL: https://manualmachine.com/kinova/gen3/2576994-user-manual/
- Status: second-hand mirror, search excerpt only.
- Base to actuator 1: 156.4 mm; last actuator to end effector: 61.5 mm (paraphrase;
  agrees with section 2).
- Reach definition (paraphrase, not verbatim): the maximum reach is measured from the
  actuator 2 frame to the interface module frame; the tool transform is defined relative to
  the interface module frame.

## 5. Kinova Gen3 one-pager (2024 EN), official

- URL: https://www.kinovarobotics.com/uploads/Kinova_Onepager_Gen3_2024_EN.pdf
  (2026 edition: https://www.kinovarobotics.com/uploads/Kinova_Onepager_Gen3_2026_EN.pdf)
- Status: primary (manufacturer), could not open; search excerpt with verbatim row fragments
  (columns 6 DoF | 7 DoF):
  - "Total weight 7.2 kg 8.2 kg"
  - "Maximum reach 891 mm 902 mm"
  - "Payload* (full-range continuous)** 2.0 kg 2.0 kg (mid-range continuous) 4.0 kg 4.0 kg"
  - Max Cartesian speed 50 cm/s (paraphrase)
  - "Actuator joint range after start-up. Infinite. (software limitation)" (quoted from the
    product page / one-pager per the search tool)
  - Operating temperature -30 °C to 35 °C, IP33 (paraphrase, 2026 edition)
  - Repeatability: not in excerpt.

## 6. Gen3 Specifications R01 (Kinova spec sheet, hosted by Hot Robotics)

- URL: https://hotrobotics.co.uk/wp-content/uploads/2021/07/Gen3-Specifications-R01.pdf
- Status: second-hand host of a manufacturer document; search excerpt only.
- Total weight 8.2 kg (no gripper); mid-range continuous payload 4 kg (no gripper);
  max Cartesian translation speed 30 cm/s in high-level mode (paraphrase). Older document
  than the one-pager (see Conflicts).

## 7. Papers / third-party pages that mention a Gen3 DH table (none usable)

- http://www.coep.ufrj.br/~fernando/downloads/cep2021-parameterization.pdf : Control
  Engineering Practice submission with a "Denavit-Hartenberg standard parameter table for
  Kinova Gen3" (Table 2). Its d7 includes the distance to a QR-code centroid ("Parameter d7
  includes the distance to the QR-code centroid"), so it is not a bare-arm table. The search
  tool gave only rounded paraphrased values (roughly 0.285, -0.42, -0.31, -0.36 m; alpha
  "π/2 for most joints and π for the base and last link"). **Garbled: rows, exact values and
  signs not intact. Not transcribed.**
- https://arxiv.org/pdf/2601.15459 : "Table 2: Denavit-Hartenberg (DH) parameters for Kinova
  Gen3 7-DOF robotic arm."; "The coordinate frames for each joint were defined according to
  the Kinova Gen3 Ultra Lightweight Robot User Guide." Values not in any excerpt. Second-hand,
  not transcribed.
- https://arxiv.org/pdf/2508.07323 : uses modified DH for the Gen3; no numeric table in excerpt.
- https://www.researchgate.net/figure/DH-parameters-for-Kinova-Gen3-arm_tbl1_348060270 :
  caption "D.H. parameters for Kinova Gen3 arm." only; values not in excerpt.
- https://www.academia.edu/123677435/Kinematices_Dynamics_and_Controls_of_Kinova_Gen3_Robotic_Arm :
  describes DH-based FK/IK for the Gen3 7-DoF; table not in excerpt.
- https://arxiv.org/pdf/2102.01217 and https://link.springer.com/chapter/10.1007/978-981-19-1983-1_10 :
  Gen3 **Lite** (different 6-DoF robot). Not used.
- Also seen in results but deliberately not opened or used: GitHub code repos implementing
  Gen3 FK and pages pointing at the kortex_description URDF (robot-description sources are
  forbidden).

## 8. Third-party listings (not used)

- https://qviro.com/product/kinova/gen3/specifications : repeatability "0.1 mm" (third-party)
- other resellers: repeatability 1.0 mm; payload 4.5 kg peak at full reach, 1.1 kg full
  reach continuous (paraphrase, third-party). Unverified; not recommended.

---

Kinematic source: dimension/length table (Table 9 "7 DoF spherical wrist robot geometric
parameters" of the Kinova Gen3 User Guide), known only from search excerpts of two
second-hand mirrors that agree (https://www.scribd.com/document/624143328/gen3 and
https://www.manualslib.com/manual/1529186/Kinova-Gen3.html?page=49; partial agreement also
from https://manualmachine.com/kinova/gen3/2576994-user-manual/). The official DH table
(user guide section "Denavit-Hartenberg (DH) parameters - 7 DoF spherical wrist",
https://www.kinovarobotics.com/uploads/User-Guide-Gen3-R07.pdf) exists but could not be read,
and no paper excerpt reproduced it intact. Joint-to-length mapping, offset directions, axis
directions and the zero pose are therefore inferences (class: dimension table with inferred
mapping).

Conflicts:
- Joint limits for actuators 2/4/6 (±126/±147/±117 deg, user guide Table 10) vs the
  one-pager's "Infinite (software limitation)": the one-pager refers to the continuous
  joints / general actuator capability; use Table 10 for joints 2, 4, 6.
- Max Cartesian speed 50 cm/s (one-pager 2024) vs 30 cm/s high-level (Specifications R01):
  use the newer one-pager.
- Large-actuator peak torque 54 N·m (R07, paraphrase) vs 74 N·m (other section / third
  party); nominal 32 vs 39 N·m depending on build date. Unverified either way; omit or treat
  as estimates.
- Large-actuator speed 13 RPM (R07) vs 17 RPM (older manual), paraphrase only.
- Repeatability 0.1 mm vs 1.0 mm (third parties only): do not use.

Not found:
- The DH table rows (alpha, a, d, theta offsets), the base-to-frame-0 transform and the
  frame-7-to-interface-module transform (section exists; content not retrievable through
  search, fetch blocked).
- Zero-pose joint axis directions (the guide has a zero-pose frame figure, Figure 70, but its
  content was not in any excerpt).
- Verbatim table rows for Table 9 / Table 10 (only search-tool paraphrase with numbers).
- Drawing cross-check dimensions at a stated pose (e.g. flange height at zero pose).
- Repeatability from a Kinova document.
- Verified per-joint speed and torque limits; link masses; housing diameters.
