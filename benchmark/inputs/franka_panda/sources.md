# Franka Emika Panda (FER): sources

Accessed 2026-11-05.

**How these were retrieved.** Direct page fetches to frankaemika.github.io /
frankarobotics.github.io were blocked by this session's network policy, so all
values come from web-search extracts of the cited pages. Quotes are reproduced
as returned. Re-check against the live pages when network access allows.

## 1. Franka Control Interface (FCI) docs: Control Interface Specification and Robot Limits

https://frankarobotics.github.io/docs/robot_specifications.html
(successor of https://frankaemika.github.io/docs/control_parameters.html, which the Panda dynamic-identification
paper below cites as the place for the Panda joint position bounds)

DH table, extract: "The Denavit–Hartenberg parameters for the Franka Research 3 kinematic chain (following Craig's
convention) are shown below". Columns: `a (m) | d (m) | α (rad) | θ (rad)`; θ column is the joint variable θ1..θ7;
the table ends with a "Flange" row: "a = 0, d = 0.107 m, α = 0, θ = 0".
Values extracted across three queries:
- "d1 = 0.333", "d3 = 0.316", "d5 = 0.384"; "a = 0.0825 m at joints 4 and −0.0825 m at joint 5, and a = 0.088 m at joint 7".
- alpha column: "0, -π/2, π/2, π/2, -π/2, π/2" for joints 1-6 (joint 7 cut off in that extract).

The current page states the table for FR3; the older page (control_parameters.html) gave the same table for the
Panda. The Panda-specific source for row 7 (alpha) is the paper in section 2.

FER joint-space limits, extract of the "Limits for Franka Emika Robot (FER)" table:
- velocity: "2.1750 rad/s for joints 1–4 and 2.6100 rad/s for joints 5–7"
- torque: "joints 1–4 have a torque limit of 87 Nm, and joints 5–7 have 12 Nm"
- torque rate: "1000 Nm/s for every joint"
- note: "the maximum joint velocity depends on joint position and motion direction"

## 2. Gaz, Cognetti, Oliva, Robuffo Giordano, De Luca: Dynamic Identification of the Franka Emika Panda Robot (RA-L 2019)

https://www.diag.uniroma1.it/~labrob/pub/papers/RAL_2019_PandaDynamicModel_PreprintXplore.pdf

"The reference frames follow the modified Denavit-Hartenberg convention." Table row extract:
"| 7 | a 7 | π/2 | 0 | q 7 |" (columns i | a_i | α_i | d_i | θ_i), figure notes
"d 1 = 0.333 m, d 3 = 0.316 m, d 5 = 0.384 m, d f = 0.107 m, a 4 = 0.0825 m, a 5 = −0.0825 m, a 7 = 0.088 m".

## 3. Panda datasheet (Franka Emika, May 2019)

https://www.generationrobots.com/media/Panda_Datasheet_May_2019.pdf
(also https://www.wiredworkers.io/wp-content/uploads/2019/12/Panda_FrankaEmika_ENG.pdf,
https://www.generationrobots.com/media/panda-franka-emika-datasheet.pdf)

- "Maximum reach 855 mm"; payload 3 kg; "Degrees of freedom 7"
- Pose repeatability "<+/- 0.1 mm" (ISO 9283)
- Joint position limits (deg): "A1, A3, A5 and A7 ... ±166°", "A2 ±101°", "A4 −176° to −4°", "A6 −1° to 215°"
  (extract; matches the rad values 2.8973, 1.7628, -3.0718/-0.0698, -0.0175/3.7525)
- Joint velocity limits: "A1–A4 at 150°/s", "A5–A7 at 180°/s" (one datasheet version; another 2019-2020 Franka
  sheet extract only showed the A1–A4 figure)
- Weight: "~17.8 kg" (datasheet copy https://centers.ulbsibiu.ro/incon/wp-content/uploads/Datasheet-Franka-Emika-Panda-Research-collaborative-robot.pdf)

## 4. Panda user handbook

https://www.manualslib.com/manual/2575639/Franka-Emika-Panda.html?page=42
- "7 degrees of freedom", payload "3 kg", arm weight "approx. 18 kg" (extract).
