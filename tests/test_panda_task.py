import unittest

from openpi_robot_runtime.panda_task import ReachMetric


class PandaTaskTest(unittest.TestCase):
    def test_reach_success_has_explicit_boundary(self) -> None:
        metric = ReachMetric((0.0, 0.0, 0.0), threshold_meters=0.04)
        self.assertTrue(metric.success((0.04, 0.0, 0.0)))
        self.assertFalse(metric.success((0.04001, 0.0, 0.0)))

    def test_distance_rejects_wrong_dimension(self) -> None:
        metric = ReachMetric((0.0, 0.0, 0.0))
        with self.assertRaises(ValueError):
            metric.distance_meters((0.0, 0.0))
