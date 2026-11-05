# Franka Emika Panda (FER, arm without hand): sources used

Accessed 2026-11-05. Direct fetches of the Franka doc hosts are blocked from this environment; all
values come from web-search extracts of the cited pages (pre-gathered in `benchmark/inputs/franka_panda/`).
Quotes as returned by the search tool.

## 1. Franka Control Interface docs: robot specifications / limits (primary)

https://frankarobotics.github.io/docs/robot_specifications.html
(successor of https://frankaemika.github.io/docs/control_parameters.html)

- "The Denavit–Hartenberg parameters for the Franka Research 3 kinematic chain (following Craig's
  convention) are shown below". Columns `a (m) | d (m) | α (rad) | θ (rad)`, θ = joint variable.
- "d1 = 0.333", "d3 = 0.316", "d5 = 0.384"; "a = 0.0825 m at joints 4 and −0.0825 m at joint 5, and
  a = 0.088 m at joint 7".
- alpha, joints 1-6: "0, -π/2, π/2, π/2, -π/2, π/2".
- Flange row: "a = 0, d = 0.107 m, α = 0, θ = 0".
- FER limits: torque "joints 1–4 have a torque limit of 87 Nm, and joints 5–7 have 12 Nm"; velocity
  "2.1750 rad/s for joints 1–4 and 2.6100 rad/s for joints 5–7" (not used; see datasheet).

Used for: `joints[*].dh` (m -> mm, rad -> deg), `ee.origin` (flange row), `joints[*].effort_limit`.

## 2. Gaz et al., Dynamic Identification of the Franka Emika Panda Robot, RA-L 2019 (peer-reviewed)

https://www.diag.uniroma1.it/~labrob/pub/papers/RAL_2019_PandaDynamicModel_PreprintXplore.pdf

- "The reference frames follow the modified Denavit-Hartenberg convention."
- Row "| 7 | a 7 | π/2 | 0 | q 7 |"; "d 1 = 0.333 m, d 3 = 0.316 m, d 5 = 0.384 m, d f = 0.107 m,
  a 4 = 0.0825 m, a 5 = −0.0825 m, a 7 = 0.088 m".

Used for: `joints[6].dh.alpha` (π/2 -> 90 deg); confirms the rest of the table for the Panda.

## 3. Panda datasheet, Franka Emika, May 2019 (second-hand: reseller copy)

https://www.generationrobots.com/media/Panda_Datasheet_May_2019.pdf

- "Degrees of freedom 7"; payload "3 kg"; "Maximum reach 855 mm"; pose repeatability "<+/- 0.1 mm".
- Joint position limits: "A1, A3, A5 and A7 ... ±166°", "A2 ±101°", "A4 −176° to −4°", "A6 −1° to 215°".
- Joint velocity limits: "A1–A4 at 150°/s", "A5–A7 at 180°/s" (A5-A7 seen in one datasheet version only).

Used for: `joints[*].limits`, `joints[*].velocity_limit`, `payload`, `reach.value`, `repeatability`.

## 4. Panda datasheet copy (second-hand: university-hosted copy)

https://centers.ulbsibiu.ro/incon/wp-content/uploads/Datasheet-Franka-Emika-Panda-Research-collaborative-robot.pdf

- Weight "~17.8 kg". Used for `total_mass`.

## 5. Panda user handbook (context only)

https://www.manualslib.com/manual/2575639/Franka-Emika-Panda.html?page=42

- "7 degrees of freedom", payload "3 kg", arm weight "approx. 18 kg" (agrees with ~17.8 kg).
