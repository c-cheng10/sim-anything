# UR10e: sources

Accessed 2026-11-05.

**How these were retrieved.** Direct page fetches to universal-robots.com were
blocked by this session's network policy, so every value below is taken from
web-search extracts of the cited page. Quotes are reproduced as returned.
Re-check against the live page when network access allows.

## 1. UR support article: DH parameters for calculations of kinematics and dynamics

https://www.universal-robots.com/articles/ur/application-installation/dh-parameters-for-calculations-of-kinematics-and-dynamics/
(the same UR10e link data is on https://www.universal-robots.com/developer/hardware-and-motion/robot-motion-dh-parameters/)

Columns: `a [m] | d [m] | alpha [rad] | Mass [kg] | Center of Mass [m] | Inertia Matrix`; section "UR10e/UR12e".
Standard (distal) DH, theta_i = q_i.

UR10e kinematics (search extract): "d1 = 0.1807 m, a2 = -0.6127 m, a3 = -0.57155 m, d4 = 0.17415 m, d5 = 0.11985 m,
and d6 = 0.11655 m, with the same alpha pattern as the UR5e" (alpha = π/2, 0, 0, π/2, -π/2, 0).

| Joint | a [m] | d [m] | alpha [rad] |
|---|---|---|---|
| 1 | 0 | 0.1807 | π/2 |
| 2 | -0.6127 | 0 | 0 |
| 3 | -0.57155 | 0 | 0 |
| 4 | 0 | 0.17415 | π/2 |
| 5 | 0 | 0.11985 | -π/2 |
| 6 | 0 | 0.11655 | 0 |

Link masses [kg] (developer page extract): "Link 1 | 7.369; Link 2 | 13.051; Link 3 | 3.989; Link 4 | 2.1; Link 5 | 1.98; Link 6 | 0.615".
Full inertia matrices are given on the page (not extracted). CoM is "an offset from the given joint frame for each
corresponding link".

## 2. UR10e datasheet (08/2023)

https://www.universal-robots.com/media/1807466/ur10e_e-series_datasheets_web.pdf
Indexed title line (drawing labels): "08/2023 180.7 612.7 571.55 119.85 174.15 691.4 R1300 190 UR10e Specification".
(06/2023 factsheet https://www.universal-robots.com/media/1828411/ur-product-factsheets-ur10e-06_2023-en-version-5-1-4-3.pdf has the same labels.)

## 3. UR10e techsheet

https://www.universal-robots.com/manuals/EN/TechSheets/UR10e_techsheet_pdf_online/UR10e_techsheet_en.pdf
Title line: "UR10e General specification Payload 12.5 kg (27.5 lbs) Reach 1300 mm (51.2 in)".
- Working range: "±360°" for every joint (extract).
- Max speed: "120°/s for base and shoulder and 180°/s for elbow and the three wrist joints" (extract). The 06/2023
  factsheet lists 180°/s for base and shoulder (conflict).
- Repeatability "±0.05 mm" per ISO 9283. Footprint "Ø190 mm".

## 4. UR10e technical specification (SW 5.22) and user manual

https://www.universal-robots.com/manuals/EN/HTML/SW5_22/Content/prod-usr-man/complianceUR10e/H_g5_sections/appendix_g5/tech_spec_sheet.htm
- Extract reports elbow working range "±160°" on this page (conflicts with ±360° in the techsheet).
https://www.universal-robots.com/manuals/EN/PDF/SW5_19/user-manual-UR10e-PDF_online/711-039-00_UR10e_User_Manual_en_Global.pdf
- Robot weight "33.3 kg / 73.5 lb".
https://www.universal-robots.com/media/1802458/ur10e-tech-specs-eng.pdf
- Weight "33.5 kg / 73.9 lbs" including cable.

## 5. Max. joint torques CB3 and e-Series

https://www.universal-robots.com/articles/ur/robot-care-maintenance/max-joint-torques-cb3-and-e-series/
- "Size 0 · 9 Nm, Size 1 · 28 Nm, Size 2 · 54 Nm, Size 3 · 150 Nm, Size 4 · 330 Nm".
- Wrist 2 and Wrist 3 are "Size 2" for UR10/UR10e/UR12e (extract).
- Forum post (secondary): base and shoulder 330 Nm, elbow 150 Nm, wrists 56 Nm (56 conflicts with the 54 Nm Size 2 rating).
