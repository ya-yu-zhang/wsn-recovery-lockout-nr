import unittest
from wsn.installation import Installation
from wsn.controller import Controller,INITIAL
from wsn.multiobjective import objectives,merit
from wsn.base_controller import POINTS
from test_base_controller import obs

def received(t,versions=(0,0)):
    o=obs(t)
    for r in o['reports']:
        if r['node']<2:r['version']=versions[r['node']]
        r['buckets']=[[b,5] for b in range(int((t-1)//5)-3,int((t-1)//5)+1)]
    return o

class InstallationTests(unittest.TestCase):
    def test_target_only_unconfirmed_source(self):
        i=Installation(1,10_000_000_000,INITIAL,2);r=i.observe(received(15,(1,0)))
        self.assertEqual(r['retry_sources'],[1]);self.assertEqual(r['retry_counts'],[0,1])
    def test_no_retry_before_timeout(self):
        i=Installation(1,10_000_000_000,INITIAL,2);self.assertEqual(i.observe(received(10))['retry_sources'],[])
    def test_retry_spacing_prevents_repeated_same_tick(self):
        i=Installation(1,10_000_000_000,INITIAL,2);i.observe(received(15));self.assertEqual(i.observe(received(16))['retry_sources'],[])
    def test_exact_cap_and_terminal(self):
        i=Installation(1,10_000_000_000,INITIAL,2)
        self.assertEqual(i.observe(received(15))['retry_sources'],[0,1]);self.assertEqual(i.observe(received(20))['retry_sources'],[0,1])
        r=i.observe(received(25));self.assertEqual(r['retry_sources'],[]);self.assertEqual(r['outcome'],'confirmation_timeout');self.assertIsNone(i.observe(received(30)))
    def test_stale_confirmation_does_not_succeed(self):
        i=Installation(1,10_000_000_000,INITIAL,2);o=received(25,(1,1))
        for r in o['reports']:r['stamp_ns']=11_000_000_000;r['received_ns']=12_000_000_000
        self.assertEqual(i.observe(o)['outcome'],'confirmation_timeout')
    def test_confirmation_requires_exact_version(self):
        i=Installation(1,10_000_000_000,INITIAL,2);self.assertEqual(i.observe(received(15,(2,0)))['missing_sources'],[0,1])
    def test_confirmed_sources_are_not_retried_after_report_expires(self):
        i=Installation(1,10_000_000_000,INITIAL,2);i.observe(received(15,(1,0)));o=received(20);o['reports']=[r for r in o['reports'] if r['node']!=0]
        self.assertEqual(i.observe(o)['retry_sources'],[1])
    def test_observed_success_closes_without_retry(self):
        i=Installation(1,10_000_000_000,INITIAL,2);r=i.observe(received(15,(1,1)));self.assertTrue(r['closed']);self.assertEqual(r['retry_sources'],[])
    def test_missing_reports_remain_unconfirmed(self):
        i=Installation(1,10_000_000_000,INITIAL,0);o=received(25);o['reports']=[];r=i.observe(o)
        self.assertEqual(r['outcome'],'confirmation_timeout');self.assertEqual(r['confirmations'],{})
    def test_future_confirmation_rejected(self):
        i=Installation(1,10_000_000_000,INITIAL,2);o=received(15,(1,1));o['reports'][0]['received_ns']=16_000_000_000
        with self.assertRaises(ValueError):i.observe(o)
    def test_retry_charged_to_same_action_without_new_fe(self):
        c=Controller('linucb_event_scalar4_retry_mask');c.step(received(10));a=c.logs[0]['action'];cmd,row=c.step(received(15,(1,0)))
        self.assertTrue(cmd.startswith('-2 1 0 2 '));self.assertEqual(row['retry']['sources'],[1]);self.assertEqual(len(c.logs),1);self.assertEqual(c.logs[0]['action'],a);self.assertEqual(c.logs[0]['install_budget_bytes'],2997);self.assertEqual(c.bandit.updates,[0]*4)
    def test_retry_feedback_includes_whole_transaction_cohort(self):
        c=Controller('linucb_event_scalar4_retry_mask');c.step(received(10));c.step(received(15,(1,0)));c.step(received(20,(1,1)));c.step(received(25,(1,1)))
        o=received(30,(1,1));o['timely_buckets']={'2':[4,4],'3':[4,4],'4':[4,4]};_,row=c.step(o);f=row['feedback']
        self.assertEqual(f['offered'],[15,15]);self.assertEqual(f['timely'],[12,12]);self.assertEqual(f['charged_install_budget_bytes'],2997);self.assertEqual(sum(c.bandit.updates),1)
    def test_missing_cohort_no_learning(self):
        c=Controller('linucb_event_scalar4_retry_mask');c.step(received(10));o=received(30);o['reports']=[r for r in o['reports'] if r['node']!=1];c.step(o)
        self.assertIsNone(c.feedbacks[0]['reward']);self.assertEqual(sum(c.bandit.updates),0)
    def test_unknown_risk_not_zero(self):
        c=Controller('linucb_mask');_,f,a,_,_=c.view(obs())
        for r in f.values():r.update(n=0,depth=0,busy=0,cca=0,mean_J_ns=0)
        self.assertEqual(objectives(INITIAL,f,a,POINTS)[:2],(0.,0.));self.assertEqual(objectives(INITIAL,f,a,POINTS,unknown=True)[:2],(.25,.25))
    def test_uncertainty_decreases_with_sample_count(self):
        c=Controller('linucb_mask');_,f,a,_,_=c.view(obs())
        for r in f.values():r.update(n=1)
        x=objectives(INITIAL,f,a,POINTS,unknown=True)
        for r in f.values():r.update(n=100)
        y=objectives(INITIAL,f,a,POINTS,unknown=True);self.assertGreater(x[0],y[0])
    def test_risk_first_changes_registered_preference(self):
        a=(.1,.1,.6);b=(.2,.2,.4);self.assertGreater(merit(a,'pareto'),merit(b,'pareto'));self.assertLess(merit(a,'riskfirst'),merit(b,'riskfirst'))
    def test_action_stop_has_no_new_late_decision(self):
        c=Controller('linucb_event_risk4_unknown_retry_mask');cmd,row=c.step(received(80));self.assertEqual(cmd,'-1 0 0');self.assertIsNone(row['decision'])

if __name__=='__main__':unittest.main()
