// Single-hop IEEE 802.15.4 unslotted CSMA-CA docking scenario (SIMPAT study, E1).
// N stations on a 5 m circle send Poisson unicast DATA frames with ACK request to a
// coordinator at the origin.  Each station keeps one MAC request outstanding, as the
// closed-loop driver does, and queues the rest in an application FIFO of capacity 16.
// Output: one JSON object with request outcomes, CCA counts and MAC service times.
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/lr-wpan-module.h"
#include "ns3/mobility-module.h"
#include "ns3/propagation-module.h"
#include "ns3/spectrum-module.h"
#include <cmath>
#include <deque>
#include <fstream>
#include <map>
#include <vector>

using namespace ns3;
using namespace ns3::lrwpan;

struct St {
    Ptr<LrWpanNetDevice> dev;
    std::deque<int64_t> fifo;
    bool active = false;
    int64_t requestNs = 0;
    Ptr<ExponentialRandomVariable> gap;
};
static std::vector<St> st;
static uint32_t payload = 64, capacity = 16;
static double stopS = 120., warmS = 5.;
static uint64_t generated = 0, queueDrops = 0, requests = 0, ok = 0, caf = 0, noack = 0, other = 0;
static uint64_t cca = 0, busy = 0, received = 0;
static long double serviceSumNs = 0;
static std::vector<int64_t> service;

static Mac16Address Addr(uint16_t id) {
    uint8_t a[2] = {uint8_t((id + 1) >> 8), uint8_t(id + 1)};
    Mac16Address m;
    m.CopyFrom(a);
    return m;
}
static bool Counted() { return Simulator::Now().GetSeconds() >= warmS; }

static void Pump(uint32_t i) {
    auto& s = st[i];
    if (s.active || s.fifo.empty()) return;
    s.active = true;
    s.requestNs = Simulator::Now().GetNanoSeconds();
    s.fifo.pop_front();
    McpsDataRequestParams p;
    p.m_srcAddrMode = SHORT_ADDR;
    p.m_dstAddrMode = SHORT_ADDR;
    p.m_dstPanId = 7;
    p.m_dstAddr = Addr(st.size() - 1);
    p.m_msduHandle = 0;
    p.m_txOptions = TX_OPTION_ACK;
    if (Counted()) requests++;
    s.dev->GetMac()->McpsDataRequest(p, Create<Packet>(payload));
}
static void Arrive(uint32_t i) {
    if (Simulator::Now().GetSeconds() >= stopS) return;
    auto& s = st[i];
    if (Counted()) generated++;
    if (s.fifo.size() + (s.active ? 1 : 0) < capacity) s.fifo.push_back(Simulator::Now().GetNanoSeconds());
    else if (Counted()) queueDrops++;
    Pump(i);
    Simulator::Schedule(Seconds(s.gap->GetValue()), &Arrive, i);
}
static void Confirm(uint32_t i, McpsDataConfirmParams params) {
    auto& s = st[i];
    if (!s.active) return;
    s.active = false;
    if (s.requestNs >= int64_t(warmS * 1e9)) {
        switch (params.m_status) {
        case MacStatus::SUCCESS: ok++; break;
        case MacStatus::CHANNEL_ACCESS_FAILURE: caf++; break;
        case MacStatus::NO_ACK: noack++; break;
        default: other++;
        }
        int64_t d = Simulator::Now().GetNanoSeconds() - s.requestNs;
        serviceSumNs += d;
        service.push_back(d);
    }
    Simulator::ScheduleNow(&Pump, i);
}
static void Indication(McpsDataIndicationParams, Ptr<Packet>) {
    if (Counted()) received++;
}
static void Cca(uint32_t i, PhyEnumeration status) {
    if (Counted()) {
        cca++;
        busy += status == IEEE_802_15_4_PHY_BUSY;
    }
    st[i].dev->GetCsmaCa()->PlmeCcaConfirm(status);
}

int main(int argc, char** argv) {
    uint32_t n = 4, seed = 1, run = 1, retries = 2;
    double rate = 1.;  // packets per second per station
    double radius = 5.;
    std::string out = "docking.json";
    CommandLine cmd;
    cmd.AddValue("stations", "number of contending stations", n);
    cmd.AddValue("rate", "Poisson packets/s per station", rate);
    cmd.AddValue("payload", "MSDU bytes", payload);
    cmd.AddValue("retries", "macMaxFrameRetries", retries);
    cmd.AddValue("stop", "generation stop (s)", stopS);
    cmd.AddValue("warm", "warm-up excluded from counts (s)", warmS);
    cmd.AddValue("radius", "station distance from coordinator (m)", radius);
    cmd.AddValue("seed", "RNG seed", seed);
    cmd.AddValue("run", "RNG run", run);
    cmd.AddValue("output", "JSON output", out);
    cmd.Parse(argc, argv);
    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(run);
    auto channel = CreateObject<SingleModelSpectrumChannel>();
    auto loss = CreateObject<LogDistancePropagationLossModel>();
    loss->SetAttribute("Exponent", DoubleValue(3.));
    channel->AddPropagationLossModel(loss);
    channel->SetPropagationDelayModel(CreateObject<ConstantSpeedPropagationDelayModel>());
    st.resize(n + 1);
    for (uint32_t i = 0; i <= n; i++) {
        auto& s = st[i];
        auto node = CreateObject<Node>();
        s.dev = CreateObject<LrWpanNetDevice>();
        auto mob = CreateObject<ConstantPositionMobilityModel>();
        if (i == n) mob->SetPosition(Vector(0, 0, 0));
        else {
            double a = 2 * M_PI * i / n;
            mob->SetPosition(Vector(radius * std::cos(a), radius * std::sin(a), 0));
        }
        node->AggregateObject(mob);
        node->AddDevice(s.dev);
        s.dev->SetChannel(channel);
        s.dev->GetPhy()->SetMobility(mob);
        s.dev->SetAddress(Addr(i));
        s.dev->GetMac()->SetPanId(7);
        s.dev->GetMac()->SetMacMaxFrameRetries(retries);
        if (i < n) {
            s.dev->GetMac()->SetMcpsDataConfirmCallback(MakeBoundCallback(&Confirm, i));
            s.dev->GetPhy()->SetPlmeCcaConfirmCallback(MakeBoundCallback(&Cca, i));
            s.gap = CreateObject<ExponentialRandomVariable>();
            s.gap->SetAttribute("Mean", DoubleValue(1. / rate));
            Simulator::Schedule(Seconds(s.gap->GetValue()), &Arrive, i);
        } else {
            s.dev->GetMac()->SetMcpsDataIndicationCallback(MakeCallback(&Indication));
        }
    }
    Simulator::Stop(Seconds(stopS + 5));
    Simulator::Run();
    std::sort(service.begin(), service.end());
    auto q = [](double f) { return service.empty() ? 0. : double(service[size_t(f * (service.size() - 1))]) / 1e6; };
    std::ofstream o(out);
    o << "{\"simulator\":\"ns-3.44 lr-wpan\",\"stations\":" << n << ",\"rate\":" << rate << ",\"payload\":" << payload
      << ",\"retries\":" << retries << ",\"seed\":" << seed << ",\"run\":" << run << ",\"stop_s\":" << stopS
      << ",\"warm_s\":" << warmS << ",\"generated\":" << generated << ",\"queue_drops\":" << queueDrops
      << ",\"requests\":" << requests << ",\"success\":" << ok << ",\"channel_access_failure\":" << caf
      << ",\"no_ack\":" << noack << ",\"other\":" << other << ",\"cca\":" << cca << ",\"cca_busy\":" << busy
      << ",\"received\":" << received << ",\"service_mean_ms\":"
      << (service.empty() ? 0. : double(serviceSumNs / service.size()) / 1e6) << ",\"service_p50_ms\":" << q(.5)
      << ",\"service_p90_ms\":" << q(.9) << "}\n";
    Simulator::Destroy();
    return 0;
}
