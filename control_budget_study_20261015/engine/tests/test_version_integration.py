import unittest
import numpy as np
from test_installation import received
from wsn.controller import Controller
from wsn.version_audit import reconstruct

CURRENT='linucb_event_scalar4_failure_current_retry_mask'
MIXED='linucb_event_scalar4_failure_retry_mask'


class GateIntegration(unittest.TestCase):
    def observation(self,n=20,failed=4):
        obs=received(30)
        for r in obs['reports']:
            if r['node']<2:
                r.update(n=100,failed=80,version=1,current_n=n,current_failed=failed)
        return obs

    def test_current_gate_ignores_old_failure_evidence(self):
        obs=self.observation(20,0)
        self.assertTrue(Controller(MIXED).view(obs)[4]['trigger_failure'])
        self.assertFalse(Controller(CURRENT).view(obs)[4]['trigger_failure'])

    def test_zero_is_unknown(self):
        event=Controller(CURRENT).view(self.observation(0,0))[4]
        self.assertFalse(event['trigger_failure'])
        self.assertIsNone(event['source_failure_reports']['0']['fraction'])

    def test_current_boundary(self):
        self.assertTrue(Controller(CURRENT).view(self.observation())[4]['trigger_failure'])
        self.assertFalse(Controller(CURRENT).view(self.observation(19,19))[4]['trigger_failure'])

    def test_missing_current_counter_does_not_fallback(self):
        obs=self.observation()
        for r in obs['reports']:
            r.pop('current_n',None)
        event=Controller(CURRENT).view(obs)[4]
        self.assertFalse(event['trigger_failure'])
        self.assertEqual(event['source_failure_reports']['0']['reason'],'counter_unavailable')

    def test_features_are_unchanged(self):
        obs=self.observation()
        self.assertEqual(Controller(CURRENT).view(obs)[3],Controller(MIXED).view(obs)[3])

    def test_invalid_current_counts_rejected(self):
        with self.assertRaises(ValueError):
            Controller(CURRENT).view(self.observation(20,21))


class OrderedAudit(unittest.TestCase):
    def fixture(self,completion_first):
        row=np.zeros(28,dtype=np.int64);row[5]=1;row[8]=1
        generated=dict(kind='generated',time_ns=0,flow=0,sequence=0,version=0,path=[0,2,3,9])
        completed=dict(kind='mac_job_completed',time_ns=1,node=0,flow=0,sequence=0,
                       generated_ns=0,generation_version=0,status=1)
        n=int(completion_first)
        report=dict(kind='report_generated',time_ns=1,report=dict(node=0,stamp_ns=1,version=0,
            n=n,mean_J_ns=n,cca=0,busy=0,failed=n,current_n=n,current_failed=n))
        return [generated]+([completed,report] if completion_first else [report,completed]),np.array([row])

    def test_tie_completion_before_sample(self):
        messages,jobs=self.fixture(True)
        _,r=reconstruct(messages,jobs,True)
        self.assertEqual(r['coincident_completions_in_reports'],1)

    def test_tie_sample_before_completion(self):
        messages,jobs=self.fixture(False)
        reports,_=reconstruct(messages,jobs,True)
        self.assertEqual(reports[0,1]['current_n'],0)

    def test_generation_version_corruption_rejected(self):
        messages,jobs=self.fixture(True)
        messages[1]['generation_version']=1
        with self.assertRaises(AssertionError):
            reconstruct(messages,jobs,True)

    def test_duplicate_terminal_rejected(self):
        messages,jobs=self.fixture(True)
        messages.insert(2,messages[1])
        with self.assertRaises(AssertionError):
            reconstruct(messages,jobs,True)

    def test_missing_terminal_rejected(self):
        messages,jobs=self.fixture(False)
        messages.pop()
        with self.assertRaises(AssertionError):
            reconstruct(messages,jobs,True)


if __name__=='__main__':unittest.main()
