#pragma once
#include <cstdint>
#include <stdexcept>
namespace controlbudget {
constexpr int64_t NS=1000000000LL;
struct Admission {int64_t before,after;uint32_t bytes;bool priority,admitted;};
class Bucket {
    uint32_t rate,burst,reserve;
    int64_t credit,last=0;
public:
    Bucket(uint32_t r=305,uint32_t b=4572,uint32_t p=1524):rate(r),burst(b),reserve(p),credit(int64_t(b)*NS){
        if(!rate||burst<381||reserve>burst-381)throw std::invalid_argument("invalid control budget");
    }
    Admission Take(int64_t now,uint32_t bytes,bool priority){
        if(now<last||bytes>381)throw std::invalid_argument("nonmonotone time or invalid reservation");
        int64_t cap=int64_t(burst)*NS,delta=now-last;
        credit=delta>(cap-credit)/rate?cap:credit+delta*rate;last=now;
        int64_t required=int64_t(bytes+(priority?0:reserve))*NS;
        Admission a{credit,credit,bytes,priority,credit>=required};
        if(a.admitted){credit-=int64_t(bytes)*NS;a.after=credit;}
        return a;
    }
};
struct SourceChoice {uint16_t period;bool emit,urgent;};
inline SourceChoice SourceReport(int64_t now,int64_t last,int64_t installed,
                                 bool failure,unsigned state,unsigned previous){
    bool urgent=now-installed<15*NS||failure||state!=previous;
    uint16_t period=urgent?5:15;
    return {period,last==0||now-last>=int64_t(period)*NS,urgent};
}
}
