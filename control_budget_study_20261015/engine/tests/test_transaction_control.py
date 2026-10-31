import copy,unittest
from wsn.controller import Controller,INITIAL
from wsn.installation import Installation
from tests.test_aligned_feedback import POLICY
from tests.test_safety_control import observation

def controller(extra='txguard_creditexplore'):
 c=Controller(POLICY.replace('_aligned_','_aligned_safe_interrupt_installbudget_transaction_'+extra+'_'))
 c.pending=dict(decision=1,time_ns=10_000_000_000,bucket=2,action=2,context=[1,0,.2,0,0,1],fe=16,install_budget_bytes=1998,paths=INITIAL,reward_expected_versions=[1,1])
 c.sequence=1;c.version_paths[1]=INITIAL;c.installation=Installation(1,10_000_000_000,INITIAL,2)
 return c

class TransactionTests(unittest.TestCase):
 def test_old_missing_path_cannot_abort_partial_new_install(self):
  c=controller();c.assess_safety(observation(20,missing=(2,)))
  o=observation(25,missing=(2,));o['reports'][1]['version']=0
  self.assertIsNone(c.interrupt_feedback(o,c.assess_safety(o)))
  self.assertEqual(c.last_interruption_check['blocked_reason'],'await_two_matching_sources')
  self.assertFalse(c.installation.closed)
 def test_predecision_matching_report_is_not_new_confirmation(self):
  c=controller();o=observation(15,failed=True);o['reports'][1]['stamp_ns']=9_000_000_000
  self.assertIsNone(c.interrupt_feedback(o,c.assess_safety(o)))
  self.assertEqual(c.last_interruption_check['blocked_reason'],'await_two_matching_sources')
 def test_full_new_pair_obeys_delivery_grace(self):
  c=controller();o=observation(15,failed=True)
  self.assertIsNone(c.interrupt_feedback(o,c.assess_safety(o)))
  self.assertEqual(c.last_interruption_check['blocked_reason'],'settled_credit_delivery_grace')
  self.assertEqual(c.last_interruption_check['reward_not_before_ns'],20_200_000_000)
 def test_received_reward_has_priority_over_interrupt(self):
  c=controller();o=observation(25,failed=True)
  for r in o['reports']:
   if r['node']<2:r['buckets']=[[2**32-1,2],[2,25],[1,25],[0,25]]
  o['timely_buckets']={'2':[20,21]}
  f=c.interrupt_feedback(o,c.assess_safety(o));self.assertIsNotNone(f['reward'])
  self.assertEqual(c.bandit.updates,[0,0,1,0]);self.assertEqual(c.safety_events,[])
 def test_unavailable_reward_after_grace_is_explicit_censor(self):
  c=controller();o=observation(25,failed=True);f=c.interrupt_feedback(o,c.assess_safety(o))
  self.assertTrue(f['censored']);self.assertIsNone(f['reward']);self.assertEqual(c.bandit.updates,[0]*4)
 def test_missing_target_is_required_even_when_versions_match(self):
  c=controller();o=observation(25);e=c.assess_safety(o)
  e.update(reason='sustained_missing_current_relay',sustained_missing_relays=[8])
  self.assertIsNone(c.interrupt_feedback(o,e));self.assertEqual(c.last_interruption_check['blocked_reason'],'missing_relay_not_in_target')
 def test_unattempted_arms_precede_retry_of_censored_arm(self):
  c=controller();self.assertEqual(c.exploration_candidates([0,1,2,3],[0,1]),[2,3])
 def test_qualified_arm_does_not_need_repeated_paid_exploration(self):
  c=controller();c.feedbacks=[dict(action=0,reward=.8)]
  self.assertEqual(c.exploration_candidates([0,1,2,3],[]),[1,2,3])
 def test_censor_does_not_mark_an_arm_as_successfully_observed(self):
  c=controller();c.feedbacks=[dict(action=1,reward=None)]
  self.assertEqual(c.exploration_candidates([1],[1]),[1])
 def test_two_failed_exposures_exhaust_the_arm_allowance(self):
  c=controller();self.assertEqual(c.exploration_candidates([1],[1,1]),[])
 def test_masked_unavailable_arms_cannot_be_explored(self):
  c=controller();self.assertEqual(c.exploration_candidates([2],[0,1]),[2])
 def test_disabled_credit_registry_preserves_single_attempt_semantics(self):
  c=controller('txguard');self.assertEqual(c.exploration_candidates([1,2],[1]),[2]);self.assertEqual(c.exploration_cap,4)

