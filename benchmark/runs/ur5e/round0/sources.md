# UR5e: sources used in spec.yaml

Accessed 2026-11-05. universal-robots.com cannot be fetched from this environment (WebFetch: host not
resolvable), so every quote below is a web-search extract. Items 1-5 come from the pre-gathered
`benchmark/inputs/ur5e/sources.md`; item 1b was added from a new web search in this run.

## 1. UR article: DH parameters for calculations of kinematics and dynamics

https://www.universal-robots.com/articles/ur/application-installation/dh-parameters-for-calculations-of-kinematics-and-dynamics/

Columns as published: `a [m] | d [m] | alpha [rad] | Dynamics: Mass [kg] | Center of Mass [m] | Inertia Matrix`.
Standard (distal) DH, theta_i = q_i (no offsets listed). UR5e rows (from inputs):

| Joint | a [m] | d [m] | alpha [rad] | spec.yaml |
|---|---|---|---|---|
| 1 | 0 | 0.1625 | π/2 | `joints[0].dh: {a: 0, d: 0.1625, alpha: 90}` |
| 2 | -0.425 | 0 | 0 | `joints[1].dh` |
| 3 | -0.3922 | 0 | 0 | `joints[2].dh` |
| 4 | 0 | 0.1333 | π/2 | `joints[3].dh` (alpha 90 deg) |
| 5 | 0 | 0.0997 | -π/2 | `joints[4].dh` (alpha -90 deg) |
| 6 | 0 | 0.0996 | 0 | `joints[5].dh` (frame 6 = tool flange) |

Link masses [kg] (inputs): "link 1 3.761, link 2 8.058, link 3 2.846, link 4 1.37, link 5 1.3, link 6 0.365"
-> `joints[*].link.mass`.

CoMs [m] (inputs): link 1 `[0, -0.02561, 0.00193]`, link 2 `[0.2125, 0, 0.11336]`, link 5 `[0, 0.0018, 0.01634]`.
FAQ: "the mass vector [x, y, z]^T is an offset from the given joint frame for each corresponding link"
-> `joints[0|1|4].link.com` (DH frame i, matching the tool's link-frame convention for dh_standard).

### 1b. Same article, CoMs for links 3, 4, 6 (web search 2026-11-05, query "UR5e DH parameters center of mass link 3 link 4 link 6 universal robots")

Extract: "Joint 3 -0.3922 0 0 Link 3 2.846 [0.15, 0.0, 0.0265] 0"; "Joint 4 0 0.1333 π/2 Link 4 1.37 [0, -0.0018, 0.01634] 0";
link 6 "0.365 kg with a center of mass of [0, 0, -0.001159] m" (a UR forum thread,
https://forum.universal-robots.com/t/correct-mass-and-center-or-mass/12353, questions whether this link-6 CoM is plausible).
-> `joints[2|3|5].link.com`. The same extract row also confirms the joint 3 and joint 4 DH values above.

## 2. UR5e datasheet (08/2023)

https://www.universal-robots.com/media/1807465/ur5e_e-series_datasheets_web.pdf

- Drawing labels: "162.5 425 392.2 99,7 133 494,9 R850 149" (match d1, a2, a3, d5, d4 in mm).
- "Payload 5 kg" -> `payload: 5`; "Reach 850 mm" (R850 on drawing) -> `reach.value: 0.850`.
- Weight "20.6 kg" including cable -> `total_mass: 20.6`. (User manual SW5.19 says 20.7 kg.)
- Footprint "Ø149 mm" -> `base.link.geometry[0].radius: 0.0745`. (Techsheet says Ø151 mm.)

## 3. UR5e techsheet

https://www.universal-robots.com/manuals/EN/TechSheets/UR5e_techsheet_pdf_online/UR5e_techsheet_en.pdf

- Every joint (base, shoulder, elbow, wrist 1-3): working range "±360°" -> `joints[*].limits: {lower: -360, upper: 360}`;
  maximum speed "±180°/s" -> `joints[*].velocity_limit: 180`.
- Pose repeatability "±0.03 mm" (ISO 9283) -> `repeatability: 0.00003` (m).

## 4. UR5e user manual SW 5.19 (reach definition only)

https://www.universal-robots.com/manuals/EN/PDF/SW5_19/user-manual-UR5e-PDF_online/710-965-00_UR5e_User_Manual_en_Global.pdf

- Working area: cylindrical volume, "850 mm" from the base joint -> `reach.measured_from: base_axis_horizontal`.
  The endpoint (flange vs wrist) is not stated; `measured_to: wrist_center` is an interpretation (see NOTES.md).

## 5. Joint torques

https://www.universal-robots.com/articles/ur/robot-care-maintenance/max-joint-torques-cb3-and-e-series/
- "Size 0 · 9 Nm, Size 1 · 28 Nm, Size 2 · 54 Nm, Size 3 · 150 Nm, Size 4 · 330 Nm"; wrist 2 and wrist 3 are Size 1 for UR5/UR5e.

https://forum.universal-robots.com/t/maximum-axis-speed-acceleration/13338 (secondary)
- UR5e base/shoulder/elbow 150 Nm, wrists 28 Nm -> `joints[*].effort_limit: [150, 150, 150, 28, 28, 28]`.
- Forum note: these are values "that will potentially cause physical damage to the joints, and this is not what a joint can exert".
