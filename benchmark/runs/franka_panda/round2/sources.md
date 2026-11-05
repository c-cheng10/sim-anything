# Franka Emika Panda (FER) sources (round2)

Accessed 2026-11-05. The Franka docs hosts could not be fetched directly from this environment; values are from
web-search extracts as gathered in `benchmark/inputs/franka_panda/sources.md` (quotes reproduced from there).

## FCI docs: Control Interface Specification and Robot Limits (primary, manufacturer)
https://frankarobotics.github.io/docs/robot_specifications.html
(successor of https://frankaemika.github.io/docs/control_parameters.html, which gave the same table for the Panda)

- "The Denavit–Hartenberg parameters for the Franka Research 3 kinematic chain (following Craig's convention) are
  shown below". Columns `a (m) | d (m) | α (rad) | θ (rad)`.
- "d1 = 0.333", "d3 = 0.316", "d5 = 0.384"; "a = 0.0825 m at joints 4 and −0.0825 m at joint 5, and a = 0.088 m at
  joint 7"; alpha "0, -π/2, π/2, π/2, -π/2, π/2" for joints 1-6.
- "Flange" row: "a = 0, d = 0.107 m, α = 0, θ = 0".
- FER limits: torque "joints 1–4 have a torque limit of 87 Nm, and joints 5–7 have 12 Nm"; velocity
  "2.1750 rad/s for joints 1–4 and 2.6100 rad/s for joints 5–7" (not used; datasheet deg/s used instead).

Used: `joints[*].dh` (rows 1-7), `ee.origin` = [0, 0, 0.107], `joints[*].effort_limit` 87/12.

## Gaz et al., Dynamic Identification of the Franka Emika Panda Robot, RA-L 2019 (peer-reviewed, quotes manufacturer)
https://www.diag.uniroma1.it/~labrob/pub/papers/RAL_2019_PandaDynamicModel_PreprintXplore.pdf
- "The reference frames follow the modified Denavit-Hartenberg convention."
- Row "| 7 | a 7 | π/2 | 0 | q 7 |"; "d 1 = 0.333 m, d 3 = 0.316 m, d 5 = 0.384 m, d f = 0.107 m, a 4 = 0.0825 m,
  a 5 = −0.0825 m, a 7 = 0.088 m".
Used: `joints[6].dh.alpha` = 90; cross-check of all lengths.

## Panda datasheet, May 2019 (manufacturer document; reseller-hosted copy = second-hand host)
https://www.generationrobots.com/media/Panda_Datasheet_May_2019.pdf
- "Maximum reach 855 mm"; payload 3 kg; "Degrees of freedom 7"; repeatability "<+/- 0.1 mm" (ISO 9283).
- Joint ranges: "A1, A3, A5 and A7 ... ±166°", "A2 ±101°", "A4 −176° to −4°", "A6 −1° to 215°".
- Speeds: "A1–A4 at 150°/s", "A5–A7 at 180°/s" (the 180°/s value seen in one datasheet version only).
Used: limits, velocity_limit, payload, repeatability, reach.value.

## Datasheet copy with weight (university-hosted copy = second-hand host)
https://centers.ulbsibiu.ro/incon/wp-content/uploads/Datasheet-Franka-Emika-Panda-Research-collaborative-robot.pdf
- Weight "~17.8 kg". (Handbook, https://www.manualslib.com/manual/2575639/Franka-Emika-Panda.html?page=42:
  "approx. 18 kg".)
Used: total_mass 17.8.

## Not found
Link masses/CoMs from the manufacturer, housing diameters, the reference points of the 855 mm reach, an official
home/"ready" pose (the one used is an estimate).
