import unittest

from openpi_robot_runtime.panda_bridge import DroidLikePandaActionBridge


class PandaBridgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = DroidLikePandaActionBridge(tuple((0.0, 1.0) for _ in range(7)), control_dt_seconds=0.1)

    def test_integrates_velocity_and_maps_gripper(self) -> None:
        result = self.bridge.to_position_command(
            current_joint_positions=(0.5,) * 7,
            droid_like_action=(0.5,) * 7 + (0.25,),
        )
        self.assertEqual(result.joint_position_targets, (0.55,) * 7)
        self.assertEqual(result.gripper_normalized, 0.25)
        self.assertFalse(result.clipped)

    def test_rejects_non_finite_values_and_clips_limits(self) -> None:
        result = self.bridge.to_position_command(
            current_joint_positions=(0.99,) * 7,
            droid_like_action=(5.0,) * 7 + (2.0,),
        )
        self.assertEqual(result.joint_position_targets, (1.0,) * 7)
        self.assertEqual(result.gripper_normalized, 1.0)
        self.assertTrue(result.clipped)
        with self.assertRaises(ValueError):
            self.bridge.to_position_command(
                current_joint_positions=(0.0,) * 7,
                droid_like_action=(float("nan"),) * 8,
            )
