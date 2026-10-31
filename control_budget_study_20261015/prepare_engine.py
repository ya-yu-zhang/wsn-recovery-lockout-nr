"""Apply the isolated, outcome-independent mechanism and scale extension."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def change(path,old,new):
    p=ROOT/'engine'/path;s=p.read_text()
    if s.count(old)!=1:raise ValueError((path,old[:70],s.count(old)))
    p.write_text(s.replace(old,new,1))

cc='ns3/wsn-closed-loop.cc'
change(cc,'#include "selective_report_retry.h"','#include "selective_report_retry.h"\n#include "unified_control_budget.h"')
change(cc,'static bool reportRetry=false;', '''static bool unifiedBudget=false,protectEvidence=true,versionPacing=false;
static uint32_t controlRate=305,controlBurst=4572,controlReserve=1524,reportPhaseSeed=0;
static std::vector<controlbudget::Bucket> controlBuckets;
static bool reportRetry=false;''')
change(cc,'uint16_t node=0,depth=0,period=5;uint64_t stamp=0;','uint16_t node=0,depth=0,period=5;uint64_t stamp=0;bool critical=false;')
change(cc,'guarded::PackReportDepth(depth,period)','guarded::PackReportDepth(depth|(critical?0x2000:0),period)')
change(cc,'depth=guarded::ReportDepth(tagged);period=', 'depth=guarded::ReportDepth(tagged);critical=bool(depth&0x2000);depth&=0x1fff;period=')
change(cc,'static std::array<int64_t,9> lastGuardedReportNs{};', 'static std::vector<int64_t> lastGuardedReportNs(10);')
change(cc,'static std::array<unsigned,9> lastLocalReportState{};', 'static std::vector<unsigned> lastLocalReportState(10);')
change(cc,'    protocol<<"{\\"kind\\":\\"queue_arrival', '''    bool budgetAllowed=true;
    if(unifiedBudget&&h.flow>=65000&&s.alive&&s.queue.size()+bool(s.active)<capacity){
        bool priority=h.flow==65001;
        if(h.flow==65000){auto body=packet->Copy();RouteHeader route;body->RemoveHeader(route);ReportHeader report;body->PeekHeader(report);priority=report.critical;}
        priority=protectEvidence&&priority;
        auto a=controlBuckets.at(node).Take(Simulator::Now().GetNanoSeconds(),381,priority);budgetAllowed=a.admitted;
        protocol<<"{\\"kind\\":\\"unified_control_admission\\",\\"time_ns\\":"<<Simulator::Now().GetNanoSeconds()<<",\\"node\\":"<<node<<",\\"flow\\":"<<h.flow<<",\\"sequence\\":"<<h.sequence<<",\\"before_q\\":"<<a.before<<",\\"after_q\\":"<<a.after<<",\\"reservation_bytes\\":381,\\"priority\\":"<<(priority?"true":"false")<<",\\"admitted\\":"<<(a.admitted?"true":"false")<<"}\\n";
    }
    protocol<<"{\\"kind\\":\\"queue_arrival''')
change(cc,'(s.alive&&s.queue.size()+bool(s.active)<capacity)?', '(s.alive&&s.queue.size()+bool(s.active)<capacity&&budgetAllowed)?')
change(cc,'    s.enqueuedNs[Identity(h)]=', '    if(!budgetAllowed){Emit("control_budget_drop",node,h.flow,h.sequence);return;}\n    s.enqueuedNs[Identity(h)]=')
change(cc,'node>=2 && node<9','node>=2 && node!=9')
change(cc,'if(reportProfile=="local15_event"){','if(reportProfile=="local15_event" && !(versionPacing&&node<2)){')
change(cc,'    protocol<<"{\\"kind\\":\\"report_tick', '''    if(versionPacing&&node<2){
        auto sample=sourceHistory.at(node).Sample(now);
        bool failure=sample.currentN>=10&&uint64_t(sample.currentFailed)*100>uint64_t(sample.currentN)*20;
        auto c=controlbudget::SourceReport(now,lastGuardedReportNs[node],installedSinceNs[node],failure,localState,lastLocalReportState[node]);
        period=c.period;emitted=c.emit;
        protocol<<"{\\"kind\\":\\"version_report_admission\\",\\"time_ns\\":"<<now<<",\\"node\\":"<<node<<",\\"installed_ns\\":"<<installedSinceNs[node]<<",\\"last_emitted_ns\\":"<<lastGuardedReportNs[node]<<",\\"state\\":"<<localState<<",\\"previous_state\\":"<<lastLocalReportState[node]<<",\\"failure\\":"<<(failure?"true":"false")<<",\\"emitted\\":"<<(emitted?"true":"false")<<",\\"period_s\\":"<<period<<"}\\n";
        if(emitted){lastGuardedReportNs[node]=now;lastLocalReportState[node]=localState;}
    }
    protocol<<"{\\"kind\\":\\"report_tick''')
change(cc,'ReportHeader r;r.period=period;', 'ReportHeader r;r.critical=unifiedBudget&&(node<2||priorityUntil[node]>now);r.period=period;')
change(cc,'*simple.rbegin()>=10','*simple.rbegin()>=stations.size()')
change(cc,'cmd.AddValue("nodes"','cmd.AddValue("unifiedBudget","bound all control DATA MAC requests",unifiedBudget);\n    cmd.AddValue("protectEvidence","reserve credit for source/active-path evidence and installation",protectEvidence);\n    cmd.AddValue("versionPacing","version-conditioned source reporting",versionPacing);\n    cmd.AddValue("controlRate","control DATA reservation bytes per second",controlRate);\n    cmd.AddValue("controlBurst","initial control credit bytes",controlBurst);\n    cmd.AddValue("controlReserve","protected control credit bytes",controlReserve);\n    cmd.AddValue("reportPhaseSeed","outcome-independent reporting phase seed",reportPhaseSeed);\n    cmd.AddValue("nodes"')
change(cc,'NS_ABORT_MSG_IF(nodes!=10,"closed-loop prototype requires ten nodes");', '''NS_ABORT_MSG_IF(nodes<10||nodes>64,"study supports ten through sixty-four nodes");
    generatedBuckets.resize(nodes);ctrlNodeBytes.resize(nodes);priorityUntil.resize(nodes);
    lastGuardedReportNs.resize(nodes);lastLocalReportState.resize(nodes);radioLast.resize(nodes);
    radioState.resize(nodes,IEEE_802_15_4_PHY_TRX_OFF);radioDurations.resize(nodes);
    controlBuckets.assign(nodes,controlbudget::Bucket(controlRate,controlBurst,protectEvidence?controlReserve:0));''')
change(cc,'for(uint32_t i=0;i<9;i++)Simulator::Schedule(Seconds(5.1+i*.02),&SendReport,i,0u);', '''for(uint32_t i=0;i<nodes;i++)if(i!=9){
        double phase=5.1+i*.02;
        if(reportPhaseSeed){uint64_t z=uint64_t(reportPhaseSeed)*2654435761ULL+uint64_t(i)*11400714819323198485ULL;z^=z>>29;phase=5.05+double(z%950)/1000.;}
        Simulator::Schedule(Seconds(phase),&SendReport,i,0u);
    }''')
change(cc,'a.path.back()!=nodes-1','a.path.back()!=9')
change(cc,'relay<2||relay>8||','relay<2||relay==9||relay>=nodes||')

base='wsn/base_controller.py'
change(base,'    out=[]\n    def visit(path):', '''    if len(points)>10:
        import heapq
        queue=[(0,0.,(source,))];completed=[];expanded=0
        while queue and len(completed)<32 and expanded<100000:
            hops,length,path=heapq.heappop(queue);expanded+=1
            if path[-1]==9:completed.append(path);continue
            if len(path)>=7:continue
            for n in sorted(points):
                d=math.dist(points[n],points[path[-1]])
                if n not in path and n!=1-source and d<=65:
                    heapq.heappush(queue,(hops+1,length+d,path+(n,)))
        return completed
    out=[]
    def visit(path):''')
change(base,'set(self.points)!=set(range(10))', 'not 10<=len(self.points)<=64 or set(self.points)!=set(range(len(self.points)))')
change(base,'for n in range(9)}','for n in self.points if n!=9}')
change(base,'len(fresh)/9]','len(fresh)/(len(self.points)-1)]')

change('wsn/topology.py',"    if name=='base':return dict(BASE)",'''    if name.startswith('budget_'):
        _,count,seed=name.split('_');count=int(count);seed=int(seed)
        if count not in (10,20,40):raise ValueError('unsupported study scale')
        p={n:tuple(float(v)+12*(uniform(seed,'budget-layout',n,axis)-.5)for axis,v in enumerate(xy))if n not in(0,1,9)else xy for n,xy in BASE.items()}
        for n in range(10,count):p[n]=(20+80*uniform(seed,'extra-x',n),-40+80*uniform(seed,'extra-y',n))
        return p
    if name=='base':return dict(BASE)''')

run='run_closed_loop.py'
change(run,"ROOT.parent/'ns3_vendor/", "ROOT.parent.parent/'ns3_vendor/")
change(run,"controller_factory=None,controller_kwargs=None):", "controller_factory=None,controller_kwargs=None,unified_budget=False,protect_evidence=True,version_pacing=False,control_rate=305,control_burst=4572,control_reserve=1524,report_phase_seed=0):")
change(run,"report_retry_mode=report_retry_mode)","report_retry_mode=report_retry_mode,unified_budget=unified_budget,protect_evidence=protect_evidence,version_pacing=version_pacing,control_rate=control_rate,control_burst=control_burst,control_reserve=control_reserve,report_phase_seed=report_phase_seed)")
change(run,"'--nodes=10'","f'--nodes={len(points)}'")
change(run,"    if faults:cmd.append", "    cmd.extend([f'--unifiedBudget={int(unified_budget)}',f'--protectEvidence={int(protect_evidence)}',f'--versionPacing={int(version_pacing)}',f'--controlRate={control_rate}',f'--controlBurst={control_burst}',f'--controlReserve={control_reserve}',f'--reportPhaseSeed={report_phase_seed}'])\n    if faults:cmd.append")
change(run,"for node in range(10)]","for node in range(len(points))]")
change(run,"    record['controller_kwargs']=", "    record['unified_control']=dict(enabled=unified_budget,protected=protect_evidence,version_pacing=version_pacing,rate=control_rate,burst=control_burst,reserve=control_reserve,report_phase_seed=report_phase_seed)\n    record['controller_kwargs']=")
print('Isolated engine updated; original frozen engine unchanged')
