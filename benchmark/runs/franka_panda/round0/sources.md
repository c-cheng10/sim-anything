# Franka Emika Panda (FER, arm only): sources used

Accessed 2026-11-05. Sections 1-4 come from the pre-gathered `benchmark/inputs/franka_panda/sources.md`
(web-search extracts; direct fetches of the Franka docs hosts are blocked from this environment, re-confirmed
this session: frankaemika.github.io does not resolve). Section 5 was fetched directly this session.

## 1. FCI docs, "Robot and interface specifications" (DH table, torque limits)

https://frankarobotics.github.io/docs/robot_specifications.html
(predecessor page https://frankaemika.github.io/docs/control_parameters.html gave the same table for the Panda)

- "The Denavit–Hartenberg parameters for the Franka Research 3 kinematic chain (following Craig's convention)"
  -> `convention: dh_modified`. Columns `a (m) | d (m) | α (rad) | θ (rad)`, θ = θ1..θ7 (no offsets).
- "d1 = 0.333", "d3 = 0.316", "d5 = 0.384" -> joints[0].dh.d, joints[2].dh.d, joints[4].dh.d
- "a = 0.0825 m at joints 4 and −0.0825 m at joint 5, and a = 0.088 m at joint 7" -> joints[3/4/6].dh.a
- alpha column "0, -π/2, π/2, π/2, -π/2, π/2" (joints 1-6) -> 0, -90, 90, 90, -90, 90 deg
- Flange row: "a = 0, d = 0.107 m, α = 0, θ = 0" -> `ee.origin.xyz: [0, 0, 0.107]`
- "joints 1–4 have a torque limit of 87 Nm, and joints 5–7 have 12 Nm" -> effort_limit
- (velocity, not used as spec value but consistent: "2.1750 rad/s for joints 1–4 and 2.6100 rad/s for joints 5–7")

## 2. Gaz et al., Dynamic Identification of the Franka Emika Panda Robot, RA-L 2019

https://www.diag.uniroma1.it/~labrob/pub/papers/RAL_2019_PandaDynamicModel_PreprintXplore.pdf

- "The reference frames follow the modified Denavit-Hartenberg convention."
- Row 7: "| 7 | a 7 | π/2 | 0 | q 7 |" -> joints[6].dh alpha = 90 deg, d = 0
- "d 1 = 0.333 m, d 3 = 0.316 m, d 5 = 0.384 m, d f = 0.107 m, a 4 = 0.0825 m, a 5 = −0.0825 m, a 7 = 0.088 m"
  (confirms the Panda-specific table)

## 3. Panda datasheet (Franka Emika, May 2019)

https://www.generationrobots.com/media/Panda_Datasheet_May_2019.pdf

- Joint limits: "A1, A3, A5 and A7 ... ±166°", "A2 ±101°", "A4 −176° to −4°", "A6 −1° to 215°" -> limits
- "A1–A4 at 150°/s", "A5–A7 at 180°/s" -> velocity_limit (deg/s)
- "Maximum reach 855 mm" -> reach 0.855 m (reference points not stated; shoulder -> flange is my interpretation)
- payload "3 kg" -> payload
- Pose repeatability "<+/- 0.1 mm" (ISO 9283) -> repeatability 0.0001 m

Weight, datasheet copy:
https://centers.ulbsibiu.ro/incon/wp-content/uploads/Datasheet-Franka-Emika-Panda-Research-collaborative-robot.pdf
- "~17.8 kg" -> total_mass 17.8

## 4. Panda user handbook (cross-check only)

https://www.manualslib.com/manual/2575639/Franka-Emika-Panda.html?page=42
- "7 degrees of freedom", payload "3 kg", weight "approx. 18 kg" (conflicts slightly with 17.8; datasheet used)

## 5. libfranka example (home pose)

https://raw.githubusercontent.com/frankaemika/libfranka/master/examples/generate_joint_position_motion.cpp
(fetched 2026-11-05; Franka's control library, not a robot-description file)

- line 28: `std::array<double, 7> q_goal = {{0, -M_PI_4, 0, -3 * M_PI_4, 0, M_PI_2, M_PI_4}};`
  -> home [0, -45, 0, -135, 0, 90, 45] deg
