// Standalone ns-3.44 LR-WPAN calibration driver; no optimizer or free deployment.
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/lr-wpan-module.h"
#include "ns3/mobility-module.h"
#include "ns3/propagation-module.h"
#include "ns3/spectrum-module.h"
#include <array>
#include <deque>
#include <fstream>
#include <map>
#include <set>
#include <vector>
#include <iomanip>
#include <tuple>
#include <cmath>
#include <cstdio>
#include "version_failure_history.h"
#include "report_period_codec.h"
#include "report_queue_policy.h"
#include "report_budget.h"
#include "wsn-local-report.h"
#include "selective_report_retry.h"
#include "unified_control_budget.h"

using namespace ns3;
using namespace ns3::lrwpan;
static bool unifiedBudget=false,protectEvidence=true,versionPacing=false;
static uint32_t controlRate=305,controlBurst=4572,controlReserve=1524,reportPhaseSeed=0;
static std::vector<controlbudget::Bucket> controlBuckets;
static bool reportRetry=false;
static std::string reportRetryMode="always";
static selective::VersionProtection reportProtection;
static bool reportBudget=false;
static aligned::RetryBudget retryBudget;
static std::map<std::tuple<uint16_t,uint64_t,uint32_t>,unsigned> reportRetryCounts;
static bool epochCertificate=false;
static std::string queueDiscipline="fifo";
static std::array<uint64_t,2> installedSinceNs{};
static bool extendedReport=true;
static bool sourceOnlyCounters=false;
static std::array<phase12::SourceHistory,2> sourceHistory{phase12::SourceHistory(0),phase12::SourceHistory(1)};

class RouteHeader : public Header {
public:
    uint16_t flow=0,version=0; uint32_t sequence=0; uint64_t generatedNs=0;
    uint8_t length=0,cursor=0; std::array<uint16_t,9> path{};
    static TypeId GetTypeId(){static TypeId t=TypeId("RouteHeader").SetParent<Header>().AddConstructor<RouteHeader>();return t;}
    TypeId GetInstanceTypeId()const override{return GetTypeId();}
    uint32_t GetSerializedSize()const override{return 36;}
    void Serialize(Buffer::Iterator i)const override{
        i.WriteHtonU16(flow);i.WriteHtonU16(version);i.WriteHtonU32(sequence);i.WriteHtonU64(generatedNs);
        i.WriteU8(length);i.WriteU8(cursor);for(auto n:path)i.WriteHtonU16(n);
    }
    uint32_t Deserialize(Buffer::Iterator i)override{
        flow=i.ReadNtohU16();version=i.ReadNtohU16();sequence=i.ReadNtohU32();generatedNs=i.ReadNtohU64();
        length=i.ReadU8();cursor=i.ReadU8();for(auto& n:path)n=i.ReadNtohU16();return 36;
    }
    void Print(std::ostream& os)const override{os<<flow<<":"<<sequence<<" hop "<<unsigned(cursor);}
};

class ReportHeader : public Header {
public:
    uint16_t node=0,depth=0,period=5;uint64_t stamp=0;bool critical=false;
    uint32_t n=0,meanJ=0,cca=0,busy=0,failed=0,version=0,ctrlBytes=0,currentN=0,currentFailed=0;
    std::array<uint32_t,4> bucket{},count{};
    static TypeId GetTypeId(){static TypeId t=TypeId("ClosedLoopReport").SetParent<Header>().AddConstructor<ReportHeader>();return t;}
    bool HasCounters()const{return extendedReport&&(!sourceOnlyCounters||node<2);}
    TypeId GetInstanceTypeId()const override{return GetTypeId();}uint32_t GetSerializedSize()const override{return HasCounters()?80:72;}
    void Serialize(Buffer::Iterator i)const override{
        i.WriteHtonU16(node);i.WriteHtonU16(guarded::PackReportDepth(depth|(critical?0x2000:0),period));i.WriteHtonU64(stamp);
        for(auto x:{n,meanJ,cca,busy,failed,version,ctrlBytes})i.WriteHtonU32(x);
        for(size_t k=0;k<4;k++){i.WriteHtonU32(bucket[k]);i.WriteHtonU32(count[k]);}
        if(HasCounters()){i.WriteHtonU32(currentN);i.WriteHtonU32(currentFailed);}
    }
    uint32_t Deserialize(Buffer::Iterator i)override{
        node=i.ReadNtohU16();uint16_t tagged=i.ReadNtohU16();depth=guarded::ReportDepth(tagged);critical=bool(depth&0x2000);depth&=0x1fff;period=guarded::ReportPeriod(tagged);stamp=i.ReadNtohU64();n=i.ReadNtohU32();meanJ=i.ReadNtohU32();cca=i.ReadNtohU32();busy=i.ReadNtohU32();failed=i.ReadNtohU32();version=i.ReadNtohU32();ctrlBytes=i.ReadNtohU32();
        for(size_t k=0;k<4;k++){bucket[k]=i.ReadNtohU32();count[k]=i.ReadNtohU32();}
        if(HasCounters()){currentN=i.ReadNtohU32();currentFailed=i.ReadNtohU32();}
        return GetSerializedSize();
    }
    void Print(std::ostream& os)const override{os<<node<<" at "<<stamp;}
};
class InstallHeader : public Header {
public:
    uint32_t decision=0;uint16_t version=0;std::array<uint8_t,2> length{};std::array<std::array<uint16_t,9>,2> paths{};
    static TypeId GetTypeId(){static TypeId t=TypeId("ClosedLoopInstall").SetParent<Header>().AddConstructor<InstallHeader>();return t;}
    TypeId GetInstanceTypeId()const override{return GetTypeId();}uint32_t GetSerializedSize()const override{return 64;}
    void Serialize(Buffer::Iterator i)const override{
        i.WriteHtonU32(decision);i.WriteHtonU16(version);i.WriteU8(length[0]);i.WriteU8(length[1]);for(auto p:paths)for(auto n:p)i.WriteHtonU16(n);for(int k=0;k<20;k++)i.WriteU8(0);
    }
    uint32_t Deserialize(Buffer::Iterator i)override{
        decision=i.ReadNtohU32();version=i.ReadNtohU16();length[0]=i.ReadU8();length[1]=i.ReadU8();for(auto& p:paths)for(auto& n:p)n=i.ReadNtohU16();for(int k=0;k<20;k++)i.ReadU8();return 64;
    }
    void Print(std::ostream& os)const override{os<<decision<<" version "<<version;}
};
static std::ofstream protocol,radio;
static std::map<uint32_t,std::pair<ReportHeader,int64_t>> receivedReports;
static std::map<uint16_t,std::vector<uint16_t>> installedPaths{{0,{0,2,3,9}},{1,{1,2,3,9}}};
static std::array<uint16_t,2> installedVersions{};
static std::vector<std::map<uint32_t,uint32_t>> generatedBuckets(10);
static std::map<uint32_t,std::array<uint32_t,2>> timelyBuckets;
static std::vector<uint64_t> ctrlNodeBytes(10);
static uint32_t controlSequence=0;static uint64_t controlDataBytes=0,applicationDataBytes=0,ackBytes=0;
static std::string reportProfile="full5";static bool brokenInstall=false,suppressReports=false,rejectFirstSource1=false,source1Rejected=false;static double generationStop=90.,simulationStop=110.;
static std::vector<int64_t> priorityUntil(10);
static bool PathPriority(){return reportProfile=="path_priority"||reportProfile=="path_priority16";}
static bool ReportLease(){return PathPriority()||reportProfile=="lease10_20"||reportProfile=="lease10_15"||reportProfile=="local15_event";}
static std::vector<int64_t> lastGuardedReportNs(10);
static std::vector<unsigned> lastLocalReportState(10);
static std::vector<int64_t> radioLast(10);static std::vector<PhyEnumeration> radioState(10,IEEE_802_15_4_PHY_TRX_OFF);
static std::vector<std::map<unsigned,int64_t>> radioDurations(10);
static void PathJson(std::ostream& out,const std::vector<uint16_t>& p){out<<"[";for(size_t k=0;k<p.size();k++){if(k)out<<",";out<<p[k];}out<<"]";}
static void ReportJson(std::ostream& out,const ReportHeader& r,int64_t received){
    out<<"{\"node\":"<<r.node<<",\"stamp_ns\":"<<r.stamp<<",\"received_ns\":"<<received<<",\"depth\":"<<r.depth<<",\"n\":"<<r.n<<",\"mean_J_ns\":"<<r.meanJ<<",\"cca\":"<<r.cca<<",\"busy\":"<<r.busy<<",\"failed\":"<<r.failed<<",\"version\":"<<r.version<<",\"ctrl_bytes\":"<<r.ctrlBytes<<",\"period_s\":"<<r.period<<",\"buckets\":[";
    for(size_t k=0;k<4;k++){if(k)out<<",";out<<"["<<r.bucket[k]<<","<<r.count[k]<<"]";}out<<"]";if(epochCertificate&&r.node<2)out<<",\"epoch_first_bucket\":"<<r.count[0];
    if(r.HasCounters())out<<",\"current_n\":"<<r.currentN<<",\"current_failed\":"<<r.currentFailed;
    out<<"}";
}
static void EnergyState(uint32_t node,PhyEnumeration old,PhyEnumeration next){
    int64_t now=Simulator::Now().GetNanoSeconds();NS_ABORT_MSG_IF(radioState[node]!=old,"radio state observer discontinuity");
    int64_t d=now-radioLast[node];radioDurations[node][unsigned(old)]+=d;
    radio<<node<<","<<radioLast[node]<<","<<now<<","<<unsigned(old)<<"\n";radioLast[node]=now;radioState[node]=next;
}
static void ControlArrived(uint32_t node,const RouteHeader& h,Ptr<Packet> packet);

struct Offered {uint16_t flow;uint32_t seq;double generated;std::vector<uint16_t> path;};
struct Station {Ptr<Node> node;Ptr<LrWpanNetDevice> device;Ptr<ConstantPositionMobilityModel> mobility;
    std::deque<Ptr<Packet>> queue;Ptr<Packet> active;bool alive=true;
    unsigned nonReportsSinceReport=4;
    uint32_t maxDepth=0;std::map<uint64_t,int64_t> enqueuedNs;std::set<uint64_t> received;};
static std::vector<Station> stations;
static std::ofstream trace,jobsTrace;
static bool monitor=true,compact=true;
struct Past{int64_t end,J;uint32_t cca,busy,failed;};
static std::vector<std::deque<Past>> histories;
using JobKey=std::tuple<uint32_t,uint16_t,uint32_t>;
struct Job{int64_t generated=0,request=0,queue=0,J=0,D=-1;uint32_t generationVersion=0,status=0,attempts=0,cca=0,busy=0,backoffs=0,sentCount=0,csmaEntries=0,activeNeighbors=0;std::array<int64_t,12> snapshot{};bool confirmed=false,sent=false;};
static std::map<JobKey,Job> jobs;
static uint64_t finalizedJobs=0,unattributedCca=0;
static JobKey Key(uint32_t n,const RouteHeader& h){return {n,h.flow,h.sequence};}
static void Finalize(const JobKey& key){
    auto it=jobs.find(key);if(it==jobs.end()||!it->second.confirmed||!it->second.sent)return;
    const auto& j=it->second;auto [node,flow,seq]=key;
    NS_ABORT_MSG_IF(j.request+j.J!=Simulator::Now().GetNanoSeconds(),"terminal callback time differs from job end");
    if(flow<2){
        protocol<<"{\"kind\":\"mac_job_completed\",\"time_ns\":"<<j.request+j.J<<",\"node\":"<<node<<",\"flow\":"<<flow<<",\"sequence\":"<<seq<<",\"generated_ns\":"<<j.generated<<",\"generation_version\":"<<j.generationVersion<<",\"status\":"<<j.status<<"}\n";
        if(node==flow)sourceHistory.at(node).Completed({node,flow,seq,j.generationVersion,j.generated,j.request+j.J,j.status});
    }
    jobsTrace<<node<<","<<flow<<","<<seq<<","<<j.generated<<","<<j.request<<","<<j.J<<","<<j.D<<","<<j.queue<<","<<j.status<<","<<j.attempts<<","<<j.cca<<","<<j.busy<<","<<j.backoffs<<","<<j.sentCount<<","<<j.csmaEntries<<","<<j.activeNeighbors;for(auto x:j.snapshot)jobsTrace<<","<<x;jobsTrace<<"\n";
    if(flow<2)histories[node].push_back(Past{j.request+j.J,j.J,j.cca,j.busy,uint32_t(j.status!=0)});
    finalizedJobs++;jobs.erase(it);
}
static uint32_t capacity=16, maxPsdu=0;
static std::map<uint16_t,uint32_t> offeredCount,deliveredCount,timelyCount;
static uint64_t phyTransmissions=0, dataTransmissions=0, ackTransmissions=0, queueDrops=0;
static std::map<unsigned,uint64_t> statusCount;
static std::set<uint64_t> sinkSeen;
static double deadline=0.2;
static uint64_t Identity(const RouteHeader& h){return (uint64_t(h.flow)<<32)|h.sequence;}
static void Emit(std::string event,uint32_t node,uint16_t flow,uint32_t seq,double value=0){
    if(compact && event!="offered" && event!="delivered" && event!="queue_drop" && event!="inactive_drop" && event!="header_error" && event!="unexpected_confirm" && event!="relay_removed")return;
    trace<<std::setprecision(17)<<Simulator::Now().GetSeconds()<<","<<event<<","<<node<<","<<flow<<","<<seq<<","<<value<<"\n";
}
static Mac16Address NodeAddress(uint16_t id){uint8_t a[2]={uint8_t((id+1)>>8),uint8_t(id+1)};Mac16Address m;m.CopyFrom(a);return m;}
static void Pump(uint32_t node);
static void Enqueue(uint32_t node,Ptr<Packet> packet){
    auto& s=stations.at(node);RouteHeader h;packet->PeekHeader(h);
    if(h.flow==65000){
        auto body=packet->Copy();RouteHeader route;body->RemoveHeader(route);ReportHeader r;body->PeekHeader(r);
        if(r.node<2){bool critical=reportProtection.Observe(node,r.node,r.version,r.stamp);
            protocol<<"{\"kind\":\"report_local_observation\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"node\":"<<node<<",\"source\":"<<r.node<<",\"version\":"<<r.version<<",\"stamp_ns\":"<<r.stamp<<",\"sequence\":"<<h.sequence<<",\"critical\":"<<(critical?"true":"false")<<"}\n";
        }
    }
    bool budgetAllowed=true;
    if(unifiedBudget&&h.flow>=65000&&s.alive&&s.queue.size()+bool(s.active)<capacity){
        bool priority=h.flow==65001;
        if(h.flow==65000){auto body=packet->Copy();RouteHeader route;body->RemoveHeader(route);ReportHeader report;body->PeekHeader(report);priority=report.critical;}
        priority=protectEvidence&&priority;
        auto a=controlBuckets.at(node).Take(Simulator::Now().GetNanoSeconds(),381,priority);budgetAllowed=a.admitted;
        protocol<<"{\"kind\":\"unified_control_admission\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"node\":"<<node<<",\"flow\":"<<h.flow<<",\"sequence\":"<<h.sequence<<",\"before_q\":"<<a.before<<",\"after_q\":"<<a.after<<",\"reservation_bytes\":381,\"priority\":"<<(priority?"true":"false")<<",\"admitted\":"<<(a.admitted?"true":"false")<<"}\n";
    }
    protocol<<"{\"kind\":\"queue_arrival\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"node\":"<<node<<",\"flow\":"<<h.flow<<",\"sequence\":"<<h.sequence<<",\"generated_ns\":"<<h.generatedNs<<",\"accepted\":"<<((s.alive&&s.queue.size()+bool(s.active)<capacity&&budgetAllowed)?"true":"false")<<"}\n";
    if(!s.alive){Emit("inactive_drop",node,h.flow,h.sequence);return;}
    if(s.queue.size()+bool(s.active)>=capacity){++queueDrops;Emit("queue_drop",node,h.flow,h.sequence);return;}
    if(!budgetAllowed){Emit("control_budget_drop",node,h.flow,h.sequence);return;}
    s.enqueuedNs[Identity(h)]=Simulator::Now().GetNanoSeconds();Emit("enqueued",node,h.flow,h.sequence);s.queue.push_back(packet);s.maxDepth=std::max(s.maxDepth,uint32_t(s.queue.size()+bool(s.active)));
    Pump(node);
}
static void RetryReport(uint32_t node,Ptr<Packet> packet){
    RouteHeader h;auto body=packet->Copy();body->RemoveHeader(h);ReportHeader r;body->PeekHeader(r);
    protocol<<"{\"kind\":\"report_packet\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"stamp_ns\":"<<r.stamp<<",\"sequence\":"<<h.sequence<<",\"source\":"<<r.node<<",\"body_bytes\":"<<r.GetSerializedSize()<<",\"retry\":true}\n";
    Enqueue(node,packet);
}
static void Confirm(uint32_t node,McpsDataConfirmParams params){
    auto& s=stations.at(node);
    if(!s.active){Emit("unexpected_confirm",node,0,0,unsigned(params.m_status));return;}
    RouteHeader h;s.active->PeekHeader(h);statusCount[unsigned(params.m_status)]++;
    Emit("mac_confirm",node,h.flow,h.sequence,unsigned(params.m_status));
    protocol<<"{\"kind\":\"queue_terminal\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"node\":"<<node<<",\"flow\":"<<h.flow<<",\"sequence\":"<<h.sequence<<"}\n";
    auto key=Key(node,h);auto& job=jobs.at(key);job.J=Simulator::Now().GetNanoSeconds()-job.request;job.status=unsigned(params.m_status);job.confirmed=true;Finalize(key);
    if(reportRetry&&h.flow==65000&&unsigned(params.m_status)!=0){
        auto body=s.active->Copy();RouteHeader route;body->RemoveHeader(route);ReportHeader r;body->PeekHeader(r);
        int64_t now=Simulator::Now().GetNanoSeconds();int64_t delay=20000000LL+int64_t((uint64_t(h.sequence)*2654435761ULL+node)%40)*1000000LL;
        auto key=std::make_tuple(r.node,r.stamp,node);
        if(r.node<2&&now+delay<=int64_t(r.stamp)+3000000000LL&&reportRetryCounts[key]<1){
            bool critical=reportProtection.Protected(node,r.node,r.version,r.stamp);
            selective::Mode mode=reportRetryMode=="always"?selective::Mode::Always:reportRetryMode=="queue"?selective::Mode::Queue:selective::Mode::CriticalQueue;
            bool admitted=selective::Allow(mode,critical,s.queue.size());
            protocol<<"{\"kind\":\"report_retry_classified\",\"time_ns\":"<<now<<",\"node\":"<<node<<",\"source\":"<<r.node<<",\"version\":"<<r.version<<",\"stamp_ns\":"<<r.stamp<<",\"parent_sequence\":"<<h.sequence<<",\"critical\":"<<(critical?"true":"false")<<",\"waiting_depth\":"<<s.queue.size()<<",\"mode\":\""<<reportRetryMode<<"\",\"admitted\":"<<(admitted?"true":"false")<<"}\n";
            if(!admitted){s.active=nullptr;Simulator::ScheduleNow(&Pump,node);return;}
            if(reportBudget){auto a=retryBudget.Reserve(node,now);protocol<<"{\"kind\":\"report_budget_admission\",\"time_ns\":"<<now<<",\"node\":"<<node<<",\"source\":"<<r.node<<",\"stamp_ns\":"<<r.stamp<<",\"parent_sequence\":"<<h.sequence<<",\"window\":"<<a.window<<",\"used_before\":"<<a.before<<",\"reservation_bytes\":1143,\"admitted\":"<<(a.admitted?"true":"false")<<"}\n";if(!a.admitted){s.active=nullptr;Simulator::ScheduleNow(&Pump,node);return;}}
            ++reportRetryCounts[key];RouteHeader next=h;next.sequence=++controlSequence;body->AddHeader(next);
            protocol<<"{\"kind\":\"report_retry_scheduled\",\"time_ns\":"<<now<<",\"dispatch_ns\":"<<now+delay<<",\"deadline_ns\":"<<r.stamp+3000000000ULL<<",\"node\":"<<node<<",\"source\":"<<r.node<<",\"stamp_ns\":"<<r.stamp<<",\"version\":"<<r.version<<",\"parent_sequence\":"<<h.sequence<<",\"sequence\":"<<next.sequence<<",\"status\":"<<unsigned(params.m_status)<<"}\n";
            Simulator::Schedule(NanoSeconds(delay),&RetryReport,node,body);
        }
    }
    s.active=nullptr;Simulator::ScheduleNow(&Pump,node);
}
static void Pump(uint32_t node){
    auto& s=stations.at(node);if(!s.alive||s.active||s.queue.empty())return;
    uint32_t ownDepth=s.queue.size();
    std::vector<epoch::Entry> entries;
    for(auto packet:s.queue){RouteHeader route;packet->PeekHeader(route);entries.push_back({route.flow==65000,int64_t(route.generatedNs)});}
    size_t chosen=epoch::Select(entries,s.nonReportsSinceReport,Simulator::Now().GetNanoSeconds(),queueDiscipline=="bounded_age");
    s.active=s.queue[chosen];s.queue.erase(s.queue.begin()+chosen);RouteHeader h;s.active->PeekHeader(h);
    if(h.flow==65000)s.nonReportsSinceReport=0;else ++s.nonReportsSinceReport;
    protocol<<"{\"kind\":\"queue_choice\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"node\":"<<node<<",\"selected_index\":"<<chosen<<",\"nonreports_after\":"<<s.nonReportsSinceReport<<",\"flow\":"<<h.flow<<",\"sequence\":"<<h.sequence<<",\"queued_before\":"<<entries.size()<<"}\n";
    NS_ABORT_MSG_IF(h.length<2||h.length>9||h.cursor+1>=h.length||h.path[h.cursor]!=node,"invalid forwarding header");
    McpsDataRequestParams params;params.m_srcAddrMode=SHORT_ADDR;params.m_dstAddrMode=SHORT_ADDR;
    params.m_dstPanId=7;params.m_dstAddr=NodeAddress(h.path[h.cursor+1]);params.m_msduHandle=0;params.m_txOptions=TX_OPTION_ACK;
    Job job;job.generated=h.generatedNs;job.generationVersion=h.version;job.request=Simulator::Now().GetNanoSeconds();job.queue=job.request-s.enqueuedNs.at(Identity(h));s.enqueuedNs.erase(Identity(h));
    double ccaRadius=std::pow(10.,(-s.device->GetPhy()->GetRxSensitivity()-10.-46.6777)/30.);
    for(uint32_t v=0;v<stations.size();v++)if(v!=node&&stations[v].active && CalculateDistance(s.mobility->GetPosition(),stations[v].mobility->GetPosition())<=ccaRadius)job.activeNeighbors++;
    auto& snap=job.snapshot;snap[0]=ownDepth;
    double rxRadius=std::pow(10.,(-s.device->GetPhy()->GetRxSensitivity()-46.6777)/30.);
    for(uint32_t v=0;v<stations.size();v++)if(v!=node){
        snap[1]+=stations[v].queue.size();snap[2]+=bool(stations[v].active);
        if(stations[v].active && CalculateDistance(s.mobility->GetPosition(),stations[v].mobility->GetPosition())<=rxRadius)snap[3]++;
    }
    auto& past=histories[node];while(!past.empty() && past.front().end<job.request-20000000000LL)past.pop_front();
    snap[4]=past.size();std::vector<int64_t> js;
    for(const auto& v:past){snap[5]+=v.J;snap[6]+=v.cca;snap[7]+=v.busy;snap[8]+=v.failed;js.push_back(v.J);}
    if(!js.empty()){
        std::sort(js.begin(),js.end());snap[9]=js[size_t(std::ceil(.9*js.size()))-1];snap[10]=past.back().end;snap[11]=past.front().end;
    }
    NS_ABORT_MSG_IF(jobs.count(Key(node,h)),"duplicate request job");jobs[Key(node,h)]=job;
    Emit("mac_request",node,h.flow,h.sequence,s.active->GetSize());
    s.device->GetMac()->McpsDataRequest(params,s.active->Copy());
}
static void Indication(uint32_t node,McpsDataIndicationParams,Ptr<Packet> packet){
    if(!stations.at(node).alive)return;
    RouteHeader h;packet->RemoveHeader(h);
    if(h.length<2||h.length>9||h.cursor+1>=h.length||h.path[h.cursor+1]!=node){Emit("header_error",node,h.flow,h.sequence);return;}
    const auto id=Identity(h);
    if(!stations[node].received.insert(id).second){Emit("duplicate",node,h.flow,h.sequence);return;}
    if(ReportLease() && h.flow<2 && node>=2 && node!=9)priorityUntil[node]=std::max(priorityUntil[node],Simulator::Now().GetNanoSeconds()+int64_t(12000000000));
    h.cursor++;
    if(h.cursor+1==h.length && h.flow>=65000){ControlArrived(node,h,packet);return;}
    if(h.cursor+1==h.length){
        if(!sinkSeen.insert(id).second)return;
        const auto delay=Simulator::Now().GetSeconds()-double(h.generatedNs)/1e9;
        protocol<<"{\"kind\":\"delivered\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"flow\":"<<h.flow<<",\"sequence\":"<<h.sequence<<",\"generated_ns\":"<<h.generatedNs<<",\"version\":"<<h.version<<"}\n";
        if(delay<=deadline)timelyBuckets[uint32_t(h.generatedNs/5000000000ULL)][h.flow]++;
        deliveredCount[h.flow]++;if(delay<=deadline)timelyCount[h.flow]++;
        Emit("delivered",node,h.flow,h.sequence,delay);return;
    }
    packet->AddHeader(h);Enqueue(node,packet);
}
static void Generate(Offered arrival){
    NS_ABORT_MSG_IF(arrival.flow>=2,"only two application parties");
    arrival.path=installedPaths.at(arrival.flow);generatedBuckets[arrival.flow][uint32_t(Simulator::Now().GetNanoSeconds()/5000000000LL)]++;
    offeredCount[arrival.flow]++;
    RouteHeader h;h.flow=arrival.flow;h.version=installedVersions[arrival.flow];h.sequence=arrival.seq;h.generatedNs=Simulator::Now().GetNanoSeconds();
    h.length=arrival.path.size();h.cursor=0;for(size_t i=0;i<arrival.path.size();++i)h.path[i]=arrival.path[i];
    auto p=Create<Packet>(64);p->AddHeader(h);Emit("offered",arrival.path.front(),h.flow,h.sequence,p->GetSize());
    protocol<<"{\"kind\":\"generated\",\"time_ns\":"<<h.generatedNs<<",\"flow\":"<<h.flow<<",\"sequence\":"<<h.sequence<<",\"version\":"<<h.version<<",\"path\":";PathJson(protocol,arrival.path);protocol<<"}\n";
    Enqueue(arrival.path.front(),p);
}
static void Tx(uint32_t node,Ptr<const Packet> p){
    phyTransmissions++;maxPsdu=std::max(maxPsdu,p->GetSize());
    NS_ABORT_MSG_IF(p->GetSize()>127,"oversized IEEE 802.15.4 PSDU");
    LrWpanMacHeader h;p->PeekHeader(h);
    if(h.IsAcknowledgment()){ackBytes+=p->GetSize();protocol<<"{\"kind\":\"phy_ack\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"node\":"<<node<<",\"bytes\":"<<p->GetSize()<<"}\n";
        ackTransmissions++;Emit("phy_ack_tx",node,0,0,p->GetSize());
    }else if(h.IsData()){
        dataTransmissions++;auto copy=p->Copy();copy->RemoveHeader(h);RouteHeader route;copy->PeekHeader(route);
        if(route.flow>=65000){controlDataBytes+=p->GetSize();ctrlNodeBytes[node]+=p->GetSize();}else applicationDataBytes+=p->GetSize();
        protocol<<"{\"kind\":\"phy_data\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"node\":"<<node<<",\"flow\":"<<route.flow<<",\"sequence\":"<<route.sequence<<",\"bytes\":"<<p->GetSize()<<"}\n";
        auto it=jobs.find(Key(node,route));if(it!=jobs.end())it->second.attempts++;Emit("phy_data_tx",node,route.flow,route.sequence,p->GetSize());
    }else Emit("phy_other_tx",node,0,0,p->GetSize());
}
static void MacRx(uint32_t node,Ptr<const Packet> p){
    auto copy=p->Copy();LrWpanMacHeader mac;copy->RemoveHeader(mac);
    if(!mac.IsData()||mac.GetShortDstAddr()!=NodeAddress(node))return;
    RouteHeader h;copy->PeekHeader(h);
    if(h.cursor+1<h.length && h.path[h.cursor+1]==node){
        auto it=jobs.find(Key(h.path[h.cursor],h));if(it!=jobs.end()&&it->second.D<0)it->second.D=Simulator::Now().GetNanoSeconds()-it->second.request;
        Emit("mac_data_received",node,h.flow,h.sequence,h.path[h.cursor]);
    }
}
static void SentPacket(uint32_t node,Ptr<const Packet> p,uint8_t count,uint8_t backoffs){
    auto copy=p->Copy();LrWpanMacHeader mac;copy->RemoveHeader(mac);if(!mac.IsData())return;
    RouteHeader h;copy->PeekHeader(h);auto key=Key(node,h);auto it=jobs.find(key);NS_ABORT_MSG_IF(it==jobs.end(),"sent trace without registered job");
    it->second.sentCount=count;it->second.backoffs=backoffs;it->second.sent=true;Finalize(key);
}
static void Cca(uint32_t node,PhyEnumeration status){
    auto& s=stations[node];
    if(s.active){RouteHeader h;s.active->PeekHeader(h);auto it=jobs.find(Key(node,h));if(it!=jobs.end()){it->second.cca++;it->second.busy+=status==IEEE_802_15_4_PHY_BUSY;}else unattributedCca++;}
    else unattributedCca++;
    s.device->GetCsmaCa()->PlmeCcaConfirm(status);
}
static void State(uint32_t node,MacState,MacState next){
    if(next!=MAC_CSMA||!stations[node].active)return;
    RouteHeader h;stations[node].active->PeekHeader(h);auto it=jobs.find(Key(node,h));if(it!=jobs.end())it->second.csmaEntries++;
}
static void InstallMonitors(){
    if(!monitor)return;
    for(uint32_t i=0;i<stations.size();i++){
        stations[i].device->GetPhy()->SetPlmeCcaConfirmCallback(MakeBoundCallback(&Cca,i));
        stations[i].device->GetMac()->TraceConnectWithoutContext("MacStateValue",MakeBoundCallback(&State,i));
    }
}
static void RxDrop(uint32_t node,Ptr<const Packet> p){Emit("phy_rx_drop",node,0,0,p->GetSize());}

static void OffWhenIdle(uint32_t node){
    if(stations[node].active){Simulator::Schedule(MilliSeconds(5),&OffWhenIdle,node);return;}
    stations[node].device->GetPhy()->PlmeSetTRXStateRequest(IEEE_802_15_4_PHY_FORCE_TRX_OFF);
}
static void FailRelay(uint32_t node){
    auto& s=stations.at(node);s.alive=false;s.mobility->SetPosition(Vector(1e9,1e9,0));
    while(!s.queue.empty()){RouteHeader h;s.queue.front()->PeekHeader(h);protocol<<"{\"kind\":\"queue_purge\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"node\":"<<node<<",\"flow\":"<<h.flow<<",\"sequence\":"<<h.sequence<<"}\n";s.enqueuedNs.erase(Identity(h));Emit("inactive_drop",node,h.flow,h.sequence);s.queue.pop_front();}
    OffWhenIdle(node);Emit("relay_removed",node,0,0);
    protocol<<"{\"kind\":\"fault_injected\",\"node\":"<<node<<",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<"}\n";
}
static std::vector<uint16_t> MonitorPath(uint32_t node){
    if(suppressReports && node<2)return {uint16_t(node),7,9};
    if(node==5)return {5,9};if(node==4)return {4,5,9};if(node==3)return {3,5,9};
    return {uint16_t(node),4,5,9};
}
static uint32_t SendControl(uint16_t flow,Ptr<Packet> payload,const std::vector<uint16_t>& path){
    RouteHeader h;h.flow=flow;h.sequence=++controlSequence;h.generatedNs=Simulator::Now().GetNanoSeconds();h.length=path.size();for(size_t i=0;i<path.size();i++)h.path[i]=path[i];
    payload->AddHeader(h);Enqueue(path.front(),payload);return h.sequence;
}
static void SendReport(uint32_t node,uint32_t slot){
    if(!stations[node].alive)return;
    int64_t now=Simulator::Now().GetNanoSeconds();
    uint16_t period=(node<2||reportProfile=="full5"||(PathPriority()&&priorityUntil[node]>now))?5:10;
    if(reportProfile=="lease10_20" && node>=2)period=priorityUntil[node]>now?10:20;
    if(reportProfile=="lease10_15" && node>=2)period=priorityUntil[node]>now?10:15;
    bool emitted=slot%(period/5)==0;
    if(reportProfile=="lease10_15"){
        emitted=lastGuardedReportNs[node]==0||now-lastGuardedReportNs[node]>=int64_t(period)*1000000000LL;
        if(emitted)lastGuardedReportNs[node]=now;
    }
    unsigned localDepth=stations[node].queue.size()+bool(stations[node].active),localCca=0,localBusy=0;
    for(const auto& p:histories[node])if(p.end>=now-20000000000LL){localCca+=p.cca;localBusy+=p.busy;}
    unsigned localState=localreport::State(localDepth,localCca,localBusy,priorityUntil[node]>now);
    if(reportProfile=="local15_event" && !(versionPacing&&node<2)){
        auto choice=localreport::Select(node<2,now,lastGuardedReportNs[node],localState,lastLocalReportState[node]);
        period=choice.period;emitted=choice.emit;
        protocol<<"{\"kind\":\"local_report_admission\",\"time_ns\":"<<now<<",\"node\":"<<node<<",\"depth\":"<<localDepth<<",\"cca\":"<<localCca<<",\"busy\":"<<localBusy<<",\"state\":"<<localState<<",\"previous_state\":"<<lastLocalReportState[node]<<",\"last_emitted_ns\":"<<lastGuardedReportNs[node]<<",\"urgent\":"<<(choice.urgent?"true":"false")<<",\"emitted\":"<<(emitted?"true":"false")<<",\"period_s\":"<<period<<"}\n";
        if(emitted){lastGuardedReportNs[node]=now;lastLocalReportState[node]=localState;}
    }
    if(versionPacing&&node<2){
        auto sample=sourceHistory.at(node).Sample(now);
        bool failure=sample.currentN>=10&&uint64_t(sample.currentFailed)*100>uint64_t(sample.currentN)*20;
        auto c=controlbudget::SourceReport(now,lastGuardedReportNs[node],installedSinceNs[node],failure,localState,lastLocalReportState[node]);
        period=c.period;emitted=c.emit;
        protocol<<"{\"kind\":\"version_report_admission\",\"time_ns\":"<<now<<",\"node\":"<<node<<",\"installed_ns\":"<<installedSinceNs[node]<<",\"last_emitted_ns\":"<<lastGuardedReportNs[node]<<",\"state\":"<<localState<<",\"previous_state\":"<<lastLocalReportState[node]<<",\"failure\":"<<(failure?"true":"false")<<",\"emitted\":"<<(emitted?"true":"false")<<",\"period_s\":"<<period<<"}\n";
        if(emitted){lastGuardedReportNs[node]=now;lastLocalReportState[node]=localState;}
    }
    protocol<<"{\"kind\":\"report_tick\",\"time_ns\":"<<now<<",\"node\":"<<node<<",\"slot\":"<<slot<<",\"period_s\":"<<period<<",\"priority_until_ns\":"<<priorityUntil[node]<<",\"emitted\":"<<(emitted?"true":"false")<<"}\n";
    if(emitted){
    ReportHeader r;r.critical=unifiedBudget&&(node<2||priorityUntil[node]>now);r.period=period;r.node=node;r.stamp=Simulator::Now().GetNanoSeconds();r.depth=stations[node].queue.size()+bool(stations[node].active);r.version=node<2?installedVersions[node]:0;r.ctrlBytes=ctrlNodeBytes[node];
    auto& past=histories[node];while(!past.empty()&&past.front().end<int64_t(r.stamp)-20000000000LL)past.pop_front();
    uint64_t sum=0;r.n=past.size();for(auto p:past){sum+=p.J;r.cca+=p.cca;r.busy+=p.busy;r.failed+=p.failed;}r.meanJ=r.n?sum/r.n:0;
    if(node<2){auto current=sourceHistory.at(node).Sample(r.stamp);
        NS_ABORT_MSG_IF(current.version!=r.version||current.mixedN!=r.n||current.mixedFailed!=r.failed,"source collector differs from actual source history");
        r.currentN=current.currentN;r.currentFailed=current.currentFailed;}
    uint32_t bucket=r.stamp/5000000000ULL;for(uint32_t k=0;k<4;k++){r.bucket[k]=bucket>=k?bucket-k:0xffffffff;r.count[k]=generatedBuckets[node][r.bucket[k]];}
    if(epochCertificate&&node<2){r.bucket[0]=0xffffffff;r.count[0]=epoch::FirstFullBucket(installedSinceNs[node]);}
    protocol<<"{\"kind\":\"report_generated\",\"time_ns\":"<<r.stamp<<",\"report\":";ReportJson(protocol,r,0);protocol<<"}\n";
    protocol<<"{\"kind\":\"report_packet\",\"time_ns\":"<<r.stamp<<",\"sequence\":"<<controlSequence+1<<",\"source\":"<<node<<",\"body_bytes\":"<<r.GetSerializedSize()<<"}\n";
    auto p=Create<Packet>();p->AddHeader(r);SendControl(65000,p,MonitorPath(node));
    }
    if(Simulator::Now().GetSeconds()+5.<generationStop+15)Simulator::Schedule(Seconds(5),&SendReport,node,slot+1);
}
static void ControlArrived(uint32_t node,const RouteHeader& h,Ptr<Packet> packet){
    int64_t now=Simulator::Now().GetNanoSeconds();
    if(h.flow==65000){
        NS_ABORT_MSG_IF(node!=9,"report terminal is not controller");ReportHeader r;packet->RemoveHeader(r);NS_ABORT_MSG_IF(r.stamp>uint64_t(now),"future report");
        if(!receivedReports.count(r.node)||receivedReports[r.node].first.stamp<r.stamp)receivedReports[r.node]={r,now};
        protocol<<"{\"kind\":\"report_received\",\"time_ns\":"<<now<<",\"sequence\":"<<h.sequence<<",\"report\":";ReportJson(protocol,r,now);protocol<<"}\n";
    }else if(h.flow==65001){
        InstallHeader cmd;packet->RemoveHeader(cmd);NS_ABORT_MSG_IF(node>=2||cmd.length[node]<2||cmd.length[node]>9,"invalid install recipient");
        std::vector<uint16_t> path(cmd.paths[node].begin(),cmd.paths[node].begin()+cmd.length[node]);
        NS_ABORT_MSG_IF(path.front()!=node||path.back()!=9,"invalid installed path endpoints");
        if(rejectFirstSource1&&node==1&&!source1Rejected){source1Rejected=true;
            protocol<<"{\"kind\":\"install_rejected\",\"time_ns\":"<<now<<",\"source\":"<<node<<",\"decision\":"<<cmd.decision<<",\"sequence\":"<<h.sequence<<"}\n";return;}
        protocol<<"{\"kind\":\"install_received\",\"time_ns\":"<<now<<",\"source\":"<<node<<",\"decision\":"<<cmd.decision<<",\"sequence\":"<<h.sequence<<",\"previous_version\":"<<installedVersions[node]<<"}\n";
        if(cmd.version>installedVersions[node]){installedVersions[node]=cmd.version;installedSinceNs[node]=uint64_t(now);installedPaths[node]=path;
            NS_ABORT_MSG_IF(!sourceHistory.at(node).InstallationReceived(cmd.version,now),"new install did not advance collector");
            protocol<<"{\"kind\":\"install_applied\",\"time_ns\":"<<now<<",\"source\":"<<node<<",\"decision\":"<<cmd.decision<<",\"version\":"<<cmd.version<<",\"path\":";PathJson(protocol,path);protocol<<"}\n";}
    }
}
static void HoldSearchCompleted(uint32_t decision,uint32_t action,uint32_t fe){
    protocol<<"{\"kind\":\"action_hold\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"decision\":"<<decision<<",\"action\":"<<action<<",\"fe\":"<<fe<<"}\n";
}
static void SendInstall(uint32_t decision,uint32_t action,uint32_t fe,std::array<std::vector<uint16_t>,2> paths,uint32_t targets,bool retry){
    protocol<<"{\"kind\":\"install_attempt\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"decision\":"<<decision<<",\"action\":"<<action<<",\"fe\":"<<fe<<",\"targets\":"<<targets<<",\"retry\":"<<(retry?"true":"false")<<"}\n";
    if(!retry)protocol<<"{\"kind\":\"install_started\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"decision\":"<<decision<<",\"action\":"<<action<<",\"fe\":"<<fe<<"}\n";
    InstallHeader cmd;cmd.decision=decision;cmd.version=decision;for(size_t f=0;f<2;f++){cmd.length[f]=paths[f].size();std::copy(paths[f].begin(),paths[f].end(),cmd.paths[f].begin());}
    for(uint32_t f=0;f<2;f++)if(targets&(1u<<f)){auto p=Create<Packet>();p->AddHeader(cmd);
        auto sequence=SendControl(65001,p,brokenInstall?std::vector<uint16_t>{9,7,uint16_t(f)}:std::vector<uint16_t>{9,5,4,uint16_t(f)});
        protocol<<"{\"kind\":\"install_packet\",\"time_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"decision\":"<<decision<<",\"source\":"<<f<<",\"sequence\":"<<sequence<<",\"retry\":"<<(retry?"true":"false")<<"}\n";}
}
static void DecisionTick(){
    int64_t now=Simulator::Now().GetNanoSeconds();
    std::cout<<"STEP {\"time_ns\":"<<now<<",\"reports\":[";bool comma=false;
    for(auto [node,r]:receivedReports){if(comma)std::cout<<",";comma=true;ReportJson(std::cout,r.first,r.second);}
    std::cout<<"],\"sink_control_bytes\":"<<ctrlNodeBytes[9]<<",\"timely_buckets\":{";comma=false;for(auto [b,counts]:timelyBuckets){if(comma)std::cout<<",";comma=true;std::cout<<"\""<<b<<"\":["<<counts[0]<<","<<counts[1]<<"]";}std::cout<<"}}"<<std::endl;
    std::string line;NS_ABORT_MSG_IF(!std::getline(std::cin,line),"controller disconnected");std::istringstream in(line);int action;uint32_t decision,fe;in>>action>>decision>>fe;
    NS_ABORT_MSG_IF(!in||action>3||action<-3||fe>64,"invalid controller reply");
    if(action==-3){uint32_t label;in>>label;NS_ABORT_MSG_IF(!in||label>3||fe==0,"invalid hold reply");Simulator::Schedule(MicroSeconds(20*fe),&HoldSearchCompleted,decision,label,fe);}
    if(action>=0||action==-2){uint32_t targets=3,label=action>=0?uint32_t(action):0;if(action==-2){in>>targets>>label;NS_ABORT_MSG_IF(fe!=0||targets<1||targets>3||label>3,"invalid retry");}std::array<std::vector<uint16_t>,2> paths;for(uint32_t f=0;f<2;f++){uint32_t length;in>>length;NS_ABORT_MSG_IF(length>9,"path too long");for(uint32_t k=0;k<length;k++){uint16_t n;in>>n;paths[f].push_back(n);}
        if(length){std::set<uint16_t> simple(paths[f].begin(),paths[f].end());NS_ABORT_MSG_IF(simple.size()!=length||paths[f].front()!=f||paths[f].back()!=9||*simple.rbegin()>=stations.size(),"invalid chosen route");}}
        NS_ABORT_MSG_IF(!in||decision==0||decision>=65536,"invalid decision");
        if(!paths[0].empty()&&!paths[1].empty())Simulator::Schedule(MicroSeconds(20*fe),&SendInstall,decision,label,fe,paths,targets,action==-2);
        else protocol<<"{\"kind\":\"action_no_solution\",\"time_ns\":"<<now<<",\"decision\":"<<decision<<",\"action\":"<<action<<",\"fe\":"<<fe<<"}\n";
    }
    if(Simulator::Now().GetSeconds()+5.<generationStop+15)Simulator::Schedule(Seconds(5),&DecisionTick);
}
int main(int argc,char** argv){
    uint32_t nodes=30,seed=17,run=1;double stop=30.,failAt=-1,spacing=10.;uint32_t chainHops=0;
    std::string arrivalFile,positionFile,output="netcheck",faultSchedule;
    CommandLine cmd;cmd.AddValue("unifiedBudget","bound all control DATA MAC requests",unifiedBudget);
    cmd.AddValue("protectEvidence","reserve credit for source/active-path evidence and installation",protectEvidence);
    cmd.AddValue("versionPacing","version-conditioned source reporting",versionPacing);
    cmd.AddValue("controlRate","control DATA reservation bytes per second",controlRate);
    cmd.AddValue("controlBurst","initial control credit bytes",controlBurst);
    cmd.AddValue("controlReserve","protected control credit bytes",controlReserve);
    cmd.AddValue("reportPhaseSeed","outcome-independent reporting phase seed",reportPhaseSeed);
    cmd.AddValue("nodes","node count including sink",nodes);cmd.AddValue("seed","PHY RNG seed",seed);
    cmd.AddValue("run","PHY RNG run",run);cmd.AddValue("arrivals","CSV time,flow,sequence,path with semicolon node IDs",arrivalFile);
    cmd.AddValue("rejectFirstSource1","functional injection: reject first received source1 install",rejectFirstSource1);cmd.AddValue("brokenInstall","functional fault: unreachable install route",brokenInstall);cmd.AddValue("suppressReports","functional fault: unreachable source report route",suppressReports);cmd.AddValue("generationStop","generation duration",generationStop);
    cmd.AddValue("positions","optional CSV node,x,y",positionFile);cmd.AddValue("output","output prefix",output);cmd.AddValue("stop","tail stop seconds",stop);
    cmd.AddValue("failAt","remove relay 2 at seconds, negative disables",failAt);
    cmd.AddValue("spacing","per-hop spacing in chain geometry",spacing);cmd.AddValue("chainHops","0 legacy, otherwise 1/2/4-hop chain",chainHops);
    cmd.AddValue("monitor","pass-through CCA and MAC-state observer",monitor);cmd.AddValue("compact","retain offered/delivered/error event trace only",compact);
    cmd.AddValue("reportProfile","full5 or hybrid5_10 actual report periods",reportProfile);
    cmd.AddValue("extendedReport","append two current-version counters (eight bytes)",extendedReport);
    cmd.AddValue("sourceOnlyCounters","omit unused extended counters from relay reports",sourceOnlyCounters);
    cmd.AddValue("faultSchedule","semicolon-separated time:relay permanent removals",faultSchedule);
    cmd.AddValue("reportBudget","one retry allocation per local node per fixed twenty-second window",reportBudget);
    cmd.AddValue("reportRetry","at most one source-report application retry per hop within three seconds",reportRetry);
    cmd.AddValue("reportRetryMode","always, queue, or critical_queue; local evidence only",reportRetryMode);
    cmd.AddValue("epochCertificate","reuse unclosed source bucket slot for version epoch certificate",epochCertificate);
    cmd.AddValue("queueDiscipline","fifo or bounded_age report scheduling",queueDiscipline);
    cmd.AddValue("capacity","FIFO capacity including active request",capacity);cmd.AddValue("deadline","deadline seconds",deadline);cmd.Parse(argc,argv);
    NS_ABORT_MSG_IF(reportProfile!="full5" && reportProfile!="hybrid5_10" && reportProfile!="path_priority" && reportProfile!="path_priority16" && reportProfile!="lease10_20" && reportProfile!="lease10_15" && reportProfile!="local15_event","unsupported report profile");
    NS_ABORT_MSG_IF(queueDiscipline!="fifo"&&queueDiscipline!="bounded_age","unsupported queue discipline");
    NS_ABORT_MSG_IF(reportRetryMode!="always"&&reportRetryMode!="queue"&&reportRetryMode!="critical_queue","unsupported report retry mode");
    NS_ABORT_MSG_IF(epochCertificate&&(!extendedReport||!sourceOnlyCounters),"epoch certificate requires source-only extended reports");
    NS_ABORT_MSG_IF(nodes<4||nodes>65534||arrivalFile.empty()||capacity<1,"invalid network check config");
    NS_ABORT_MSG_IF(nodes<10||nodes>64,"study supports ten through sixty-four nodes");
    generatedBuckets.resize(nodes);ctrlNodeBytes.resize(nodes);priorityUntil.resize(nodes);
    lastGuardedReportNs.resize(nodes);lastLocalReportState.resize(nodes);radioLast.resize(nodes);
    radioState.resize(nodes,IEEE_802_15_4_PHY_TRX_OFF);radioDurations.resize(nodes);
    controlBuckets.assign(nodes,controlbudget::Bucket(controlRate,controlBurst,protectEvidence?controlReserve:0));simulationStop=stop;
    protocol.open(output+".protocol.jsonl.partial");radio.open(output+".radio.csv.partial");radio<<"node,start_ns,end_ns,state\n";
    RngSeedManager::SetSeed(seed);RngSeedManager::SetRun(run);
    trace.open(output+".csv.partial");NS_ABORT_MSG_IF(!trace,"cannot write trace");trace<<"time,event,node,flow,sequence,value\n";
    jobsTrace.open(output+".jobs.csv.partial");NS_ABORT_MSG_IF(!jobsTrace,"cannot open jobs output");jobsTrace<<"node,flow,sequence,generated_ns,request_ns,J_ns,D_ns,queue_ns,status,attempts,cca,busy,backoffs,sent_count,csma_entries,active_neighbors,pre_depth,other_queued,other_active,rx_active,past_n,past_sum_J_ns,past_cca,past_busy,past_failed,past_J90_ns,past_last_end_ns,past_first_end_ns\n";
    auto channel=CreateObject<SingleModelSpectrumChannel>();
    auto loss=CreateObject<LogDistancePropagationLossModel>();loss->SetAttribute("Exponent",DoubleValue(3.));
    channel->AddPropagationLossModel(loss);channel->SetPropagationDelayModel(CreateObject<ConstantSpeedPropagationDelayModel>());
    stations.resize(nodes);histories.resize(nodes);
    std::map<uint32_t,Vector> positionOverrides;
    if(!positionFile.empty()){std::ifstream pf(positionFile);NS_ABORT_MSG_IF(!pf,"cannot read positions");std::string ln;std::getline(pf,ln);while(std::getline(pf,ln)){std::replace(ln.begin(),ln.end(),',',' ');std::istringstream ps(ln);uint32_t n;double x,y;ps>>n>>x>>y;NS_ABORT_MSG_IF(!ps||n>=nodes||!std::isfinite(x)||!std::isfinite(y),"invalid position");positionOverrides[n]=Vector(x,y,0);}}
    for(uint32_t i=0;i<nodes;++i){
        auto& s=stations[i];s.node=CreateObject<Node>();s.device=CreateObject<LrWpanNetDevice>();s.mobility=CreateObject<ConstantPositionMobilityModel>();
        Vector pos(1000.+i*10,1000.,0);if(i==0)pos=Vector(0,0,0);if(i==1)pos=Vector(0,2,0);if(i==2)pos=Vector(5,1,0);if(i==nodes-1)pos=Vector(10,1,0);
        if(chainHops){
            NS_ABORT_MSG_IF(chainHops>8||nodes<chainHops+2,"invalid chain layout");
            pos=Vector(10000+i*10,10000,0);
            if(i==0)pos=Vector(0,0,0);
            if(i==1)pos=Vector(0,2,0);
            if(i>=2&&i<=chainHops)pos=Vector((i-1)*spacing,0,0);
            if(i==nodes-1)pos=Vector(chainHops*spacing,0,0);
        }
        if(positionOverrides.count(i))pos=positionOverrides.at(i);
        if((brokenInstall||suppressReports)&&i==7)pos=Vector(10000,10000,0);
        s.mobility->SetPosition(pos);s.node->AggregateObject(s.mobility);s.node->AddDevice(s.device);
        s.device->SetChannel(channel);s.device->GetPhy()->SetMobility(s.mobility);s.device->SetAddress(NodeAddress(i));
        s.device->GetMac()->SetPanId(7);s.device->GetMac()->SetMacMaxFrameRetries(2);
        s.device->GetMac()->TraceConnectWithoutContext("MacSentPkt",MakeBoundCallback(&SentPacket,i));
        s.device->GetMac()->SetMcpsDataConfirmCallback(MakeBoundCallback(&Confirm,i));
        s.device->GetMac()->SetMcpsDataIndicationCallback(MakeBoundCallback(&Indication,i));
        s.device->GetPhy()->TraceConnectWithoutContext("TrxStateValue",MakeBoundCallback(&EnergyState,i));
        s.device->GetPhy()->TraceConnectWithoutContext("PhyTxBegin",MakeBoundCallback(&Tx,i));
        s.device->GetMac()->TraceConnectWithoutContext("MacRx",MakeBoundCallback(&MacRx,i));
        s.device->GetPhy()->TraceConnectWithoutContext("PhyRxDrop",MakeBoundCallback(&RxDrop,i));
    }
    Simulator::ScheduleNow(&InstallMonitors);
    if(ReportLease()){priorityUntil[2]=12000000000LL;priorityUntil[3]=12000000000LL;}
    for(uint32_t i=0;i<nodes;i++)if(i!=9){
        double phase=5.1+i*.02;
        if(reportPhaseSeed){uint64_t z=uint64_t(reportPhaseSeed)*2654435761ULL+uint64_t(i)*11400714819323198485ULL;z^=z>>29;phase=5.05+double(z%950)/1000.;}
        Simulator::Schedule(Seconds(phase),&SendReport,i,0u);
    }
    Simulator::Schedule(Seconds(10),&DecisionTick);
    std::ifstream in(arrivalFile);NS_ABORT_MSG_IF(!in,"cannot read arrivals");std::string line;std::getline(in,line);
    std::set<uint64_t> identifiers;
    while(std::getline(in,line)){
        if(line.empty())continue;std::replace(line.begin(),line.end(),',',' ');std::istringstream row(line);
        Offered a;std::string path;row>>a.generated>>a.flow>>a.seq>>path;std::replace(path.begin(),path.end(),';',' ');std::istringstream p(path);uint16_t n;
        while(p>>n)a.path.push_back(n);
        NS_ABORT_MSG_IF(a.generated<0||a.generated>=stop||a.path.size()<2||a.path.size()>9||a.path.back()!=9,"invalid arrival or route");
        std::set<uint16_t> simple(a.path.begin(),a.path.end());
        NS_ABORT_MSG_IF(simple.size()!=a.path.size()||*simple.rbegin()>=nodes||!identifiers.insert((uint64_t(a.flow)<<32)|a.seq).second,"non-simple path or duplicate packet");
        Simulator::Schedule(Seconds(a.generated),&Generate,a);
    }
    NS_ABORT_MSG_IF(failAt>=0&&!faultSchedule.empty(),"two fault schedule formats supplied");
    if(failAt>=0)Simulator::Schedule(Seconds(failAt),&FailRelay,2);
    if(!faultSchedule.empty()){
        std::istringstream schedules(faultSchedule);std::string event;std::set<uint32_t> removed;
        while(std::getline(schedules,event,';')){
            std::replace(event.begin(),event.end(),':',' ');std::istringstream item(event);double when;uint32_t relay;std::string extra;
            item>>when>>relay;NS_ABORT_MSG_IF(!item||item>>extra||!std::isfinite(when)||when<0||when>=generationStop||relay<2||relay==9||relay>=nodes||!removed.insert(relay).second,"invalid permanent fault schedule");
            Simulator::Schedule(Seconds(when),&FailRelay,relay);
        }
    }
    Simulator::Stop(Seconds(stop));Simulator::Run();
    NS_ABORT_MSG_IF(!jobs.empty(),"unfinished or unfinalized MAC jobs at stop");
    for(uint32_t i=0;i<nodes;i++){int64_t end=Simulator::Now().GetNanoSeconds();radioDurations[i][unsigned(radioState[i])]+=end-radioLast[i];radio<<i<<","<<radioLast[i]<<","<<end<<","<<unsigned(radioState[i])<<"\n";}
    protocol.close();radio.close();std::rename((output+".protocol.jsonl.partial").c_str(),(output+".protocol.jsonl").c_str());std::rename((output+".radio.csv.partial").c_str(),(output+".radio.csv").c_str());
    std::ofstream summary(output+".json.partial");summary<<"{\"ns3_version\":\"3.44\",\"closed_loop_prototype\":true,\"nodes_including_sink\":"<<nodes<<",\"max_psdu_bytes\":"<<maxPsdu
       <<",\"total_attempts\":3,\"mac_max_retries\":2,\"phy_transmissions\":"<<phyTransmissions<<",\"data_transmissions\":"<<dataTransmissions<<",\"ack_transmissions\":"<<ackTransmissions
       <<",\"finalized_jobs\":"<<finalizedJobs<<",\"unattributed_cca\":"<<unattributedCca<<",\"rx_sensitivity_dbm\":"<<stations[0].device->GetPhy()->GetRxSensitivity()<<",\"queue_drops\":"<<queueDrops<<",\"offered\":["<<offeredCount[0]<<","<<offeredCount[1]<<"],\"delivered\":["<<deliveredCount[0]<<","<<deliveredCount[1]<<"],\"timely\":["<<timelyCount[0]<<","<<timelyCount[1]<<"],\"mac_status_counts\":{";
    bool first=true;for(auto [status,count]:statusCount){if(!first)summary<<",";first=false;summary<<"\""<<status<<"\":"<<count;}summary<<"},\"control_psdu_bytes\":"<<controlDataBytes<<",\"application_psdu_bytes\":"<<applicationDataBytes<<",\"ack_psdu_bytes\":"<<ackBytes<<",\"stop_ns\":"<<Simulator::Now().GetNanoSeconds()<<",\"max_queue_depth\":[";
    for(uint32_t i=0;i<nodes;++i){if(i)summary<<",";summary<<stations[i].maxDepth;}summary<<"]}\n";
    summary.close();std::rename((output+".json.partial").c_str(),(output+".json").c_str());jobsTrace.close();std::rename((output+".jobs.csv.partial").c_str(),(output+".jobs.csv").c_str());
    trace.close();std::rename((output+".csv.partial").c_str(),(output+".csv").c_str());Simulator::Destroy();return 0;
}
