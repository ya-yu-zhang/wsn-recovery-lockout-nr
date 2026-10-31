import copy,subprocess,tempfile,unittest
from pathlib import Path
from wsn.aligned_feedback import VersionBucketCache
from wsn.controller import Controller,INITIAL
POLICY='linucb_event_scalar4_failure_current_ops_epoch_aligned_ctx6_noop_cache20_retry_freshfixed_mask'
def observation(t=30,versions=(1,1),anchors=(3,4),counts=(25,25)):
 return dict(time_ns=int(t*1e9),reports=[dict(node=f,version=versions[f],epoch_first_bucket=anchors[f],stamp_ns=25_100_000_000,received_ns=25_200_000_000,buckets=[[2**32-1,anchors[f]],[4,counts[f]],[3,25],[2,25]])for f in(0,1)],timely_buckets={'4':[20,22],'3':[25,25],'2':[25,25]})
def controller(held=False):
 c=Controller(POLICY);c.pending=dict(decision=1,time_ns=10_000_000_000,bucket=2,action=2,context=[1,0,.2,0,0,1],fe=16,install_budget_bytes=0 if held else 1998,paths=None if held else INITIAL,reward_expected_versions=[0,0]if held else[1,1],admitted_hold=held,admission=dict(proposed_paths=INITIAL));return c
def settle(c,o):return c.feedback(o,{r['node']:r for r in o['reports']})
class AlignedTests(unittest.TestCase):
 def test_late_second_install_moves_reward_after_both_epochs(self):
  c=controller();r=settle(c,observation());self.assertEqual(r['cohort_start_ns'],20_000_000_000);self.assertEqual(r['offered'],[25,25]);self.assertEqual(c.bandit.updates,[0,0,1,0])
 def test_old_version_counts_cannot_score_expected_new_version(self):
  c=controller();o=observation(versions=(0,0),anchors=(0,0));self.assertIsNone(settle(c,o));o['time_ns']=40_000_000_000;r=settle(c,o);self.assertTrue(r['censored']);self.assertIsNone(r['reward']);self.assertEqual(c.bandit.updates,[0]*4)
 def test_one_confirmed_source_is_not_two_source_confirmation(self):
  c=controller();self.assertIsNone(settle(c,observation(versions=(1,0))));self.assertNotIn('reward_bucket',c.pending)
 def test_admitted_hold_uses_old_versions_but_post_decision_bucket(self):
  c=controller(True);o=observation(versions=(0,0),anchors=(0,0));r=settle(c,o);self.assertEqual(r['expected_versions'],[0,0]);self.assertEqual(r['cohort_start_ns'],10_000_000_000)
 def test_sparse_window_is_censored_without_searching_later_windows(self):
  c=controller();r=settle(c,observation(counts=(19,25)));self.assertEqual(r['missing_reason'],'insufficient_generation');self.assertIsNone(c.pending);self.assertEqual(r['offered'],[])
 def test_closed_bucket_requires_delivery_deadline_to_settle(self):
  c=controller();o=observation(25.199);o['reports']=[dict(r,received_ns=25_150_000_000)for r in o['reports']];self.assertIsNone(settle(c,o));o['time_ns']=25_200_000_000;self.assertIsNotNone(settle(c,o)['reward'])
 def test_first_visible_provenance_is_retained_and_versions_separate(self):
  cache=VersionBucketCache();o=observation();cache.observe(o);old=copy.deepcopy(cache.entries);cache.observe(o);self.assertEqual(cache.entries,old);o=observation(versions=(2,2));cache.observe(o);self.assertIn((0,1,4),cache.entries);self.assertIn((0,2,4),cache.entries)
 def test_duplicate_feedback_never_updates_twice(self):
  c=controller();settle(c,observation());self.assertIsNone(settle(c,observation()));self.assertEqual(c.bandit.updates,[0,0,1,0])
 def test_timeout_records_no_imputed_partial_reward(self):
  c=controller();o=observation();o['reports'][1]['buckets']=[[2**32-1,4],[3,25],[2,25]];self.assertIsNone(settle(c,o));o['time_ns']=40_000_000_000;r=settle(c,o);self.assertTrue(r['censored']);self.assertEqual(r['offered'],[])
 def test_budget_boundary_and_per_node_independence(self):
  h=Path(__file__).resolve().parents[1]/'ns3'
  code='#include "report_budget.h"\n#include <cassert>\nint main(){aligned::RetryBudget b;assert(b.Reserve(0,19999999999LL).admitted);assert(!b.Reserve(0,19999999999LL).admitted);assert(b.Reserve(0,20000000000LL).admitted);assert(b.Reserve(1,20000000000LL).admitted);assert(!b.Reserve(1,20000000001LL).admitted);assert(aligned::ReservationBytes==1143);}'
  with tempfile.TemporaryDirectory()as d:
   p=Path(d);(p/'test.cc').write_text(code);subprocess.run(['g++','-std=c++20','-I',str(h),str(p/'test.cc'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
