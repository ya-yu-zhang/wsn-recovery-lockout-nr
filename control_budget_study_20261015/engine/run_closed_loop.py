from pathlib import Path
import copy,subprocess,os,csv,json,math,hashlib,gzip,time,uuid
import numpy as np
from wsn.rng import uniform
from wsn.topology import geometry
from wsn.controller import Controller,POINTS,INITIAL
ROOT=Path(__file__).resolve().parent;NSROOT=ROOT.parent.parent/'ns3_vendor/ns-allinone-3.44/ns-3.44';OUT=ROOT/'results/native'


def compile_driver():
    assert (NSROOT/'VERSION').read_text().strip()=='3.44', 'requires pinned ns-3.44'
    b=NSROOT/'build';binary=ROOT/'ns3/wsn-closed-loop';cmd=['g++','-std=c++20','-O2','-I',str(b/'include'),str(ROOT/'ns3/wsn-closed-loop.cc'),'-L',str(b/'lib'),'-Wl,-rpath,'+str(b/'lib')]
    cmd+=['-lns3.44-'+x for x in ('lr-wpan','spectrum','mobility','propagation','antenna','network','stats','core')];cmd+=['-o',str(binary)]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr)
    (ROOT/'results/compile.json').write_text(json.dumps(dict(command=cmd,source_sha256=hashlib.sha256((ROOT/'ns3/wsn-closed-loop.cc').read_bytes()).hexdigest()),indent=2));return binary


def atomic_gzip(path,payload):
    temp=path.parent/('.gzip-'+uuid.uuid4().hex)
    with temp.open('wb') as f:f.write(gzip.compress(payload));f.flush();os.fsync(f.fileno())
    assert gzip.decompress(temp.read_bytes())==payload;os.replace(temp,path)


def arrivals(scenario,seed,generation_stop=90):
    rates={'steady':(5,20,5),'failure':(5,15,5),'multi_failure':(5,20,5),'overload':(10,40,10)}[scenario];out=[]
    for f in (0,1):
        seq=0
        for stage in range(math.ceil(generation_stop/30)):
            rate=rates[stage%3]
            t=stage*30.
            while True:
                t+=-math.log(uniform(seed,'phase11offered',scenario,f,stage,seq))/rate
                if t>=min((stage+1)*30.,generation_stop):break
                out.append((t,f,seq,INITIAL[f]));seq+=1
    return sorted(out)


def one(binary,scenario,policy,seed,broken=False,missing=False,folder=OUT,profile='full5',reject=False,topology='base',extended=True,source_only=False,generation_stop=90,faults=None,queue_discipline="fifo",epoch_certificate=False,report_retry=False,report_budget=False,report_retry_mode='always',controller_factory=None,controller_kwargs=None,unified_budget=False,protect_evidence=True,version_pacing=False,control_rate=305,control_burst=4572,control_reserve=1524,report_phase_seed=0):
    if generation_stop<30 or generation_stop%5:raise ValueError('horizon must be a multiple of five seconds')
    faults=([(35,2)] if scenario=='failure' else []) if faults is None else list(faults)
    action_stop_ns=int(generation_stop-10)*1_000_000_000
    stop=generation_stop+20
    points=geometry(topology)
    folder.mkdir(parents=True,exist_ok=True)
    identity=dict(topology=topology,scenario=scenario,profile=profile,policy=policy,seed=seed,broken=broken,missing=missing,reject=reject,extended=extended,source_only=source_only,generation_stop=generation_stop,faults=faults,queue=queue_discipline,epoch=epoch_certificate,report_retry=report_retry,report_budget=report_budget,report_retry_mode=report_retry_mode,unified_budget=unified_budget,protect_evidence=protect_evidence,version_pacing=version_pacing,control_rate=control_rate,control_burst=control_burst,control_reserve=control_reserve,report_phase_seed=report_phase_seed)
    stem='observable_'+hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24];prefix=folder/stem
    apath=Path(str(prefix)+'_arrivals.csv');rows=arrivals(scenario,seed,generation_stop)
    with apath.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(('time','flow','sequence','path'));w.writerows((t,flow,seq,';'.join(map(str,p))) for t,flow,seq,p in rows)
    ppath=Path(str(prefix)+'_positions.csv');ppath.write_text('node,x,y\n'+''.join(f'{n},{x},{y}\n' for n,(x,y) in sorted(points.items())))
    cmd=[str(binary),f'--nodes={len(points)}',f'--run={seed}',f'--arrivals={apath}',f'--positions={ppath}',f'--output={prefix}',f'--stop={stop}',f'--generationStop={generation_stop}','--compact=1','--monitor=1','--failAt=-1',f'--brokenInstall={int(broken)}',f'--suppressReports={int(missing)}',f'--reportProfile={profile}',f'--rejectFirstSource1={int(reject)}']
    cmd.append(f'--extendedReport={int(extended)}')
    cmd.append(f'--sourceOnlyCounters={int(source_only)}')
    cmd.extend([f'--queueDiscipline={queue_discipline}',f'--epochCertificate={int(epoch_certificate)}',f'--reportRetry={int(report_retry)}',f'--reportBudget={int(report_budget)}'])
    cmd.append(f'--reportRetryMode={report_retry_mode}')
    cmd.extend([f'--unifiedBudget={int(unified_budget)}',f'--protectEvidence={int(protect_evidence)}',f'--versionPacing={int(version_pacing)}',f'--controlRate={control_rate}',f'--controlBurst={control_burst}',f'--controlReserve={control_reserve}',f'--reportPhaseSeed={report_phase_seed}'])
    if faults:cmd.append('--faultSchedule='+';'.join(f'{when}:{relay}' for when,relay in faults))
    factory=Controller if controller_factory is None else controller_factory
    controller=factory(policy,profile,points=points,action_stop_ns=action_stop_ns,selection_seed=seed,**(controller_kwargs or {}));steps=[];start=time.time()
    with Path(str(prefix)+'.stderr.log').open('w') as err:
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1)
        try:
            for line in proc.stdout:
                if not line.startswith('STEP '):raise ValueError('unexpected native output '+line[:200])
                obs=json.loads(line[5:]);reply,log=controller.step(obs);steps.append(copy.deepcopy(log));proc.stdin.write(reply+'\n');proc.stdin.flush()
            code=proc.wait(timeout=30)
            if code:raise RuntimeError(Path(str(prefix)+'.stderr.log').read_text())
        except BaseException:proc.kill();proc.wait();raise
    summary=json.loads(Path(str(prefix)+'.json').read_text());protocol=Path(str(prefix)+'.protocol.jsonl').read_text().splitlines();messages=[json.loads(x) for x in protocol]
    timely=[sum(x['kind']=='delivered' and x['flow']==f and (x['time_ns']-x['generated_ns'])<=200_000_000 for x in messages)/sum(x['flow']==f for x in messages if x['kind']=='generated') for f in (0,1)]
    radio=np.loadtxt(Path(str(prefix)+'.radio.csv'),delimiter=',',skiprows=1,dtype=np.int64,ndmin=2)
    currents={1:18.8,2:17.4,6:18.8,9:17.4,8:.426};assert set(radio[:,3])<=set(currents)
    energy=[sum((int(e)-int(b))/1e9*3*currents[int(s)]/1000 for n,b,e,s in radio if n==node) for node in range(len(points))]
    record=dict(id=stem,topology=topology,points=points,scenario=scenario,policy=policy,report_profile=profile,seed=seed,extended_report=extended,source_only_counters=source_only,generation_stop=generation_stop,action_stop_ns=action_stop_ns,selection_seed=seed,faults=faults,broken_install=broken,source_reports_missing=missing,source1_first_rejection=reject,
      safety_events=getattr(controller,'safety_events',[]),install_reservations=getattr(controller,'install_reservations',[]),cost_observations=getattr(controller,'cost_observations',[]),report_budget=report_budget,reward_waits=getattr(controller,"reward_waits",[]),report_retry=report_retry,report_retry_mode=report_retry_mode,queue_discipline=queue_discipline,epoch_certificate=epoch_certificate,command=cmd,native=summary,offered=len(rows),timely_by_party=timely,mean_timely=sum(timely)/2,worst_party_timely=min(timely),
      estimated_radio_joules_by_node=energy,estimated_radio_joules=sum(energy),energy_scope='CC2420-like radio model only; no battery depletion/CPU/sensor/transient energy',
      decisions=controller.logs,retries=controller.retries,installations=[dict(decision=x.decision,retry_limit=x.retry_limit,history=x.history,closed=x.closed,outcome=x.outcome) for x in controller.installations],feedbacks=controller.feedbacks,feedback_waits=controller.feedback_waits,bandit_updates=controller.bandit.updates,
      constraint_pair_checks=sum(x['candidate_pair_freshness_checks'] for x in controller.constraint_logs),
      constraint_wall_ns=sum(x['constraint_wall_ns'] for x in controller.constraint_logs),total_fe=sum(r['fe'] for r in controller.logs),wall_seconds=time.time()-start,hashes={})
    record['unified_control']=dict(enabled=unified_budget,protected=protect_evidence,version_pacing=version_pacing,rate=control_rate,burst=control_burst,reserve=control_reserve,report_phase_seed=report_phase_seed)
    record['controller_kwargs']=controller_kwargs or {}
    record['state_candidates']=getattr(controller,'state_candidates',[])
    record['fork_info']=getattr(controller,'fork_info',None)
    cpath=Path(str(prefix)+'.controller.json');cpath.write_text(json.dumps(dict(safety_events=getattr(controller,'safety_events',[]),install_reservations=getattr(controller,'install_reservations',[]),cost_observations=getattr(controller,'cost_observations',[]),policy=policy,report_profile=profile,retry_limit=controller.retry_limit,retries=controller.retries,installations=record['installations'],feedback_waits=controller.feedback_waits,reward_waits=getattr(controller,"reward_waits",[]),warmup_attempts=controller.warmup_attempts,event_attempts=controller.event_attempts,constraint_logs=controller.constraint_logs,steps=steps,bandit_A=controller.bandit.A.tolist(),bandit_b=controller.bandit.b.tolist(),memory=controller.memory),indent=2))
    for suffix in ('.csv','.jobs.csv','.protocol.jsonl','.radio.csv'):
        p=Path(str(prefix)+suffix);payload=p.read_bytes();record['hashes'][suffix]=hashlib.sha256(payload).hexdigest();atomic_gzip(Path(str(p)+'.gz'),payload);p.unlink()
    record['hashes']['positions']=hashlib.sha256(ppath.read_bytes()).hexdigest();record['hashes']['arrivals']=hashlib.sha256(apath.read_bytes()).hexdigest();record['hashes']['controller']=hashlib.sha256(cpath.read_bytes()).hexdigest()
    Path(str(prefix)+'.record.json').write_text(json.dumps(record,indent=2));return record


def main():
    from run_development import main as development_main
    development_main()

if __name__=='__main__':main()
