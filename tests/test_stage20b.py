import unittest
from openpi_robot_runtime.stage20b import CONDITIONS, DEVELOPMENT_TARGETS, FINAL_TEST_TARGETS, select_condition

class Stage20BTest(unittest.TestCase):
    def test_new_splits_are_disjoint_and_selection_is_frozen(self) -> None:
        self.assertFalse(set(DEVELOPMENT_TARGETS) & set(FINAL_TEST_TARGETS))
        rows = []
        for condition in CONDITIONS:
            for _ in DEVELOPMENT_TARGETS:
                rows.append({"condition": condition.name, "success": condition.name == "damped_slow_200", "final_distance_m": 0.001 if condition.name != "damped_slow_200" else 0.02, "bridge_clipped_steps": 0})
        self.assertEqual(select_condition(rows), "damped_slow_200")
