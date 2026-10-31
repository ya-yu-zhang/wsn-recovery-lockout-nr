#pragma once
#include <cstdint>
#include <map>
#include <utility>
namespace aligned {
constexpr int64_t WindowNs=20000000000LL;
constexpr uint32_t ReservationBytes=3*3*127;
struct Admission {uint64_t window;uint32_t before;bool admitted;};
class RetryBudget {
 std::map<std::pair<uint32_t,uint64_t>,uint32_t> used;
public:
 Admission Reserve(uint32_t node,int64_t now){
  auto window=uint64_t(now/WindowNs);auto& count=used[{node,window}];
  Admission a{window,count,count<1};if(a.admitted)++count;return a;
 }
};
}
