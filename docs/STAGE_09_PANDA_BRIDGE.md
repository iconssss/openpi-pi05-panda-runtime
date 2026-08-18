# Stage 9 - Panda DROID-like bridge smoke

Date: 2026-08-18

## Purpose and boundary

This stage validates a *simulator-only* interface bridge from an 8-dimensional
DROID-like action to the official MuJoCo Menagerie Panda model. It is not a
policy-transfer, manipulation-success, camera-calibration, or real-robot claim.

## Verified model interface

The immutable Panda `scene.xml` loaded headlessly with MuJoCo 2.3.7:

- 7 arm joints: `joint1` through `joint7`;
- 9 `qpos` / 9 velocity coordinates;
- 8 controls: arm actuator indices 0--6 and one tendon-based gripper control
  at index 7;
- no XML-defined cameras (`ncam=0`).

The last point matters: the two images used by the DROID-shaped request are
explicit synthetic free-camera proxies. They demonstrate image construction and
transport shape, not DROID camera equivalence.

## Bridge convention

`DroidLikePandaActionBridge` treats the first seven values as joint velocities,
clips them to +/- 1 rad/s, integrates one 1/15 s control interval, and clamps
the resulting targets to the XML joint limits. The eighth value is clipped to
`[0, 1]`, then linearly mapped to the MuJoCo gripper actuator control range.
This is a declared simulator convention rather than an asserted physical Panda
SDK contract.

## Remote smoke evidence

The remote smoke applied a fixed finite action, set the resolved controls, and
stepped MuJoCo 15 times. It constructed two uint8 `224x224x3` RGB proxy frames
and a 7-joint / one-gripper DROID-shaped observation.

Artifacts:

- `/root/shared-nvme/openpi-robot-runtime/results/panda_bridge_smoke/report.json`
- `/root/shared-nvme/openpi-robot-runtime/results/panda_bridge_smoke/exterior_proxy.png`
- `/root/shared-nvme/openpi-robot-runtime/results/panda_bridge_smoke/wrist_proxy.png`

The smoke intentionally does **not** call π0.5. The next bounded experiment is
to make one live policy request using these synthetic proxies, then execute only
the first action through this bridge under the already-tested process-owned
deadline and safe-hold boundary.
