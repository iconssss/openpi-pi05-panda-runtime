import unittest

from openpi_robot_runtime.embodiment_diagnostics import ActionInterpretation, cosine_alignment, one_step_progress


class EmbodimentDiagnosticsTest(unittest.TestCase):
    def test_fixed_action_interpretations_preserve_gripper_and_transform_arm(self) -> None:
        action = (1.0, -2.0, 0.5, 0.0, 1.0, -1.0, 2.0, 0.25)
        self.assertEqual(ActionInterpretation("identity").apply(action), action)
        self.assertEqual(ActionInterpretation("negative_half", arm_sign=-1.0, arm_gain=0.5).apply(action), (-0.5, 1.0, -0.25, 0.0, -0.5, 0.5, -1.0, 0.25))

    def test_alignment_and_progress_are_explicit(self) -> None:
        self.assertEqual(cosine_alignment((1.0, 0.0), (2.0, 0.0)), 1.0)
        self.assertEqual(cosine_alignment((1.0, 0.0), (-2.0, 0.0)), -1.0)
        self.assertIsNone(cosine_alignment((0.0, 0.0), (2.0, 0.0)))
        self.assertAlmostEqual(one_step_progress(0.2, 0.17), 0.03)

    def test_invalid_interpretation_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ActionInterpretation("bad", arm_sign=0.0)
