# Stage 8 — ALOHA Simulator Readiness

Date: 2026-08-18

## Dependency and contract audit

Project 2's existing isolated OpenPI environment already contains:

- Python 3.11.15
- MuJoCo 2.3.7, dm-control 1.0.14, gymnasium 0.29.1
- gym-aloha 0.1.1, imageio and Pillow

No dependency installation is currently needed in the Python environment.
The old Project 1 `lerobot-act` environment is absent and is not reused.

`gym_aloha/AlohaTransferCube-v0` uses a top camera `(480, 640, 3)` and a
14-dimensional dual-arm action vector. π0.5-DROID expects two `224x224` images,
a 7-joint single-arm state, and predicts 8 actions. They are not directly
interchangeable. A task evaluation must use an explicit, limited cross-embodiment
adapter and cannot be presented as native π0.5-DROID evaluation.

## Headless renderer diagnosis

The first smoke test set `MUJOCO_GL=egl` and `PYOPENGL_PLATFORM=egl` but failed
while importing PyOpenGL EGL (`eglQueryString` unavailable). This occurs before
environment reset and is classified as a remote container system EGL/OpenGL
runtime issue—not an OpenPI, checkpoint, or gym-aloha schema failure.

No packages, drivers, Project 1 files, checkpoint, or shared-persistent data
were modified during diagnosis. The next bounded repair candidate is installation
of minimal container-system EGL/OpenGL runtime libraries (such as `libegl1` and
`libgl1`; `libosmesa6` only if EGL remains unavailable). It requires explicit
approval because it writes to the nonpersistent container system disk.

Shared disk remains 21 GB free. The Project 2 OpenPI environment is 4.7 GB and
project runtime/cache directory is 20 GB.

## Repair and successful smoke test

With user approval, minimal `libegl1` and `libgl1` runtime packages were added
to the nonpersistent container system disk. The dependency solver installed the
necessary Mesa/EGL dependency chain (about 55 MB download and 234 MB system-disk
use); `/root/shared-nvme`, Project 2's Python environment, checkpoint, and
other projects were unchanged.

The same EGL test then passed: `gym_aloha/AlohaTransferCube-v0` reset, stepped
five zero actions, and rendered a `480x640x3 uint8` top image. Artifacts:

- `/root/shared-nvme/openpi-robot-runtime/results/aloha_headless_smoke/report.json`
- `/root/shared-nvme/openpi-robot-runtime/results/aloha_headless_smoke/transfer_cube_top_seed7.png`

### Embodiment mismatch decision

The Gym wrapper exposes a 14-dimensional normalized dual-arm action. Its
underlying dm-control action spec is 16 joint/finger target values, while
π0.5-DROID predicts 7 single-arm joint velocities plus one gripper position.
The simulator has one top camera; DROID requires two camera views and a
7-joint state. This is a topology and control-mode mismatch, not merely image
resize or range scaling. Directly driving ALOHA with π0.5-DROID is rejected as
an invalid evaluation.

No Panda/Franka 7-DoF asset is currently present in Project 2. A credible next
simulator is therefore a separately stored MuJoCo Menagerie Panda/Franka asset,
followed by an explicitly documented DROID-like observation/action bridge.

## Official Panda asset acquisition (completed)

The official MuJoCo Menagerie Panda subtree is now materialized at
`/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie`. It is pinned
to commit `da76818e269b82289eba39808e2fb91d679d6994` and contains 80 files,
totalling exactly `36,560,926` bytes.

Every file was accepted only after its content reproduced the corresponding
official Git blob SHA-1. The downloader is resumable: it preserves verified
targets and partial files, and fetches an immutable jsDelivr URL containing the
commit (`.../mujoco_menagerie@<commit>/...`) before falling back to GitHub Raw.

Two recovery defects were found and corrected: an early jsDelivr URL omitted
the required `@commit` separator and returned an HTML response; later, asking a
partial clone for blob sizes caused on-demand network reads. The final downloader
uses the local official Git tree only for file paths and blob IDs, then validates
the downloaded file's own byte length as part of the Git blob hash. This is an
integrity check stronger than a separate length-only check and avoids a network
dependency for manifest recovery.

The asset download is complete; no policy evaluation has yet been performed
against Panda. The next stage must implement and validate the explicit
DROID-like Panda observation/action bridge before any VLA simulation claim.
