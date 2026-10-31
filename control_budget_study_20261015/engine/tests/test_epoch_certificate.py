import copy,unittest
from test_stable_context import POLICY
from test_base_controller import obs
from wsn.controller import Controller,INITIAL
class EpochTests(unittest.TestCase):
 def observation(self):
  o=obs(20)
  for r in o['reports']:
   if r['node']<2:r.update(version=1,epoch_first_bucket=2,buckets=[[2**32-1,2],[3,25],[2,25],[1,25]])
  o['timely_buckets']={'2':[25,20],'3':[25,20]};return o
 def test_report_anchor_recovers_closed_current_version_window(self):
  o=self.observation();c=Controller(POLICY.replace('_ops_','_ops_epoch_'));c.version_paths[1]=INITIAL
  s=c.view(o)[-1]['settled_service'];self.assertTrue(s['known']);self.assertEqual(s['buckets'],[2]);self.assertEqual(s['worst_timely'],.8)
  old=Controller(POLICY);old.version_paths[1]=INITIAL;self.assertFalse(old.view(o)[-1]['settled_service']['known'])
 def test_pre_epoch_bucket_excluded(self):
  o=self.observation();c=Controller(POLICY.replace('_ops_','_ops_epoch_'));c.version_paths[1]=INITIAL
  self.assertNotIn(1,c.view(o)[-1]['settled_service']['buckets'])
 def test_wire_marker_mismatch_rejected(self):
  o=self.observation();o['reports'][0]['epoch_first_bucket']=3
  with self.assertRaises(ValueError):Controller(POLICY.replace('_ops_','_ops_epoch_')).view(o)
 def test_no_truth_or_unreceived_epoch_required(self):
  o=self.observation();o['reports']=[r for r in o['reports']if r['node']!=0]
  c=Controller(POLICY.replace('_ops_','_ops_epoch_'));c.version_paths[1]=INITIAL
  self.assertEqual(c.view(o)[-1]['settled_service']['reason'],'missing_fresh_source')
