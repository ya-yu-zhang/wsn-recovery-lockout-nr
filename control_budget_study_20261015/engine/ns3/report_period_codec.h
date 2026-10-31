#pragma once
#include <cstdint>
#include <stdexcept>

namespace guarded {
inline uint16_t PackReportDepth(uint16_t depth, uint16_t period) {
    if (depth > 0x3fff) throw std::invalid_argument("report depth overflow");
    uint16_t tag = 0;
    switch (period) {
        case 5: break;
        case 10: tag = 0x8000; break;
        case 20: tag = 0x4000; break;
        case 15: tag = 0xc000; break;
        default: throw std::invalid_argument("unsupported reporting period");
    }
    return depth | tag;
}
inline uint16_t ReportPeriod(uint16_t packed) {
    switch (packed & 0xc000) {
        case 0x8000: return 10;
        case 0x4000: return 20;
        case 0xc000: return 15;
        default: return 5;
    }
}
inline uint16_t ReportDepth(uint16_t packed) { return packed & 0x3fff; }
}
