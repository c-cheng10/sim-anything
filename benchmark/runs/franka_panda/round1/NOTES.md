# Franka Emika Panda round 1: notes

- **Sources**: FCI docs (modified DH table, flange row, torques), Gaz et al. RA-L 2019 (joint 7 alpha,
  table confirmation), Panda datasheet May 2019 (ranges, speeds, payload, reach, repeatability;
  second-hand reseller copy), a university-hosted datasheet copy (mass ~17.8 kg; second-hand). All of
  these came from web-search extracts. See `sources.md`.
- **Convention**: `dh_modified` (Craig), with each row stored on its own joint exactly as published and
  theta_i = q_i. Units are mm/deg: the table's metres were written in mm (x1000) and π/2 as 90 deg, so the
  datasheet's degree ranges and deg/s speeds stay verbatim.
- **EE site**: the flange face centre, from the DH "Flange" row: `ee.origin.xyz = [0, 0, 107]` along z7. No
  hand is modelled. FK at q = 0 gives the flange at (88, 0, 926) mm, pointing down, which matches the
  Panda's upright zero pose.
- **Estimates**:
  - Home pose: A2 -45, A4 -135, A6 90, A7 45 deg. A4's range of -176..-4 deg excludes zero. This pose
    puts the flange pointing straight down at (307, 0, 590) mm, the usual Panda ready posture.
  - All collision radii: 35-60 mm, from photos.
  - The reach definition: shoulder to flange. The datasheet gives no reference points. The stretched
    shoulder-to-flange length from the DH lengths is about 858 mm.
- **Iterations**: 2.
  1. FAILED: self_collision_home. At home, the A7 flange cylinder (r 40) touched the A4 and A5 links
     by 2 mm, and A2 was left at 0, which tilted the flange.
  2. Home changed to the ready pose (A2 -45, A7 45 added) and the A7 radius cut to 35 mm. PASSED: 14
     checks, 0 errors, 1 warning.
- **Final status**: PASSED. The reach check gives 0.858 m, 0.3% from the rated 0.855 m. The remaining
  warning is about collision exclusions: A2/A4 is excluded because the capsules overlap around the short
  A3 link (82.5 mm offset) in every sampled pose. This is expected for the Panda's elbow offset, but it
  means A2/A4 contacts are not checked.
- **Doubts**:
  - Joint speeds: I used the datasheet's 150/180 deg/s. The FCI FER table gives 2.175/2.61 rad/s
    (124.6/149.5 deg/s), which is lower, and the A5-A7 180 deg/s figure appears in only one datasheet
    version.
  - The FCI page now heads the DH table "FR3". The Panda attribution relies on the older FCI page and
    the Gaz paper, which give the same table.
  - Frames 1 and 2 coincide at 333 mm in modified DH. As a result, the auto base cylinder runs the full
    333 mm and link 1 is a sphere at the shoulder, whereas the real arm has a short base and a tall
    link 1. This only affects geometry and mass distribution, not kinematics.
  - No per-link masses are modelled. The builder spreads the 17.8 kg by volume.
