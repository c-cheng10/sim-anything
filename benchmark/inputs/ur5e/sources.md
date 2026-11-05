# UR5e: sources

Accessed 2026-11-05.

**How these were retrieved.** Direct page fetches (WebFetch/curl) to
universal-robots.com were blocked by this session's network policy, so every
value below is taken from web-search extracts of the cited page (the search
tool returns text excerpts of the indexed page). Quotes are reproduced as
returned. Re-check against the live page when network access allows; the
"verification" note on each item says how strongly it is supported.

## 1. UR support article: DH parameters for calculations of kinematics and dynamics

https://www.universal-robots.com/articles/ur/application-installation/dh-parameters-for-calculations-of-kinematics-and-dynamics/
(also mirrored at https://www.universal-robots.com/developer/hardware-and-motion/robot-motion-dh-parameters/)

Table columns as published: `a [m] | d [m] | alpha [rad] | Dynamics: Mass [kg] | Center of Mass [m] | Inertia Matrix`.
Convention: standard (distal) DH; UR's article uses theta_i = q_i (no theta offsets listed).

UR5e kinematics (search extract, two independent queries agree):

| Joint | a [m] | d [m] | alpha [rad] |
|---|---|---|---|
| 1 | 0 | 0.1625 | π/2 |
| 2 | -0.425 | 0 | 0 |
| 3 | -0.3922 | 0 | 0 |
| 4 | 0 | 0.1333 | π/2 |
| 5 | 0 | 0.0997 | -π/2 |
| 6 | 0 | 0.0996 | 0 |

UR5e link masses [kg] (extract): link 1 3.761, link 2 8.058, link 3 2.846, link 4 1.37, link 5 1.3, link 6 0.365.
Centres of mass [m] (only partly extracted): link 1 `[0, -0.02561, 0.00193]`, link 2 `[0.2125, 0, 0.11336]`,
link 5 `[0, 0.0018, 0.01634]`; links 3, 4, 6 not extracted. Article FAQ (extract): "the mass vector [x, y, z]^T
is an offset from the given joint frame for each corresponding link". Article notes inertia matrices for UR3e/UR5e
are given as negligible.

Caveat quoted in forum threads: the per-robot calibrated DH values differ slightly from these nominal values.

Verification: d1, a2, a3, d4, d5, d6 and the alpha column extracted twice (two queries). Strong.

## 2. UR5e datasheet (08/2023)

https://www.universal-robots.com/media/1807465/ur5e_e-series_datasheets_web.pdf

Indexed title line (the dimension drawing labels): "08/2023 162.5 425 392.2 99,7 133 494,9 R850 149 UR5e Specification Payload".
- Payload "5 kg", Reach "850 mm", weight "20.6 kg" including cable (extract).
- Footprint "Ø149 mm".
- Max TCP speed 4 m/s (extract).

## 3. UR5e techsheet

https://www.universal-robots.com/manuals/EN/TechSheets/UR5e_techsheet_pdf_online/UR5e_techsheet_en.pdf

Title line: "UR5e General specification Payload 5 kg (11 lbs) Reach 850 mm (33.5 in)".
- Per-joint table: every joint (base, shoulder, elbow, wrist 1, wrist 2, wrist 3) working range "±360°", maximum speed "±180°/s" (extract).
- Pose repeatability "±0.03 mm" per ISO 9283.
- Footprint listed as "Ø151 mm" in this sheet (conflicts with Ø149 in the datasheet).

## 4. UR5e user manual / technical specification (SW 5.19)

https://www.universal-robots.com/manuals/EN/HTML/SW5_19/Content/prod-usr-man/complianceUR5e/H_g5_sections/appendix_g5/tech_spec_sheet.htm
https://www.universal-robots.com/manuals/EN/PDF/SW5_19/user-manual-UR5e-PDF_online/710-965-00_UR5e_User_Manual_en_Global.pdf

- Weight "20.7 kg" (user manual; datasheet says 20.6 kg).
- "Joints max 180°/s", tool "approx. 1 m/s" (older framing of the speed spec).
- Working area: cylindrical volume above and below the base, "850 mm" from the base joint (extract).

## 5. UR article: Max. joint torques CB3 and e-Series

https://www.universal-robots.com/articles/ur/robot-care-maintenance/max-joint-torques-cb3-and-e-series/

- Joint size ratings: "Size 0 · 9 Nm, Size 1 · 28 Nm, Size 2 · 54 Nm, Size 3 · 150 Nm, Size 4 · 330 Nm".
- Extract shows Wrist 2 and Wrist 3 as Size 1 for UR5/UR5e.
- The full joint-to-size mapping was not in the extract; a UR forum post
  (https://forum.universal-robots.com/t/maximum-axis-speed-acceleration/13338) gives UR5e base/shoulder/elbow 150 Nm,
  wrists 28 Nm. Secondary source.
- Forum note: these are the values "that will potentially cause physical damage to the joints, and this is not what a
  joint can exert".
