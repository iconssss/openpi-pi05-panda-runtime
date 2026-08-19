import unittest

from openpi_robot_runtime.stage18 import (
    ADAPTER_SEEDS,
    STAGE17_HELD_OUT_TARGET_INDICES,
    STAGE18_EPISODE_STEPS,
    combine_residual_action,
    evaluation_variants,
)


class Stage18ProtocolTest(unittest.TestCase):
    def test_pre_registered_held_out_protocol(self) -> None:
        self.assertEqual(STAGE17_HELD_OUT_TARGET_INDICES, (8, 9, 10, 11))
        self.assertEqual(STAGE18_EPISODE_STEPS, 40)
        variants = evaluation_variants()
        self.assertEqual([variant.name for variant in variants], [
            "raw_pi05_identity", "residual_adapter_seed_11", "residual_adapter_seed_22",
            "residual_adapter_seed_33", "dls_oracle",
        ])
        self.assertEqual([variant.adapter_seed for variant in variants if variant.adapter_seed is not None], list(ADAPTER_SEEDS))

    def test_residual_preserves_gripper_and_rejects_wrong_dimensions(self) -> None:
        self.assertEqual(combine_residual_action((1.0,) * 7 + (0.25,), (-0.5,) * 7), (0.5,) * 7 + (0.25,))
        with self.assertRaises(ValueError):
            combine_residual_action((0.0,) * 7, (0.0,) * 7)
        with self.assertRaises(ValueError):
            combine_residual_action((0.0,) * 8, (0.0,) * 6)
