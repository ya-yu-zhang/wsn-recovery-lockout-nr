#pragma once
#include <cstdint>
#include <deque>
#include <set>
#include <stdexcept>
#include <array>
#include <map>

namespace phase12 {
struct Completion {
    uint32_t node,flow;
    uint64_t sequence;
    uint32_t generationVersion;
    int64_t generatedNs,endNs;
    uint32_t status;
};
struct Snapshot {
    uint32_t source,version;
    int64_t stampNs;
    uint32_t currentN=0,currentFailed=0,mixedN=0,mixedFailed=0;
    std::array<uint8_t,8> Counters() const {
        if(currentFailed>currentN)throw std::invalid_argument("failed exceeds n");
        std::array<uint8_t,8> bytes{};
        for(unsigned i=0;i<4;i++){
            bytes[i]=uint8_t(currentN>>(24-8*i));
            bytes[4+i]=uint8_t(currentFailed>>(24-8*i));
        }
        return bytes;
    }
};
class SourceHistory {
    uint32_t source,version=0;
    int64_t window,clock=0;
    std::deque<Completion> history;
    std::set<uint64_t> seen;
    std::map<uint32_t,std::pair<int64_t,int64_t>> intervals{{0,{0,INT64_MAX}}};
    void Clock(int64_t now){
        if(now<0||now<clock)throw std::invalid_argument("nonmonotonic source clock");
        clock=now;
        while(!history.empty()&&history.front().endNs<now-window)history.pop_front();
    }
public:
    explicit SourceHistory(uint32_t node,int64_t width=20000000000LL):source(node),window(width){
        if(width<=0)throw std::invalid_argument("window");
    }
    bool InstallationReceived(uint32_t next,int64_t now){
        Clock(now);
        if(next<=version)return false;
        intervals.at(version).second=now;intervals[next]={now,INT64_MAX};
        version=next;return true;
    }
    bool Completed(const Completion& job){
        if(job.node!=source||job.flow!=source)return false;
        if(job.generatedNs<0||job.generatedNs>job.endNs||job.generationVersion>version)
            throw std::invalid_argument("invalid job provenance");
        auto interval=intervals.find(job.generationVersion);
        if(interval==intervals.end()||job.generatedNs<interval->second.first||job.generatedNs>interval->second.second)
            throw std::invalid_argument("invalid generation interval");
        if(seen.count(job.sequence))throw std::invalid_argument("duplicate terminal job");
        Clock(job.endNs);seen.insert(job.sequence);history.push_back(job);return true;
    }
    Snapshot Sample(int64_t now){
        Clock(now);Snapshot s{source,version,now};
        for(const auto& j:history){
            if(s.mixedN==UINT32_MAX)throw std::overflow_error("count");
            s.mixedN++;s.mixedFailed+=j.status!=0;
            if(j.generationVersion==version){s.currentN++;s.currentFailed+=j.status!=0;}
        }
        return s;
    }
};
}
