# Stool grip correction

The first correction froze the donor animation at frame 0. That is the wrong pose for the visible forward tilt.

## Stock evidence

- `SSBU-Dumped-Scripts-main/smashline/lua2cpp_gamewatch/gamewatch/AttackS3.txt` generates NORMAL_WEAPON at fighter frame 8 and selects `attack_s3`, then removes it at frame 25. The port keeps those timings.
- In `export/fighter/gamewatch/motion/normal_weapon/c00/c01attacks3s.nuanmb`, `Have` has 45 samples. Frames 0?6 have translation `(0.30, 5.798, 4.289)` and quaternion `(-0.0288986005, 0, -0.000008723, 0.9995823503)`. Frames 7?44 have translation `(0.30, 4.654, 9.409)` and quaternion `(0.0993024036, 0, -0.00000868351, 0.9950572848)`. Both scales are `(1, 1, 1)`. c06 and c07 contain the same values.
- The article hierarchy is `Have` (root) ? `Rot` ? `chair_c`. `chair_c` is already constant: translation `(0, 2.212, 3.765)`, identity rotation, scale `(1, 1.296, 1.709)`.
- The four chairM mesh objects have skinning influences from both `Have` and `chair_c`. Changing only chair_c would not move every stool vertex together.
- The built c06/c07 fighter skeletons preserve every original G&W bone, parent, and bind transform. Added Pyra bones do not replace G&W's hand hierarchy. The earlier claim that a grafted hand caused the stock root motion was not established.

## Correction

`fix_stool_grip` now samples Have at the stock spawn frame (8), checks that every remaining donor sample is identical, and writes that exact transform as a constant. It preserves chair_c, other transforms, visibility, and duration. This removes the pre-spawn pose from the article, shifts the root forward by 5.12 units relative to the previous fix, and restores the stock visible rotation. It does not add a guessed hand offset or alter the attachment descriptor.

The native article attachment and runtime motion synchronization have not been measured on the console. The selected pose is grounded in the donor clip and fighter spawn timing; its final in-game appearance still requires console verification. Up-Smash fixes are retained.
