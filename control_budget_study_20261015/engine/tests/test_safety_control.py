import copy,unittest
from wsn.controller import Controller,INITIAL
from wsn.installation import Installation
from tests.test_aligned_feedback import POLICY

def observation(t=15,failed=False,missing=()):
 reports=[]
 for n in range(9):
  if n in missing:continue
  reports.append(dict(node=n,stamp_ns=int((t-1)*1e9),received_ns=int((t-.5)*1e9),depth=0,n=40,failed=0,current_n=40,current_failed=20 if failed and n<2 else 0,version=1 if n<2 else 0,ctrl_bytes=10*n,period_s=5,cca=20,busy=0,mean_J_ns=1000,epoch_first_bucket=2,buckets=[[2**32-1,2],[1,25],[0,25]]))
 return dict(time_ns=int(t*1e9),reports=reports,sink_control_bytes=100,timely_buckets={})
def controller(extra='interrupt_installbudget'):
 c=Controller(POLICY.replace('_aligned_','_aligned_safe_'+extra+'_'))
 c.pending=dict(decision=1,time_ns=10_000_000_000,bucket=2,action=2,context=[1,0,.2,0,0,1],fe=16,install_budget_bytes=1998,paths=INITIAL,reward_expected_versions=[1,1])
 c.sequence=1;c.version_paths[1]=INITIAL;c.installation=Installation(1,10_000_000_000,INITIAL,2);return c
class SafetyTests(unittest.TestCase):
 def test_one_missing_step_is_not_sustained(self):
  c=controller();o=observation(missing=(2,));e=c.assess_safety(o);self.assertIsNone(e['reason'])
 def test_two_missing_steps_interrupt_unconfirmed_transaction(self):
  c=controller();c.assess_safety(observation(missing=(2,)));o=observation(20,missing=(2,));e=c.assess_safety(o);r=c.interrupt_feedback(o,e);self.assertTrue(r['censored']);self.assertEqual(c.installation.outcome,'safety_interrupted');self.assertEqual(c.bandit.updates,[0]*4)
 def test_old_version_failure_cannot_abort_new_transaction(self):
  c=controller();o=observation(failed=True)
  for r in o['reports']:r['version']=0
  self.assertIsNone(c.interrupt_feedback(o,c.assess_safety(o)));self.assertIsNotNone(c.pending)
 def test_matching_version_failure_censors_once(self):
  c=controller();o=observation(failed=True);e=c.assess_safety(o);self.assertIsNone(c.interrupt_feedback(o,e)['reward']);self.assertIsNone(c.interrupt_feedback(o,e));self.assertEqual(len(c.feedbacks),1)
 def test_missing_source_cannot_trigger_interrupt(self):
  c=controller();o=observation(failed=True,missing=(1,));self.assertIsNone(c.interrupt_feedback(o,c.assess_safety(o)))
 def test_action_cutoff_disables_interrupt(self):
  c=controller();o=observation(80,failed=True);self.assertIsNone(c.interrupt_feedback(o,c.assess_safety(o)))
 def test_cost_duplicate_receipts_not_double_charged(self):
  c=controller();o=observation();a=c.observe_cost(o);b=c.observe_cost(o);self.assertEqual(a['observed_control_data_lower_bound'],b['observed_control_data_lower_bound']);self.assertEqual(b['observed_control_data_lower_bound'],460)
 def test_stale_meter_is_retained_as_lower_bound(self):
  c=controller();o=observation();c.observe_cost(o);o['reports']=[];self.assertEqual(c.observe_cost(o)['observed_control_data_lower_bound'],460)
 def test_sink_meter_reversal_is_rejected(self):
  c=controller();o=observation();c.observe_cost(o);o['sink_control_bytes']=99
  with self.assertRaises(ValueError):c.observe_cost(o)
 def test_budget_blocks_new_paths_with_unconfirmed_current_route(self):
  c=controller();o=observation();c.current_observation=o;c.reservations[0]=1;_,_,active,_,_=c.view(o);domains,row=c.constraint_view(active,o['time_ns']);self.assertFalse(any(row['available']));self.assertTrue(row['install_budget_exhausted'])
 def test_budget_boundary_restores_feasible_domains(self):
  c=controller();o=observation(20);c.current_observation=o;c.reservations[0]=1;_,_,active,_,_=c.view(o);domains,row=c.constraint_view(active,o['time_ns']);self.assertTrue(all(row['available']))
 def test_fresh_relay_resets_streak(self):
  c=controller();c.assess_safety(observation(missing=(2,)));c.assess_safety(observation(20));e=c.assess_safety(observation(25,missing=(2,)));self.assertIsNone(e['reason'])
