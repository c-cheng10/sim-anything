# UR5e: sources used

Accessed 2026-11-05. Direct fetches of universal-robots.com are blocked from this environment; all
values come from web-search extracts of the cited pages (pre-gathered in `benchmark/inputs/ur5e/`,
plus one search of my own for the torque mapping). Quotes as returned by the search tool.

## 1. UR support article: DH parameters for calculations of kinematics and dynamics (primary)

https://www.universal-robots.com/articles/ur/application-installation/dh-parameters-for-calculations-of-kinematics-and-dynamics/

Columns: `a [m] | d [m] | alpha [rad] | Mass [kg] | Center of Mass [m] | Inertia`. Standard DH, theta_i = q_i.

| Joint | a [m] | d [m] | alpha [rad] | mass [kg] | CoM [m] |
|---|---|---|---|---|---|
| 1 | 0 | 0.1625 | π/2 | 3.761 | [0, -0.02561, 0.00193] |
| 2 | -0.425 | 0 | 0 | 8.058 | [0.2125, 0, 0.11336] |
| 3 | -0.3922 | 0 | 0 | 2.846 | (not extracted) |
| 4 | 0 | 0.1333 | π/2 | 1.37 | (not extracted) |
| 5 | 0 | 0.0997 | -π/2 | 1.3 | [0, 0.0018, 0.01634] |
| 6 | 0 | 0.0996 | 0 | 0.365 | (not extracted) |

FAQ extract: "the mass vector [x, y, z]^T is an offset from the given joint frame for each corresponding link".
Used for: `joints[*].dh` (m -> mm, rad -> deg), `joints[*].link.mass`, `joints[*].link.com` (m -> mm).

## 2. UR5e datasheet 08/2023 (primary)

https://www.universal-robots.com/media/1807465/ur5e_e-series_datasheets_web.pdf

- Drawing labels: "162.5 425 392.2 99,7 133 494,9 R850 149" (consistent with the DH table in mm).
- "Payload 5 kg", "Reach 850 mm", weight "20.6 kg" (incl. cable), footprint "Ø149 mm".
Used for: `payload`, `reach.value`, `total_mass`; footprint informs the (estimated) base radius.

## 3. UR5e techsheet (primary)

https://www.universal-robots.com/manuals/EN/TechSheets/UR5e_techsheet_pdf_online/UR5e_techsheet_en.pdf

- Every joint (base, shoulder, elbow, wrist 1-3): working range "±360°", maximum speed "±180°/s".
- Pose repeatability "±0.03 mm" per ISO 9283. Footprint "Ø151 mm" (conflicts with datasheet Ø149).
Used for: `joints[*].limits`, `joints[*].velocity_limit`, `repeatability`.

## 4. UR5e user manual SW 5.19 (primary, context only)

https://www.universal-robots.com/manuals/EN/PDF/SW5_19/user-manual-UR5e-PDF_online/710-965-00_UR5e_User_Manual_en_Global.pdf

- Weight "20.7 kg" (conflict with datasheet 20.6 kg; datasheet used).
- Working area: cylindrical volume "850 mm" from the base joint. Basis for the (estimated) reach definition.

## 5. UR article: Max. joint torques CB3 and e-Series (primary, via search extract)

https://www.universal-robots.com/articles/ur/robot-care-maintenance/max-joint-torques-cb3-and-e-series/

- "Size 0 · 9 Nm, Size 1 · 28 Nm, Size 2 · 54 Nm, Size 3 · 150 Nm, Size 4 · 330 Nm".
- Search extract (2026-11-05): the UR5/UR5e/UR7e column assigns size 3 to base, shoulder and elbow and
  size 1 to wrist 1, wrist 2 and wrist 3. The article says these belong to the joint itself and cannot
  all be used in an application.
- Agreeing secondary source: https://forum.universal-robots.com/t/maximum-axis-speed-acceleration/13338
  (UR5e base/shoulder/elbow 150 Nm, wrists 28 Nm).
Used for: `joints[*].effort_limit` (150, 150, 150, 28, 28, 28).
