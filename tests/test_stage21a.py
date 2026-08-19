import unittest
from openpi_robot_runtime.stage21a import action_feature, split_for_target
class Stage21ATest(unittest.TestCase):
 def test_fixed_chunk_summary_and_target_split(self):
  self.assertEqual(action_feature(((1.,)*8,(3.,)*8)), (1.,)*8+(2.,)*8)
  self.assertEqual([split_for_target(i) for i in (0,15,16,19,20,23)], ["train","train","validation","validation","test","test"])
  with self.assertRaises(ValueError): action_feature(())
