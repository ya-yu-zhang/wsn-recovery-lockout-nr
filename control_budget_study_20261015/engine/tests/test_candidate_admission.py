import copy,unittest
from wsn.controller import Controller,INITIAL
from wsn.candidate_controller import candidate_gate
from wsn.learning_controller import exposure_gate
from tests.test_safety_control import observation

POLICY='linucb_event_scalar4_failure_current_ops_epoch_aligned_safe_interrupt_installbudget_transaction_txguard_observable_installexit_learnstudy_candidate2_gated_ctx6_noop_cache20_retry_freshfixed_mask'
def ready(failed=True):
    c=Controller(POLICY,'local15_event');c.sequence=1;c.version_paths[1]=INITIAL;c.current_observation=observation(55,failed=failed)
    c.feedbacks=[dict(decision=1,reward=.8,action=0,time_ns=50_000_000_000)]
    c.service_evidence={'known':False,'reason':'unobserved'}
    c.candidate_witnesses={str(a):((0,4,5,9),(1,4,5,9)) for a in range(4)}
    return c
class CandidateAdmissionTests(unittest.TestCase):
    def test_recent_regular_feedback_does_not_start_exposure_cooldown(self):
        c=ready();self.assertIn('transaction_cooldown',exposure_gate(c,[1,2,3])['reasons'])
        self.assertTrue(candidate_gate(c,[1,2,3])['admitted'])
    def test_fresh_candidate_survives_missing_current_relay(self):
        c=ready();c.current_observation['reports']=[r for r in c.current_observation['reports'] if r['node']!=2]
        self.assertIn('congestion_unknown',exposure_gate(c,[1,2,3])['reasons'])
        self.assertTrue(candidate_gate(c,[1,2,3])['admitted'])
    def test_unmeasured_candidate_relays_are_explicit_not_low(self):
        c=ready()
        for r in c.current_observation['reports']:
            if r['node'] in (4,5):r['cca']=r['busy']=0
        g=candidate_gate(c,[1]);self.assertTrue(g['admitted']);self.assertEqual(g['unmeasured_candidate_relays']['1'],[4,5])
        self.assertIn('not low congestion',g['uncertainty_scope'])
    def test_poor_received_service_can_trigger_without_source_failure(self):
        c=ready(False);c.service_evidence={'known':True,'worst_timely':.7}
        self.assertTrue(candidate_gate(c,[1])['admitted'])
    def test_unknown_service_is_not_poor_service(self):
        c=ready(False);c.service_evidence={'known':False,'worst_timely':0}
        self.assertIn('no_received_failure_or_service_deficit',candidate_gate(c,[1])['reasons'])
    def test_no_counterfactual_truth_input(self):
        c=ready(False);c.current_observation['physical_fault_truth']=[2]
        self.assertFalse(candidate_gate(c,[1])['admitted'])
    def test_stale_candidate_witness_is_not_eligible(self):
        c=ready();c.current_observation['reports']=[r for r in c.current_observation['reports'] if r['node']!=4]
        self.assertEqual(candidate_gate(c,[1])['eligible'],[])
    def test_unknown_source_channel_blocks_primary_but_is_logged_for_plain(self):
        c=ready();c.current_observation['reports'][0]['cca']=0
        self.assertIn('source_congestion_unknown',candidate_gate(c,[1])['reasons'])
        g=candidate_gate(c,[1],plain=True);self.assertTrue(g['admitted']);self.assertFalse(g['source_congestion_known'])
    def test_busy_source_still_blocks_primary(self):
        c=ready();c.current_observation['reports'][0]['busy']=6
        self.assertFalse(candidate_gate(c,[1])['admitted'])
    def test_source_queue_still_blocks_primary(self):
        c=ready();c.current_observation['reports'][1]['depth']=3
        self.assertIn('source_queue_above_two',candidate_gate(c,[1])['reasons'])
    def test_censored_exposure_consumes_arm_and_cooldown(self):
        c=ready();c.logs=[dict(decision=2,selection_phase='event_exploration')];c.event_attempts=[2]
        c.feedbacks.append(dict(decision=2,time_ns=50_000_000_000,reward=None,action=2))
        g=candidate_gate(c,[1,2,3]);self.assertNotIn(2,g['eligible']);self.assertIn('exposure_transaction_cooldown',g['reasons'])
    def test_old_exposure_closure_releases_cooldown(self):
        c=ready();c.logs=[dict(decision=2,selection_phase='event_exploration')];c.event_attempts=[2]
        c.feedbacks.append(dict(decision=2,time_ns=30_000_000_000,reward=None,action=2))
        self.assertTrue(candidate_gate(c,[1,2,3])['admitted'])
    def test_credited_arm_cannot_be_exposed(self):
        c=ready();c.feedbacks.append(dict(decision=2,reward=.9,action=1,time_ns=20_000_000_000))
        self.assertNotIn(1,candidate_gate(c,[1,2,3])['eligible'])
    def test_spent_installation_budget_is_retained(self):
        c=ready();c.reservations[2]=1
        self.assertIn('installation_budget_used',candidate_gate(c,[1])['reasons'])
