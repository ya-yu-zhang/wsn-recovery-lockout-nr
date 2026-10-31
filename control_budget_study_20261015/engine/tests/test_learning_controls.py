import unittest
import numpy as np
from wsn.controller import Controller
from wsn.base_controller import LinUCB,InterceptLinUCB
from wsn.version_audit import reconstruct
from test_installation import received

PREFIX='linucb_event_scalar4_failure_current_'


class LearningControls(unittest.TestCase):
    def feedback(self,mode):
        policy=PREFIX+(mode+'_' if mode else '')+'retry_mask'
        c=Controller(policy)
        c.pending=dict(decision=1,time_ns=10_000_000_000,bucket=2,action=0,
                       context=[1.,.2,.3,.4,.5,.6,.7,.8,.9],fe=8,install_budget_bytes=1998)
        obs=received(30)
        reports={r['node']:r for r in obs['reports']}
        for r in reports.values():
            r['stamp_ns']=25_000_000_000;r['buckets']=[[2,20],[3,20],[4,20],[5,20]]
        obs['timely_buckets']={str(b):[10,10] for b in (2,3,4)}
        fb=c.feedback(obs,reports)
        return c,fb

    def test_feedback_reward_identical_across_controls(self):
        rewards=[self.feedback(m)[1]['reward'] for m in ('','random','intercept','frozen')]
        self.assertEqual(len(set(rewards)),1)

    def test_frozen_skips_update_but_keeps_valid_feedback(self):
        c,fb=self.feedback('frozen')
        self.assertIsNotNone(fb['reward']);self.assertIsNone(fb['updated_action'])
        self.assertEqual(c.bandit.updates,[0]*4)
        self.assertTrue(np.array_equal(c.bandit.A[0],np.eye(9)))
        self.assertFalse(c.pending)

    def test_intercept_projects_update_and_scores(self):
        c,_=self.feedback('intercept')
        expected=np.eye(9);expected[0,0]=2
        self.assertTrue(np.array_equal(c.bandit.A[0],expected))
        self.assertEqual(c.bandit.b[0,1:].tolist(),[0.]*8)
        self.assertEqual(c.bandit.scores([1.]+[0.]*8),c.bandit.scores([1.]+[100.]*8))

    def test_full_model_uses_context(self):
        c,fb=self.feedback('')
        self.assertEqual(c.bandit.updates,[1,0,0,0]);self.assertEqual(fb['updated_action'],0)
        self.assertGreater(c.bandit.A[0,1,1],1)

    def test_random_has_shadow_updates_without_score_selection(self):
        c,fb=self.feedback('random')
        self.assertEqual(c.bandit.updates,[1,0,0,0]);self.assertEqual(c.selection_mode,'random')

    def test_long_horizon_allows_late_decision(self):
        late=Controller('force1',action_stop_ns=320_000_000_000)
        self.assertIsNotNone(late.step(received(100))[1]['decision'])
        self.assertIsNone(Controller('force1').step(received(100))[1]['decision'])

    def test_intercept_and_full_initialization_match(self):
        a=LinUCB();b=InterceptLinUCB()
        self.assertTrue(np.array_equal(a.A,b.A));self.assertTrue(np.array_equal(a.b,b.b))

    def test_controls_share_exploration_and_protocol(self):
        cs=[Controller(PREFIX+(m+'_' if m else '')+'retry_mask') for m in ('','random','intercept','frozen')]
        self.assertEqual({c.exploration_cap for c in cs},{4})
        self.assertEqual({c.retry_limit for c in cs},{2})
        self.assertEqual({c.search_mode for c in cs},{'scalar'})


class SourceOnlyAudit(unittest.TestCase):
    def relay(self,extra):
        report=dict(node=2,stamp_ns=1,version=0,n=0,mean_J_ns=0,cca=0,busy=0,failed=0)
        if extra:report.update(current_n=0,current_failed=0)
        return [dict(kind='report_generated',time_ns=1,report=report)],np.empty((0,28),dtype=np.int64)

    def test_relay_without_unused_counters(self):
        messages,jobs=self.relay(False)
        r,_=reconstruct(messages,jobs,True,True)
        self.assertNotIn('current_n',r[2,1])

    def test_unexpected_relay_counter_rejected(self):
        messages,jobs=self.relay(True)
        with self.assertRaises(AssertionError):reconstruct(messages,jobs,True,True)


if __name__=='__main__':unittest.main()
