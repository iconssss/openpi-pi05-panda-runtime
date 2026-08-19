import unittest

from openpi_robot_runtime.stage20 import DIAGNOSTIC_TARGETS, DLS_DIAGNOSTIC_CONDITIONS, FINAL_TEST_TARGETS, select_diagnostic_condition


class Stage20ProtocolTest(unittest.TestCase):
    def test_split_is_disjoint_and_selection_prefers_all_success(self) -> None:
        self.assertFalse(set(DIAGNOSTIC_TARGETS) & set(FINAL_TEST_TARGETS))
        rows = []
        for condition in DLS_DIAGNOSTIC_CONDITIONS:
            for _ in DIAGNOSTIC_TARGETS:
                rows.append({"condition": condition.name, "success": condition.name == "existing_120", "final_distance_m": 0.01 if condition.name == "existing_120" else 0.001})
        self.assertEqual(select_diagnostic_condition(rows), "existing_120")

    def test_selection_uses_lower_distance_then_shorter_horizon(self) -> None:
        rows = []
        for condition in DLS_DIAGNOSTIC_CONDITIONS:
            for _ in DIAGNOSTIC_TARGETS:
                rows.append({"condition": condition.name, "success": False, "final_distance_m": 0.1 if condition.name != "existing_40" else 0.05})
        self.assertEqual(select_diagnostic_condition(rows), "existing_40")
