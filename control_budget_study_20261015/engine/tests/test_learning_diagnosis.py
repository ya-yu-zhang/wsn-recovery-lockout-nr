import copy,unittest
from wsn.controller import Controller,INITIAL
from wsn.learning_controller import exposure_gate
from tests.test_safety_control import observation

POLICY='linucb_event_scalar4_failure_current_ops_epoch_aligned_safe_interrupt_installbudget_transaction_txguard_observable_installexit_learnstudy_gated_ctx6_noop_cache20_retry_freshfixed_mask'

def prepared():
    c=Controller(POLICY,'local15_event');c.sequence=1;c.version_paths[1]=INITIAL
    c.feedbacks=[dict(reward=.8,action=0,time_ns=30_000_000_000)]
    c.current_observation=observation(55,failed=True)
    return c

class LearningDiagnosisTests(unittest.TestCase):
    def test_received_failure_with_settled_idle_state_admits(self):
        g=exposure_gate(prepared(),[0,1,2,3]);self.assertTrue(g['admitted']);self.assertEqual(set(g['eligible']),{1,2,3})
    def test_unknown_relay_is_not_zero_congestion(self):
        c=prepared();c.current_observation['reports']=[r for r in c.current_observation['reports'] if r['node']!=2]
        self.assertIn('congestion_unknown',exposure_gate(c,[1,2,3])['reasons'])
    def test_old_source_snapshot_blocks_exposure(self):
        c=prepared();c.current_observation['reports'][0]['stamp_ns']=0
        self.assertIn('missing_fresh_source',exposure_gate(c,[1,2,3])['reasons'])
    def test_congestion_and_queue_are_separate_refusals(self):
        c=prepared();c.current_observation['reports'][2].update(busy=6,cca=20,depth=3)
        g=exposure_gate(c,[1,2,3]);self.assertIn('busy_above_quarter',g['reasons']);self.assertIn('queue_above_two',g['reasons'])
    def test_missing_cca_is_unknown(self):
        c=prepared();c.current_observation['reports'][2]['cca']=0
        self.assertFalse(exposure_gate(c,[1,2,3])['admitted'])
    def test_censored_feedback_does_not_enable_or_credit(self):
        c=prepared();c.feedbacks=[dict(reward=None,action=2,time_ns=30_000_000_000)]
        g=exposure_gate(c,[1,2,3]);self.assertIn('no_prior_qualified_feedback',g['reasons']);self.assertEqual(g['credited_actions'],[])
    def test_spent_censored_attempt_cannot_be_retried(self):
        c=prepared();c.event_attempts=[2];self.assertNotIn(2,exposure_gate(c,[1,2,3])['eligible'])
    def test_matched_version_does_not_allow_unknown_path(self):
        c=prepared();c.current_observation['reports'][0]['version']=99
        self.assertIn('unmatched_observed_paths',exposure_gate(c,[1,2,3])['reasons'])
    def test_recent_feedback_and_budget_block(self):
        c=prepared();c.feedbacks[0]['time_ns']=50_000_000_000;c.reservations[2]=1
        g=exposure_gate(c,[1,2,3]);self.assertIn('transaction_cooldown',g['reasons']);self.assertIn('installation_budget_used',g['reasons'])
    def test_resource_and_credited_actions_are_excluded(self):
        c=prepared();c.feedbacks.append(dict(reward=.7,action=1,time_ns=30_000_000_000))
        self.assertEqual(set(exposure_gate(c,[0,1,2])['eligible']),{2})
    def test_freeze_retains_existing_model_and_disables_future_training(self):
        c=Controller(POLICY.replace('_gated_','_gated_freeze4_'),'local15_event')
        for _ in range(4):c.bandit.update(0,[1,0,0,0,0,1],.8)
        a=copy.deepcopy(c.bandit.A);c.step(observation(55))
        self.assertFalse(c.train_bandit);self.assertEqual(c.freeze_time_ns,55_000_000_000)
        self.assertTrue((a==c.bandit.A).all())

