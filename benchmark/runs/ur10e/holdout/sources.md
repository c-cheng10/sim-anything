# UR10e sources (holdout run)

Accessed 2026-11-05. universal-robots.com (and the third-party PDF mirrors tried) could not be fetched from this
environment (DNS blocked), so all values come from web-search extracts, as pre-gathered in
`benchmark/inputs/ur10e/sources.md` / `facts.yaml`, plus one confirming web search made in this run.

## 1. UR support article: DH parameters for calculations of kinematics and dynamics (primary)

https://www.universal-robots.com/articles/ur/application-installation/dh-parameters-for-calculations-of-kinematics-and-dynamics/
(same UR10e data on https://www.universal-robots.com/developer/hardware-and-motion/robot-motion-dh-parameters/)

Columns `a [m] | d [m] | alpha [rad] | Mass [kg] | Center of Mass [m] | Inertia Matrix`, section "UR10e/UR12e",
standard DH, theta_i = q_i. Extract: "d1 = 0.1807 m, a2 = -0.6127 m, a3 = -0.57155 m, d4 = 0.17415 m, d5 = 0.11985 m,
and d6 = 0.11655 m, with the same alpha pattern as the UR5e" (alpha = π/2, 0, 0, π/2, -π/2, 0).

| Joint | a [m] | d [m] | alpha [rad] | used as |
|---|---|---|---|---|
| 1 | 0 | 0.1807 | π/2 | joints[0].dh (alpha 90 deg) |
| 2 | -0.6127 | 0 | 0 | joints[1].dh |
| 3 | -0.57155 | 0 | 0 | joints[2].dh |
| 4 | 0 | 0.17415 | π/2 | joints[3].dh (alpha 90 deg) |
| 5 | 0 | 0.11985 | -π/2 | joints[4].dh (alpha -90 deg) |
| 6 | 0 | 0.11655 | 0 | joints[5].dh (flange) |

Link masses (developer page extract): "Link 1 | 7.369; Link 2 | 13.051; Link 3 | 3.989; Link 4 | 2.1; Link 5 | 1.98;
Link 6 | 0.615" -> joints[i].link.mass.

## 2. UR10e datasheet (08/2023), drawing labels (cross-check only)

https://www.universal-robots.com/media/1807466/ur10e_e-series_datasheets_web.pdf
"08/2023 180.7 612.7 571.55 119.85 174.15 691.4 R1300 190 UR10e Specification" -> agrees with d1, a2, a3, d5, d4 (mm);
R1300 working-area radius; 190 = footprint diameter.

## 3. UR10e techsheet

https://www.universal-robots.com/manuals/EN/TechSheets/UR10e_techsheet_pdf_online/UR10e_techsheet_en.pdf
- "Payload 12.5 kg (27.5 lbs) Reach 1300 mm (51.2 in)" -> payload, reach.value
- Working range "±360°" for every joint -> joints[*].limits
- "120°/s for base and shoulder and 180°/s for elbow and the three wrist joints" -> joints[*].velocity_limit
- Repeatability "±0.05 mm" (ISO 9283) -> repeatability (0.00005 m)
- Footprint "Ø190 mm" -> base cylinder radius 0.095 m (listed as estimate: mapping footprint to collision cylinder)

Confirming web search (2026-11-05, query "UR10e user manual technical specifications Elbow ±160° working range"):
summary "Every spec sheet and manual excerpt that gives a number lists ±360° for the elbow", e.g. "Working range ± 360°
for Base, Shoulder, Elbow, Wrist 1, Wrist 2 and Wrist 3" (UR10e fact sheet), "Elbow ± 360° ±180°/Sec".

## 4. User manual / tech specs (mass)

https://www.universal-robots.com/manuals/EN/PDF/SW5_19/user-manual-UR10e-PDF_online/711-039-00_UR10e_User_Manual_en_Global.pdf
- Robot weight "33.3 kg / 73.5 lb" -> total_mass
https://www.universal-robots.com/media/1802458/ur10e-tech-specs-eng.pdf
- "33.5 kg / 73.9 lbs" including cable (not used; conflict noted)

## 5. Joint torques

https://www.universal-robots.com/articles/ur/robot-care-maintenance/max-joint-torques-cb3-and-e-series/
- "Size 0 · 9 Nm, Size 1 · 28 Nm, Size 2 · 54 Nm, Size 3 · 150 Nm, Size 4 · 330 Nm"; Wrist 2 and Wrist 3 are "Size 2"
  for UR10/UR10e/UR12e -> joints[4], joints[5].effort_limit = 54
https://forum.universal-robots.com/t/maximum-axis-speed-acceleration/13338 (second-hand: forum post)
- base and shoulder 330 Nm, elbow 150 Nm, wrists 56 Nm -> joints[0..2].effort_limit (330, 330, 150)
- wrist 1: estimate 54 Nm (Size 2 assumption), see NOTES.md

## Conflicts
- elbow range ±360° (techsheet, confirmed by search) vs ±160° (one SW5.22 tech-spec page extract)
- base/shoulder speed 120°/s (techsheet) vs 180°/s (06/2023 factsheet)
- weight 33.3 kg (user manual) vs 33.5 kg incl. cable
- wrist torque 54 Nm (Size 2) vs 56 Nm (forum)
