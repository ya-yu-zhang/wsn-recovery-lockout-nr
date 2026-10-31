import copy,json,unittest
from wsn.fork_controller import ForkController,digest,eligibility,clean
from tests.test_safety_control import observation
from run_mechanisms import policy
class ForkDiagnosisTests(unittest.TestCase):
    def test_snapshot_hash_ignores_host_clock(self):
        self.assertEqual(digest({'compute_wall_ns':1,'x':[1,2]}),digest({'compute_wall_ns':900,'x':[1,2]}))
    def test_snapshot_hash_changes_with_received_evidence(self):
        self.assertNotEqual(digest({'reports':[{'version':1}]}),digest({'reports':[{'version':2}]}))
    def test_audit_replay_crosses_same_json_boundary(self):
        from audit_closed_loop import clean as audit_clean
        c=ForkController(policy('resource10_on'));_,row=c.step(observation(10))
        saved=json.loads(json.dumps(row))
        self.assertIn('0',saved['fork_candidate']['snapshot']['visible_versions'])
        self.assertEqual(audit_clean(row),audit_clean(saved))
    def test_all_arms_must_have_common_feasible_pool(self):
        self.assertEqual(eligibility([True]*4,False,True,False,True),[])
        self.assertIn('not_all_arms_feasible',eligibility([True,False,True,True],False,True,False,True))
        self.assertIn('candidate_pools_differ',eligibility([True]*4,False,True,False,False))
    def test_open_transaction_and_used_budget_are_not_forked(self):
        r=eligibility([True]*4,True,False,True,True)
        self.assertEqual(set(r),{'pending_transaction','installation_open','install_budget_used'})
    def test_fork_specification_validation(self):
        with self.assertRaises(ValueError):ForkController(policy('resource10_on'),fork_arm=1)
        with self.assertRaises(ValueError):ForkController(policy('resource10_on'),fork_time_ns=10,fork_arm=4)
    def test_reference_and_branch_have_identical_pre_fork_core(self):
        a=ForkController(policy('resource10_on'));b=ForkController(policy('resource10_on'),fork_time_ns=20_000_000_000,fork_arm=3)
        o=observation(10);ra,sa=a.step(copy.deepcopy(o));rb,sb=b.step(copy.deepcopy(o));self.assertEqual(ra,rb)
        for key in ('fork_control','fork_candidate'):sa.pop(key);sb.pop(key)
        self.assertEqual(clean(sa),clean(sb))
    def test_initial_fork_changes_one_action_and_cutoff(self):
        c=ForkController(policy('resource10_on'),fork_time_ns=10_000_000_000,fork_arm=3)
        _,s=c.step(observation(10));self.assertEqual(s['decision']['action'],3);self.assertEqual(c.action_stop_ns,10_000_000_001)
        self.assertIsNotNone(c.fork_info);self.assertEqual(c.bandit.updates,[0]*4)
    def test_closed_installation_cutoff_does_not_cancel_retry(self):
        c=ForkController(policy('resource10_on'),fork_time_ns=10_000_000_000,fork_arm=1)
        initial=observation(10);o=observation(15)
        for obs in (initial,o):
            for report in obs['reports']:
                if report['node']<2:report['version']=0
        _,first=c.step(initial);self.assertIsNotNone(first['decision']['paths']);reply,s=c.step(o)
        self.assertTrue(reply.startswith('-2 '));self.assertIsNone(s['decision']);self.assertIsNotNone(s['retry'])
