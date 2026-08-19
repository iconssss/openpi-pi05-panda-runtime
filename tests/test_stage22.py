import unittest
from openpi_robot_runtime.stage22 import audit,generate
class Stage22Test(unittest.TestCase):
 def test_balanced_counterfactuals_are_state_matched(self):
  a=audit(generate());self.assertTrue(all(x['constant_cosine_abs']==0 and x['max_within_group_state_delta']==0 for x in a.values()))
