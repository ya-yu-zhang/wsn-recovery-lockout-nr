import unittest
from wsn.controller import Controller
from test_base_controller import obs
P='linucb_event_scalar4_failure_current_ops_low4_noop_cache20_retry_mask'
class LeaseTests(unittest.TestCase):
 def test_period_specific_freshness(self):
  c=Controller(P,'lease10_20')
  self.assertEqual(c.fresh_limit(0,{'period_s':20}),8_000_000_000)
  self.assertEqual(c.fresh_limit(2,{'period_s':10}),16_000_000_000)
  self.assertEqual(c.fresh_limit(2,{'period_s':20}),32_000_000_000)
 def test_idle_relay_report_is_not_physical_liveness(self):
  c=Controller(P,'lease10_20');o=obs(40)
  for r in o['reports']:
   r['period_s']=20 if r['node']>=2 else 5
  r=o['reports'][2];r['stamp_ns']=9_000_000_000;r['received_ns']=10_000_000_000
  self.assertIn(2,c.view(o)[2]);o['time_ns']=42_000_000_000
  self.assertNotIn(2,c.view(o)[2])
if __name__=='__main__':unittest.main()
