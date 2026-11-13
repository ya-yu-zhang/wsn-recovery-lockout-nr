// Phase-2 FlockLab trace-driven reception error model (registered 2026-11-11).
// Attached via LrWpanPhy::SetPostReceptionErrorModel at each receiver. For data/command frames,
// the sender is read from the MAC short source address (NodeAddress(i) = i+1) and the
// (sender -> this receiver) FlockLab link decides reception:
//   mode 2 (R2): cyclic replay of the measured 0/1 strobe stream, start offset = hash(seed,link);
//   mode 1 (R1): Bernoulli(link PRR) with a per-link SplitMix64 stream.
// ACK frames are never trace-dropped (declared limitation). Links absent from the trace file
// have PRR 0 (FlockLab nodes that never heard each other).
#pragma once
#include "ns3/error-model.h"
#include "ns3/lr-wpan-mac-header.h"
#include <map>
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <stdexcept>
namespace tracelink {
struct Link { std::vector<uint8_t> bits; double prr=0; uint64_t cursor=0, rng=0, evaluated=0, dropped=0, consumed_zero=0; };
inline uint64_t SplitMix(uint64_t& x){ uint64_t z=(x+=0x9e3779b97f4a7c15ULL); z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL; z=(z^(z>>27))*0x94d049bb133111ebULL; return z^(z>>31); }
struct Table {
    int mode=0; uint64_t seed=0; std::map<std::pair<uint16_t,uint16_t>,Link> links;
    void Load(const std::string& file,int m,uint64_t s){
        mode=m; seed=s; std::ifstream in(file); if(!in) throw std::runtime_error("cannot read trace file");
        std::string line; std::getline(in,line);
        while(std::getline(in,line)){ if(line.empty()) continue; std::replace(line.begin(),line.end(),',',' ');
            std::istringstream r(line); uint32_t a,b; double prr; std::string bits; r>>a>>b>>prr>>bits;
            Link L; L.prr=prr; for(char c:bits) L.bits.push_back(c=='1');
            uint64_t h=seed*1000003ULL+a*1009ULL+b; L.rng=h; L.cursor=L.bits.empty()?0:SplitMix(h)%L.bits.size();
            links[{uint16_t(a),uint16_t(b)}]=L; }
    }
    bool Corrupt(uint16_t src,uint16_t dst){
        auto it=links.find({src,dst});
        static Link none; Link& L= it==links.end()? none : it->second;
        L.evaluated++; bool ok;
        if(it==links.end()) ok=false;
        else if(mode==2 && !L.bits.empty()){ ok=L.bits[L.cursor%L.bits.size()]; L.cursor++; }
        else { double u=double(SplitMix(L.rng)>>11)/double(1ULL<<53); ok=u<L.prr; }
        if(!ok){ L.dropped++; L.consumed_zero++; }
        return !ok;
    }
    void Write(const std::string& file){ std::ofstream o(file); o<<"src,dst,prr,evaluated,dropped\n";
        for(auto& [k,L]:links) if(L.evaluated) o<<k.first<<","<<k.second<<","<<L.prr<<","<<L.evaluated<<","<<L.dropped<<"\n"; }
};
inline Table& Global(){ static Table t; return t; }
class TraceLinkErrorModel : public ns3::ErrorModel {
  public:
    uint16_t me=0;
    static ns3::TypeId GetTypeId(){ static ns3::TypeId tid=ns3::TypeId("tracelink::TraceLinkErrorModel").SetParent<ns3::ErrorModel>().AddConstructor<TraceLinkErrorModel>(); return tid; }
  private:
    bool DoCorrupt(ns3::Ptr<ns3::Packet> p) override {
        ns3::lrwpan::LrWpanMacHeader mac; auto c=p->Copy(); c->RemoveHeader(mac);
        if(mac.IsAcknowledgment()) return false;
        if(!(mac.IsData()||mac.IsCommand())) return false;
        uint8_t a[2]; mac.GetShortSrcAddr().CopyTo(a); uint16_t id=((uint16_t(a[0])<<8)|a[1]); if(id==0) return false;
        return Global().Corrupt(uint16_t(id-1),me);
    }
    void DoReset() override {}
};
}
