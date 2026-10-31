import math,subprocess,tempfile,unittest
from pathlib import Path
from tools.audit_selective_retry import audit_messages
from wsn.topology import geometry
class SelectiveRetryTests(unittest.TestCase):
    def compile_check(self,body):
        header=Path(__file__).resolve().parents[1]/'ns3'
        with tempfile.TemporaryDirectory()as td:
            p=Path(td);(p/'check.cc').write_text('#include "selective_report_retry.h"\n#include <cassert>\nint main(){'+body+'}')
            subprocess.run(['g++','-std=c++20','-I',str(header),str(p/'check.cc'),'-o',str(p/'check')],check=True)
            subprocess.run([str(p/'check')],check=True)
    def test_duplicates_do_not_consume_protection(self):
        self.compile_check('selective::VersionProtection p;assert(p.Observe(4,0,0,5));assert(p.Observe(4,0,0,5));assert(p.Observe(4,0,0,10));assert(!p.Observe(4,0,0,15));')
    def test_version_reset_and_stale_version_do_not_regress(self):
        self.compile_check('selective::VersionProtection p;p.Observe(4,0,1,5);p.Observe(4,0,1,10);assert(p.Observe(4,0,2,15));assert(!p.Observe(4,0,1,20));assert(p.Protected(4,0,2,15));assert(p.Observe(4,0,2,20));assert(!p.Observe(4,0,2,25));')
    def test_nodes_and_sources_are_local_and_independent(self):
        self.compile_check('selective::VersionProtection p;p.Observe(4,0,0,5);p.Observe(4,0,0,10);assert(!p.Observe(4,0,0,15));assert(p.Observe(4,1,0,15));assert(p.Observe(5,0,0,15));assert(!p.Observe(5,2,0,15));assert(!p.Protected(6,0,0,15));')
    def test_queue_boundary_and_critical_ablation(self):
        self.compile_check('using namespace selective;assert(Allow(Mode::Queue,false,4));assert(!Allow(Mode::Queue,true,5));assert(Allow(Mode::CriticalQueue,true,5));assert(!Allow(Mode::CriticalQueue,false,5));assert(Allow(Mode::Always,false,16));')
    def messages(self):
        return [dict(kind='report_generated',time_ns=5,report=dict(node=0,stamp_ns=5,version=1)),dict(kind='report_local_observation',time_ns=6,node=4,source=0,stamp_ns=5,version=1,critical=True)]
    def test_audit_rejects_false_critical_observation(self):
        m=self.messages();m[-1]['critical']=False
        with self.assertRaises(AssertionError):audit_messages(m,'critical_queue',True)
    def test_audit_rejects_unaccounted_queue_depth(self):
        m=self.messages()+[dict(kind='report_retry_classified',time_ns=7,node=4,source=0,stamp_ns=5,version=1,parent_sequence=1,critical=True,waiting_depth=5,mode='critical_queue',admitted=True)]
        with self.assertRaises(AssertionError):audit_messages(m,'critical_queue',True)
    def congested(self,mode,admitted):
        m=self.messages()+[dict(kind='queue_arrival',time_ns=6,node=4,flow=0,sequence=k,accepted=True)for k in range(5)]
        m.append(dict(kind='report_retry_classified',time_ns=7,node=4,source=0,stamp_ns=5,version=1,parent_sequence=1,critical=True,waiting_depth=5,mode=mode,admitted=admitted))
        return m
    def test_queue_ablation_suppresses_even_critical_congested_report(self):
        r=audit_messages(self.congested('queue',False),'queue',True)
        self.assertEqual(r['congested_suppressed'],1);self.assertEqual(r['critical_congested_policy_admitted'],0)
    def test_protected_retry_still_requires_original_budget(self):
        m=self.congested('critical_queue',True)
        with self.assertRaises(AssertionError):audit_messages(m,'critical_queue',True)
        m.append(dict(kind='report_budget_admission',time_ns=7,node=4,parent_sequence=1,admitted=False))
        r=audit_messages(m,'critical_queue',True);self.assertEqual(r['critical_congested_policy_admitted'],1);self.assertEqual(r['critical_congested_retries_scheduled'],0)
    def test_reserved_geometries_are_valid_without_service_outcomes(self):
        for s in range(1032301,1032305):
            g=geometry('protect_'+str(s));self.assertEqual(g,geometry('protect_'+str(s)))
            for a,b in ((0,2),(1,2),(2,3),(3,9)):self.assertLessEqual(math.dist(g[a],g[b]),55)
    def test_unregistered_protection_geometry_is_rejected(self):
        with self.assertRaises(ValueError):geometry('protect_1032305')
