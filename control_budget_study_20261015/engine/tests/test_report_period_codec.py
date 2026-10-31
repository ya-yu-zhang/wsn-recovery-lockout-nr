import subprocess, tempfile, unittest
from pathlib import Path
from wsn.controller import Controller

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'linucb_event_scalar4_failure_current_ops_ctx6_noop_cache20_retry_freshfixed_mask'


class GuardedReportingTests(unittest.TestCase):
    def test_all_wire_depths_and_legacy_tags(self):
        code = r'''
#include "report_period_codec.h"
#include <cassert>
int main() {
 for (unsigned depth=0;depth<=0x3fff;depth++)
  for (auto period:{5,10,15,20}) {
   auto packed=guarded::PackReportDepth(depth,period);
   assert(guarded::ReportDepth(packed)==depth);
   assert(guarded::ReportPeriod(packed)==period);
   if(period!=15) assert(packed==(depth|(period==10?0x8000:period==20?0x4000:0)));
  }
 bool rejected=false;
 try {guarded::PackReportDepth(0x4000,15);} catch(const std::invalid_argument&) {rejected=true;}
 assert(rejected);rejected=false;
 try {guarded::PackReportDepth(0,12);} catch(const std::invalid_argument&) {rejected=true;}
 assert(rejected);
}
'''
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'codec.cc').write_text(code)
            subprocess.run(['g++','-std=c++17','-I',str(ROOT/'ns3'),str(p/'codec.cc'),'-o',str(p/'codec')],check=True,capture_output=True)
            subprocess.run([str(p/'codec')],check=True,capture_output=True)

    def test_reporting_bound_including_lease_transitions(self):
        # Arbitrary on/off transitions can break a global-modulus schedule.
        periods=[10,15,15,10,15,10,10]
        old=[slot*5 for slot,p in enumerate(periods) if slot%(p//5)==0]
        self.assertEqual(old,[0,30])
        for pattern in range(1<<14):
            emitted=[0];last=0
            for slot in range(1,15):
                period=10 if pattern&(1<<(slot-1)) else 15
                if slot*5-last>=period:last=slot*5;emitted.append(last)
            self.assertLessEqual(max(b-a for a,b in zip(emitted,emitted[1:])),15)

    def test_fixed_freshness_is_retained(self):
        c=Controller(POLICY,'lease10_15')
        self.assertEqual(c.fresh_limit(2,{'period_s':15}),16_000_000_000)
        self.assertEqual(c.fresh_limit(0,{'period_s':5}),8_000_000_000)


if __name__=='__main__':unittest.main()
