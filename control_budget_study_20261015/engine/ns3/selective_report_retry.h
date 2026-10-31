#ifndef WSN_SELECTIVE_REPORT_RETRY_H
#define WSN_SELECTIVE_REPORT_RETRY_H
#include <cstdint>
#include <map>
#include <set>
#include <utility>
namespace selective {
// First two distinct report stamps actually observed at each local forwarding
// node for a version. Duplicate retries do not create additional protection.
class VersionProtection {
    struct Seen {bool initialized=false;uint16_t version=0;std::set<uint64_t> stamps;};
    std::map<std::pair<uint32_t,uint16_t>,Seen> seen;
public:
    bool Observe(uint32_t node,uint16_t source,uint16_t version,uint64_t stamp){
        if(source>=2)return false;
        auto& s=seen[{node,source}];
        if(!s.initialized||version>s.version){s.initialized=true;s.version=version;s.stamps.clear();}
        if(version!=s.version)return false;
        if(!s.stamps.count(stamp)&&s.stamps.size()<2)s.stamps.insert(stamp);
        return s.stamps.count(stamp);
    }
    bool Protected(uint32_t node,uint16_t source,uint16_t version,uint64_t stamp)const{
        auto it=seen.find({node,source});
        return it!=seen.end()&&it->second.version==version&&it->second.stamps.count(stamp);
    }
};
enum class Mode {Always,Queue,CriticalQueue};
inline bool Allow(Mode mode,bool critical,unsigned waiting){
    return mode==Mode::Always || waiting<=4 || (mode==Mode::CriticalQueue&&critical);
}
} // namespace selective
#endif
