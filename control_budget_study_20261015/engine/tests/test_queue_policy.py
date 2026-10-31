import subprocess,tempfile,unittest
from pathlib import Path
class QueuePolicyTests(unittest.TestCase):
 def test_bounded_overtaking_age_fifo_and_epoch_rounding(self):
  header=Path(__file__).resolve().parents[1]/'ns3'
  code='''#include "report_queue_policy.h"
  #include <cassert>
  int main(){using namespace epoch;
   std::vector<Entry> q={{false,0},{false,0},{true,0},{true,0}};
   assert(Select(q,4,2000000000LL,true)==2);
   for(unsigned k=0;k<4;k++)assert(Select(q,k,2000000000LL,true)==0);
   assert(Select(q,4,999999999LL,true)==0);
   assert(Select(q,4,2000000000LL,false)==0);
   assert(Select({},4,2000000000LL,true)==0);
   assert(FirstFullBucket(0)==0);assert(FirstFullBucket(1)==1);
   assert(FirstFullBucket(5000000000ULL)==1);assert(FirstFullBucket(5000000001ULL)==2);
  }'''
  with tempfile.TemporaryDirectory()as td:
   p=Path(td);(p/'test.cc').write_text(code)
   subprocess.run(['g++','-std=c++20','-I',str(header),str(p/'test.cc'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
