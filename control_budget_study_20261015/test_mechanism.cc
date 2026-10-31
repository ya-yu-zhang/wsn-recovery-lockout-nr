#include "unified_control_budget.h"
#include <cassert>
#include <iostream>
#include <random>
using namespace controlbudget;
int main(){
    Bucket b;int ordinary=0;for(int i=0;i<20;i++)ordinary+=b.Take(0,381,false).admitted;
    assert(ordinary==8);for(int i=0;i<4;i++)assert(b.Take(0,381,true).admitted);
    assert(!b.Take(0,381,true).admitted);assert(b.Take(1250000000LL,381,true).admitted);
    std::mt19937 random(1729);Bucket stream;int64_t t=0,reserved=0;
    for(int i=0;i<10000;i++){
        t+=random()%1000000000;auto a=stream.Take(t,381,bool(random()%2));
        if(a.admitted){reserved+=381;if(!a.priority)assert(a.after>=1524*NS);}
        assert(reserved*NS<=4572*NS+305*t);assert(a.after>=0&&a.after<=4572*NS);
    }
    auto first=SourceReport(5*NS,0,0,false,0,0);assert(first.emit&&first.period==5);
    auto stable=SourceReport(20*NS,15*NS,0,false,0,0);assert(!stable.emit&&stable.period==15);
    assert(SourceReport(30*NS,15*NS,0,false,0,0).emit);
    auto failed=SourceReport(20*NS,15*NS,0,true,0,0);assert(failed.emit&&failed.period==5);
    assert(SourceReport(20*NS,15*NS,18*NS,false,0,0).period==5);
    assert(SourceReport(20*NS,15*NS,0,false,1,0).period==5);
    std::cout<<"PASS budget bound over 10000 mixed-priority requests, protected reserve, and version/failure pacing\n";
}
