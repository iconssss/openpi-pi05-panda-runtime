import unittest

from openpi_robot_runtime.stage19_analysis import analyze_stage18_report, mean_curve_svg


def row(variant: str, final: float) -> dict[str, object]:
    return {"variant": variant, "visual_condition": "canonical", "target_index": 8,
            "distance_curve_m": [0.2] * 31 + [final] * 10, "success": False,
            "safe_hold_count": 0, "bridge_clipped_steps": 0}


class Stage19AnalysisTest(unittest.TestCase):
    def test_keeps_all_arms_and_reports_raw_difference(self) -> None:
        names = ("raw_pi05_identity", "residual_adapter_seed_11", "residual_adapter_seed_22", "residual_adapter_seed_33", "dls_oracle")
        report = {"experiment_boundary": {"steps_per_episode": 40}, "episodes": [row(name, 0.2 if name == names[0] else 0.1) for name in names]}
        result = analyze_stage18_report(report)
        self.assertEqual(tuple(result["variants"]), names)
        self.assertAlmostEqual(result["final_distance_reduction_vs_raw_m"]["residual_adapter_seed_22"], 0.1)
        self.assertIn("zero bridge-clipped steps", result["supported_negative_finding"])
        self.assertIn("raw_pi05_identity", mean_curve_svg(result))

    def test_rejects_missing_arm_and_mismatched_curve(self) -> None:
        report = {"experiment_boundary": {}, "episodes": [row("raw_pi05_identity", 0.1)]}
        with self.assertRaises(ValueError):
            analyze_stage18_report(report)
