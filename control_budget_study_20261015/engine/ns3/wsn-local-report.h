#ifndef WSN_LOCAL_REPORT_H
#define WSN_LOCAL_REPORT_H
#include <cstdint>
namespace localreport {
struct Choice { uint16_t period; bool emit; bool urgent; };
inline unsigned State(unsigned depth, unsigned cca, unsigned busy, bool leased) {
    unsigned bin = depth == 0 ? 0 : depth <= 2 ? 1 : depth <= 8 ? 2 : 3;
    return bin + 4 * (cca != 0 && uint64_t(busy) * 100 > uint64_t(cca) * 35) + 8 * leased;
}
inline Choice Select(bool source, int64_t now, int64_t last, unsigned state, unsigned previous) {
    if (source) return {5, true, false};
    bool urgent = state >= 8 && state != previous;
    bool emit = last == 0 || now-last >= 15000000000LL || (urgent && now-last >= 10000000000LL);
    return {uint16_t(urgent ? 10 : 15), emit, urgent};
}
}
#endif
