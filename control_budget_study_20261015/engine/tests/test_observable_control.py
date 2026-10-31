import copy,subprocess,tempfile,unittest
from pathlib import Path
from wsn.controller import Controller,INITIAL
from wsn.observable_controller import BoundedInstallation
from tests.test_aligned_feedback import POLICY
from tests.test_safety_control import observation

class ObservableTests(unittest.TestCase):
    def installation(self):return BoundedInstallation(1,10_000_000_000,INITIAL)
    def obs(self,t,versions=(0,0)):
        o=observation(t)
        for r in o['reports']:
            if r['node']<2:r['version']=versions[r['node']]
        return o
    def test_missing_confirmation_exits_without_claiming_failure(self):
        i=self.installation();row=i.observe(self.obs(20));self.assertEqual(row['outcome'],'abandoned_unconfirmed');self.assertEqual(row['retry_sources'],[])
        self.assertIn('no assertion of physical failure',row['exit_scope'])
    def test_deadline_does_not_require_fresh_source_reports(self):
        i=self.installation();o=self.obs(20);o['reports']=[];self.assertEqual(i.observe(o)['outcome'],'abandoned_unconfirmed')
    def test_one_retry_is_targeted_only_to_unconfirmed_source(self):
        i=self.installation();a=i.observe(self.obs(15,(1,0)));self.assertEqual(a['retry_sources'],[1]);b=i.observe(self.obs(16,(1,0)));self.assertEqual(b['retry_sources'],[])
    def test_matching_confirmation_at_deadline_has_priority(self):
        i=self.installation();r=i.observe(self.obs(20,(1,1)));self.assertEqual(r['outcome'],'confirmed');self.assertFalse(r['late_confirmation'])
    def test_late_two_source_reports_reconcile_abandoned_route(self):
        i=self.installation();i.observe(self.obs(20));r=i.observe(self.obs(25,(1,1)));self.assertTrue(r['late_confirmation']);self.assertEqual(r['outcome'],'confirmed')
    def test_late_partial_confirmation_never_marks_route_confirmed(self):
        i=self.installation();i.observe(self.obs(20));self.assertIsNone(i.observe(self.obs(25,(1,0))));self.assertEqual(i.outcome,'abandoned_unconfirmed')
    def test_predecision_and_old_version_reports_cannot_confirm(self):
        i=self.installation();o=self.obs(15,(1,1))
        for r in o['reports']:
            if r['node']<2:r['stamp_ns']=9_000_000_000
        self.assertEqual(i.observe(o)['missing_sources'],[0,1])
    def test_future_confirmation_is_rejected(self):
        i=self.installation();o=self.obs(15,(1,1));o['reports'][0]['received_ns']=16_000_000_000
        with self.assertRaises(ValueError):i.observe(o)
    def test_score_only_suppresses_forced_exposures_not_ucb(self):
        policy=POLICY.replace('_aligned_','_aligned_safe_interrupt_installbudget_transaction_txguard_observable_scoreonly_installexit_')
        c=Controller(policy);self.assertEqual(c.exploration_cap,0);self.assertEqual(c.exploration_candidates([0,1,2,3],[]),[]);self.assertEqual(c.bandit.alpha,.6)
    def test_installation_exit_is_censored_and_does_not_train(self):
        policy=POLICY.replace('_aligned_','_aligned_safe_interrupt_installbudget_transaction_txguard_observable_scoreonly_installexit_')
        c=Controller(policy);c.sequence=1;c.version_paths[1]=INITIAL;c.installation=self.installation()
        c.pending=dict(decision=1,time_ns=10_000_000_000,bucket=2,action=2,context=[1,0,.2,0,0,1],fe=16,install_budget_bytes=1998,paths=INITIAL,reward_expected_versions=[1,1])
        _,r=c.step(self.obs(20));self.assertEqual(r['feedback']['exit_kind'],'installation_budget_exit');self.assertIsNone(r['feedback']['reward']);self.assertEqual(c.bandit.updates,[0]*4)
    def test_native_schedule_bounds_and_source_freshness(self):
        code=r'''
        #include "wsn-local-report.h"
        #include <cassert>
        int main(){
          for(unsigned previous=0;previous<16;previous++)for(unsigned state=0;state<16;state++){
            for(int seconds=5;seconds<=15;seconds+=5){
              auto q=localreport::Select(false,1000000000LL+seconds*1000000000LL,1000000000LL,state,previous);
              if(seconds<10)assert(!q.emit);
              if(seconds==15)assert(q.emit);
              if(state==previous&&seconds<15)assert(!q.emit);
            }
            auto s=localreport::Select(true,6000000000LL,1000000000LL,state,previous);
            assert(s.emit&&s.period==5&&!s.urgent);
          }
          assert(localreport::State(0,0,0,false)==0);
          assert(localreport::State(16,100,35,true)==11);
          assert(localreport::State(16,100,36,true)==15);
          assert(localreport::Select(false,1000000000LL,0,0,0).emit);
        }'''
        with tempfile.TemporaryDirectory()as folder:
            p=Path(folder);(p/'test.cc').write_text(code)
            subprocess.run(['g++','-std=c++20','-I',str(Path(__file__).resolve().parents[1]/'ns3'),str(p/'test.cc'),'-o',str(p/'test')],check=True,capture_output=True)
            subprocess.run([str(p/'test')],check=True)
