# UR5e sources (round2)

Accessed 2026-11-05. universal-robots.com could not be fetched directly from this environment; every value is from
web-search extracts, as gathered in `benchmark/inputs/ur5e/sources.md` (quotes reproduced from there) plus one
confirming search on 2026-11-05.

## DH table and link dynamics (primary, manufacturer support article)
https://www.universal-robots.com/articles/ur/application-installation/dh-parameters-for-calculations-of-kinematics-and-dynamics/

Columns as published: `a [m] | d [m] | alpha [rad] | Dynamics: Mass [kg] | Center of Mass [m] | Inertia Matrix`;
table header "UR5e/UR7e Kinematics a [m] d [m] alpha [rad]" (confirmed in a 2026-11-05 search, which also showed
"d = 0.1625 m, alpha = π/2" for joint 1 and "a = -0.425 m" for joint 2).

| Joint | a [m] | d [m] | alpha [rad] | Mass [kg] |
|---|---|---|---|---|
| 1 | 0 | 0.1625 | π/2 | 3.761 |
| 2 | -0.425 | 0 | 0 | 8.058 |
| 3 | -0.3922 | 0 | 0 | 2.846 |
| 4 | 0 | 0.1333 | π/2 | 1.37 |
| 5 | 0 | 0.0997 | -π/2 | 1.3 |
| 6 | 0 | 0.0996 | 0 | 0.365 |

Used: every row verbatim (alpha π/2 -> 90 deg); masses as `joints[*].link.mass`.
Centres of mass (extract): link 1 `[0, -0.02561, 0.00193]`, link 2 `[0.2125, 0, 0.11336]`, link 5 `[0, 0.0018, 0.01634]`;
"the mass vector [x, y, z]^T is an offset from the given joint frame for each corresponding link".

## Datasheet 08/2023 (primary)
https://www.universal-robots.com/media/1807465/ur5e_e-series_datasheets_web.pdf
- Drawing labels: "162.5 425 392.2 99,7 133 494,9 R850 149" (cross-check of d1, a2, a3, d5, d4).
- "Payload 5 kg", "Reach 850 mm", weight "20.6 kg" (including cable), footprint "Ø149 mm".
Used: payload 5, total_mass 20.6, reach 0.85 m, base radius estimate from Ø149.

## Techsheet (primary)
https://www.universal-robots.com/manuals/EN/TechSheets/UR5e_techsheet_pdf_online/UR5e_techsheet_en.pdf
- Every joint (base, shoulder, elbow, wrist 1-3): working range "±360°", maximum speed "±180°/s".
- Pose repeatability "±0.03 mm" per ISO 9283. Footprint "Ø151 mm" (conflicts with datasheet Ø149).
Used: limits ±360, velocity_limit 180, repeatability 0.03.

## User manual SW 5.19 (primary)
https://www.universal-robots.com/manuals/EN/PDF/SW5_19/user-manual-UR5e-PDF_online/710-965-00_UR5e_User_Manual_en_Global.pdf
- Working area: cylindrical volume above and below the base, "850 mm" from the base joint. Weight "20.7 kg".
Used: reach.measured_from = base_axis_horizontal.

## Joint torques
https://www.universal-robots.com/articles/ur/robot-care-maintenance/max-joint-torques-cb3-and-e-series/ (primary)
- "Size 0 · 9 Nm, Size 1 · 28 Nm, Size 2 · 54 Nm, Size 3 · 150 Nm, Size 4 · 330 Nm"; Wrist 2 and Wrist 3 Size 1 for UR5/UR5e.
https://forum.universal-robots.com/t/maximum-axis-speed-acceleration/13338 (SECOND-HAND, forum post)
- UR5e base/shoulder/elbow 150 Nm, wrists 28 Nm; values "that will potentially cause physical damage to the joints".
Used: effort_limit 150/150/150/28/28/28 (joints 1-4 second-hand).

## Not found
Housing / link outer diameters (only footprint), CoMs of links 3/4/6, an explicit statement whether the 850 mm reach
ends at the flange or the wrist (a third-party site says "base axis to the wrist"; not used, not primary).
