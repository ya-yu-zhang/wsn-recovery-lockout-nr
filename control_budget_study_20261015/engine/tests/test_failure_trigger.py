import unittest,math
from wsn.controller import Controller,INITIAL
from wsn.topology import geometry
from test_installation import received

class FailureTests(unittest.TestCase):
    def signal(self,t,n=100,failed=30):
        o=received(t)
        for r in o['reports']:
            if r['node']<2:r.update(n=n,failed=failed,version=1)
        return o
    def test_failure_enables_event_without_busy_or_missing(self):
        c=Controller('linucb_event_scalar4_failure_retry_mask');c.step(received(10));_,row=c.step(self.signal(30))
        self.assertTrue(row['event']['trigger_failure']);self.assertEqual(row['event']['missing'],0);self.assertIsNotNone(row['decision'])
    def test_matched_original_does_not_trigger_from_failed_field(self):
        c=Controller('linucb_event_scalar4_retry_mask');c.step(received(10));_,row=c.step(self.signal(30))
        self.assertTrue(row['event']['transmission_failure']);self.assertFalse(row['event']['trigger_failure']);self.assertIsNone(row['decision'])
    def test_minimum_samples(self):
        c=Controller('linucb_event_scalar4_failure_retry_mask');self.assertFalse(c.view(self.signal(30,n=19,failed=19))[4]['trigger_failure'])
    def test_registered_boundary(self):
        c=Controller('linucb_event_scalar4_failure_retry_mask');self.assertTrue(c.view(self.signal(30,n=20,failed=4))[4]['trigger_failure']);self.assertFalse(c.view(self.signal(30,n=20,failed=3))[4]['trigger_failure'])
    def test_expired_report_not_failure_truth(self):
        o=self.signal(30)
        for r in o['reports']:
            if r['node']<2:r['stamp_ns']=10_000_000_000;r['received_ns']=11_000_000_000
        self.assertFalse(Controller('linucb_event_scalar4_failure_retry_mask').view(o)[4]['trigger_failure'])
    def test_invalid_failure_counts_rejected(self):
        with self.assertRaises(ValueError):Controller('linucb_event_scalar4_failure_retry_mask').view(self.signal(30,n=20,failed=21))
    def test_pending_transaction_not_preempted(self):
        c=Controller('linucb_event_scalar4_failure_retry_mask');c.step(received(10));cmd,row=c.step(self.signal(15))
        self.assertTrue(row['event']['trigger_failure']);self.assertIsNone(row['decision']);self.assertEqual(len(c.logs),1)
    def test_topology_prior_and_runtime_state_are_isolated(self):
        a=Controller('linucb_event_scalar4_retry_mask',points=geometry('base'));b=Controller('linucb_event_scalar4_retry_mask',points=geometry('jitter_a'))
        self.assertNotEqual(a.points,b.points);a.memory.append(((0,4,5,9),(1,4,5,9)));self.assertEqual(len(b.memory),1)
        for c in (a,b):
            for pair in c.catalog:
                for p in pair:self.assertTrue(all(math.dist(c.points[u],c.points[v])<=65 for u,v in zip(p,p[1:])))
    def test_rule_uses_failure_recovery_arm(self):
        c=Controller('event_rule_scalar_failure_retry_mask');c.step(received(10));_,row=c.step(self.signal(30));self.assertEqual(row['decision']['action'],2)

if __name__=='__main__':unittest.main()
