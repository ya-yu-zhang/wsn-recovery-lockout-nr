import copy,unittest
import numpy as np
from wsn.feedback import ClosedBucketCache,BUCKET_NS
from wsn.controller import Controller
from test_installation import received

PREFIX='linucb_event_scalar4_failure_current_'

def source(node,stamp,buckets):
    return dict(node=node,stamp_ns=int(stamp*1e9),received_ns=int((stamp+.1)*1e9),buckets=buckets)

def snapshot(t,reports):return dict(time_ns=int(t*1e9),reports=reports,timely_buckets={str(b):[4,4] for b in (2,3,4)})

def pending():return dict(decision=1,time_ns=10_000_000_000,bucket=2,action=2,context=[1.]+[.2]*8,fe=16,install_budget_bytes=3996)

def early():
    return snapshot(30,[source(0,25.1,[[5,1],[4,5],[3,5],[2,5]]),source(1,20.1,[[4,0],[3,5],[2,5],[1,5]])])

def late():
    return snapshot(35,[source(0,30.1,[[6,1],[5,5],[4,5],[3,5]]),source(1,30.12,[[6,1],[5,5],[4,5],[3,5]])])

class CacheTests(unittest.TestCase):
    def test_open_bucket_excluded_at_positive_phase_offset(self):
        c=ClosedBucketCache();c.observe(snapshot(10,[source(0,5.1,[[1,2],[0,5],[2**32-1,0]])]))
        self.assertEqual(set(c.entries),{(0,0)})
    def test_exact_bucket_end_is_closed(self):
        c=ClosedBucketCache();c.observe(snapshot(10,[source(0,5,[[0,5]])]));self.assertIn((0,0),c.entries)
    def test_duplicate_preserves_first_visible_provenance(self):
        c=ClosedBucketCache();c.observe(early());old=copy.deepcopy(c.entries);c.observe(early());self.assertEqual(c.entries,old)
    def test_out_of_order_final_counts_accepted_without_replacing_provenance(self):
        c=ClosedBucketCache();c.observe(early());old=copy.deepcopy(c.entries[0,2]);c.observe(snapshot(31,[source(0,20.1,[[2,5]])]));self.assertEqual(c.entries[0,2],old)
    def test_conflicting_final_count_rejected(self):
        c=ClosedBucketCache();c.observe(early())
        with self.assertRaises(ValueError):c.observe(snapshot(31,[source(0,25.1,[[2,6]])]))
    def test_future_receipt_rejected(self):
        with self.assertRaises(ValueError):ClosedBucketCache().observe(snapshot(25,[source(0,25.1,[[2,5]])]))
    def test_cache_expiry_and_run_isolation(self):
        c=ClosedBucketCache();c.observe(early());c.observe(snapshot(100,[]));self.assertEqual(c.entries,{})
        self.assertEqual(ClosedBucketCache().entries,{})
    def test_source_identity_and_no_missing_imputation(self):
        c=ClosedBucketCache();c.observe(snapshot(30,[source(0,25.1,[[2,5],[3,5],[4,5]]),source(4,25.1,[[2,9],[3,9],[4,9]])]))
        counts,proof,missing=c.cohort([2,3,4]);self.assertEqual(counts,[15]);self.assertEqual(missing,[[],[2,3,4]])
        self.assertTrue(all(p['source']==0 for p in proof))
    def test_clock_regression_rejected(self):
        c=ClosedBucketCache();c.observe(early())
        with self.assertRaises(ValueError):c.observe(snapshot(29,[]))

class GraceTests(unittest.TestCase):
    def controller(self,mode='',cache20=False):
        c=Controller(PREFIX+(mode+'_' if mode else '')+('cache20_' if cache20 else 'grace5_')+'retry_mask');c.pending=pending();return c
    def settle(self,c,o):return c.feedback(o,{r['node']:r for r in o['reports']})
    def test_wait_then_combine_oldest_bucket_missing_from_latest_report(self):
        c=self.controller();self.assertIsNone(self.settle(c,early()));self.assertEqual(c.bandit.updates,[0]*4)
        f=self.settle(c,late());self.assertEqual(f['offered'],[15,15]);self.assertTrue(f['recovered_after_wait'])
        self.assertEqual(f['extra_wait_ns'],BUCKET_NS);self.assertEqual(f['charged_install_budget_bytes'],3996)
        self.assertEqual(c.bandit.updates,[0,0,1,0]);self.assertEqual(len(f['bucket_evidence']),6)
    def test_missing_at_deadline_still_missing(self):
        c=self.controller();self.settle(c,early());o=snapshot(35,early()['reports']);f=self.settle(c,o)
        self.assertIsNone(f['reward']);self.assertIsNone(c.pending);self.assertEqual(c.bandit.updates,[0]*4)
        self.assertEqual(f['missing_closed_buckets'],[[],[4]])
    def test_no_wait_when_cohort_complete_at_original_due_time(self):
        c=self.controller();o=early();o['reports'][1]=source(1,25.12,[[5,0],[4,5],[3,5],[2,5]])
        f=self.settle(c,o);self.assertEqual(f['extra_wait_ns'],0);self.assertEqual(c.feedback_waits,[])
    def test_cache_without_grace_cannot_fill_unreceived_bucket(self):
        c=self.controller(cache20=True);f=self.settle(c,early());self.assertIsNone(f['reward']);self.assertIsNone(c.pending)
    def test_frozen_uses_valid_feedback_without_training(self):
        c=self.controller('frozen');self.settle(c,early());f=self.settle(c,late())
        self.assertIsNotNone(f['reward']);self.assertIsNone(f['updated_action']);self.assertTrue(np.array_equal(c.bandit.A[2],np.eye(9)))
    def test_reward_equal_across_all_controls(self):
        rewards=[]
        for mode in ('','random','intercept','frozen'):
            c=self.controller(mode);self.settle(c,early());rewards.append(self.settle(c,late())['reward'])
        self.assertEqual(len(set(rewards)),1)
    def test_final_feedback_only_once(self):
        c=self.controller();self.settle(c,early());self.settle(c,late());self.assertIsNone(self.settle(c,late()));self.assertEqual(len(c.feedbacks),1)
    def test_empty_finalized_cohort_does_not_wait(self):
        c=self.controller();o=early();o['timely_buckets']={}
        o['reports']=[source(f,25.1,[[2,0],[3,0],[4,0]]) for f in (0,1)]
        f=self.settle(c,o);self.assertEqual(f['missing_reason'],'empty offered cohort');self.assertEqual(c.feedback_waits,[])
    def test_pending_grace_blocks_observed_event_without_new_packets(self):
        c=self.controller();o=received(30)
        for r in o['reports']:
            if r['node']==1:r.update(stamp_ns=20_100_000_000,received_ns=20_200_000_000,buckets=[[4,0],[3,5],[2,5],[1,5]])
            if r['node']==0:r.update(current_n=20,current_failed=4)
        cmd,row=c.step(o);self.assertEqual(cmd,'-1 0 0');self.assertIsNone(row['decision']);self.assertIsNone(row['feedback'])
        self.assertTrue(row['feedback_wait']['observed_event_blocked']);self.assertEqual(row['feedback_wait']['extra_packets_requested'],0)

if __name__=='__main__':unittest.main()
