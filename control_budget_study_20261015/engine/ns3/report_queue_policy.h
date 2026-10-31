#pragma once
#include <cstddef>
#include <cstdint>
#include <vector>
namespace epoch {
struct Entry { bool report; int64_t generatedNs; };
// Reports remain in arrival order. A report may bypass non-report packets only
// after four non-report requests; no packet is dropped or sent out of band.
inline size_t Select(const std::vector<Entry>& entries, unsigned nonReports,
                     int64_t now, bool enabled) {
    if (!enabled || entries.empty() || nonReports < 4) return 0;
    for (size_t i=0;i<entries.size();++i) {
        if (entries[i].report) {
            return now-entries[i].generatedNs >= 1000000000LL ? i : 0;
        }
    }
    return 0;
}
inline uint32_t FirstFullBucket(uint64_t installedNs) {
    constexpr uint64_t width=5000000000ULL;
    return uint32_t(installedNs/width + (installedNs%width != 0));
}
}
