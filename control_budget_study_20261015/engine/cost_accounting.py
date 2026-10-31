"""Reconcile actual control cost; requires the restored phase11 evidence.

This program produces no simulated/pseudo research outcomes when input is absent.
Tests use labelled small accounting fixtures, not benchmark results.
"""
from pathlib import Path
import argparse,csv,gzip,hashlib,importlib.util,io,json,statistics as S

def trace(path,root):
    if path.exists():return gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes()
    if path.name.endswith('.csv.gz'):
        encoded=Path(str(path)[:-7]+'.ccsv.xz');codec=root/'wsn/csv_archive.py'
        if encoded.exists() and codec.exists():
            spec=importlib.util.spec_from_file_location('phase11_lossless_codec',codec)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            return module.decode(encoded.read_bytes())
    raise FileNotFoundError('missing original phase11 trace: '+str(path))

def reconcile(messages,jobs,record):
    packets={};applied=[];received=[];phy=[];ack=[];generated=[];delivered=[]
    for x in messages:
        k=x['kind']
        if k=='install_packet':
            if x['sequence'] in packets:raise ValueError('duplicate installation sequence')
            packets[x['sequence']]=x
        elif k=='install_applied':applied.append(x)
        elif k=='install_received':received.append(x)
        elif k=='phy_data':phy.append(x)
        elif k=='phy_ack':ack.append(x)
        elif k=='generated':generated.append(x)
        elif k=='delivered':delivered.append(x)
    transactions={}
    for seq,x in packets.items():
        key=(x['decision'],x['source']);row=transactions.setdefault(key,dict(decision=key[0],source=key[1],
            initial_packets=0,retry_packets=0,initial_data_bytes=0,retry_data_bytes=0,
            actual_applied_ns=None,actual_receipt_count=0,duplicate_receipt_count=0))
        row['retry_packets' if x['retry'] else 'initial_packets']+=1
    report_bytes=install_bytes=other_control=application_bytes=0
    for x in phy:
        if x['flow']==65000:report_bytes+=x['bytes']
        elif x['flow']==65001:
            if x['sequence'] not in packets:raise ValueError('unattributed installation DATA')
            p=packets[x['sequence']];transactions[p['decision'],p['source']]['retry_data_bytes' if p['retry'] else 'initial_data_bytes']+=x['bytes']
            install_bytes+=x['bytes']
        elif x['flow']>=65000:other_control+=x['bytes']
        elif x['flow'] in (0,1):application_bytes+=x['bytes']
        else:raise ValueError('unknown application flow')
    for x in applied:
        key=(x['decision'],x['source'])
        if key not in transactions:raise ValueError('unattributed actual installation')
        row=transactions[key]
        if row['actual_applied_ns'] is not None:raise ValueError('version applied twice')
        row['actual_applied_ns']=x['time_ns']
    for x in received:
        row=transactions[x['decision'],x['source']];row['actual_receipt_count']+=1
        row['duplicate_receipt_count']+=x['previous_version']==x['decision']
    ctrl=report_bytes+install_bytes+other_control;ackbytes=sum(x['bytes'] for x in ack)
    if (ctrl,application_bytes,ackbytes)!=tuple(record['native'][k] for k in ('control_psdu_bytes','application_psdu_bytes','ack_psdu_bytes')):
        raise ValueError('native byte summary mismatch')
    for x in jobs:
        if len(x)!=28 or x[5]<=0 or x[7]<0:raise ValueError('invalid28column native job')
    if len(jobs)!=record['native']['finalized_jobs']:raise ValueError('native job count mismatch')
    if sum(r[9] for r in jobs)!=len(phy):raise ValueError('MAC/DATA attempt mismatch')
    if len({tuple(r[:3]) for r in jobs})!=len(jobs):raise ValueError('duplicate native job')
    classes={}
    for label,accept in [('source_application',lambda r:r[0]<2 and r[1]==r[0]),
                         ('all_application',lambda r:r[1]<2),
                         ('report',lambda r:r[1]==65000),('installation',lambda r:r[1]==65001)]:
        xs=[r for r in jobs if accept(r)];q=sorted(r[7]/1e6 for r in xs)
        classes[label]=dict(jobs=len(xs),failed=sum(r[8]!=0 for r in xs),
            queue_mean_ms=S.mean(q) if q else None,queue_max_ms=max(q) if q else None,
            queue_p95_ms=q[max(0,(95*len(q)+99)//100-1)] if q else None,
            summed_queue_ms=sum(q),summed_mac_J_ms=sum(r[5]/1e6 for r in xs),data_attempts=sum(r[9] for r in xs))
    initial=sum(r['initial_data_bytes'] for r in transactions.values());retry=sum(r['retry_data_bytes'] for r in transactions.values())
    if initial+retry!=install_bytes:raise ValueError('installation DATA partition mismatch')
    # Same-path installs do not change the path but still increment its version.
    current={0:[0,2,3,9],1:[1,2,3,9]};same_path=0
    for x in sorted(applied,key=lambda x:x['time_ns']):
        same_path+=x['path']==current[x['source']];current[x['source']]=x['path']
    return dict(report_data_bytes=report_bytes,initial_install_data_bytes=initial,retry_install_data_bytes=retry,
        other_control_data_bytes=other_control,total_control_data_bytes=ctrl,global_ack_bytes=ackbytes,
        ack_attribution='global only; not inferred as per-control or per-transaction ACK',
        classes=classes,transactions=list(transactions.values()),same_path_install_applications=same_path,
        duplicate_install_receipts=sum(r['duplicate_receipt_count'] for r in transactions.values()),
        generated_by_party=[sum(x['flow']==f for x in generated) for f in (0,1)],
        timely_by_party=[sum(x['flow']==f and x['time_ns']-x['generated_ns']<=200_000_000 for x in delivered) for f in (0,1)])

def case(root,r):
    prefix=root/'results/native'/r['id']
    for suffix,h in r['hashes'].items():
        path=Path(str(prefix)+('_arrivals.csv' if suffix=='arrivals' else '_positions.csv' if suffix=='positions' else '.controller.json' if suffix=='controller' else suffix+'.gz'))
        if hashlib.sha256(trace(path,root)).hexdigest()!=h:raise ValueError('original hash mismatch: '+r['id']+' '+suffix)
    messages=[json.loads(l) for l in trace(Path(str(prefix)+'.protocol.jsonl.gz'),root).decode().splitlines()]
    jobs=[[int(v) for v in row] for row in list(csv.reader(io.StringIO(trace(Path(str(prefix)+'.jobs.csv.gz'),root).decode())))[1:]]
    costs=reconcile(messages,jobs,r)
    if costs['generated_by_party']!=r['native']['offered'] or costs['timely_by_party']!=r['native']['timely']:
        raise ValueError('native source service count mismatch')
    actual=[a/b for a,b in zip(costs['timely_by_party'],costs['generated_by_party'])]
    if any(abs(a-b)>1e-12 for a,b in zip(actual,r['timely_by_party'])):
        raise ValueError('recorded timely delivery mismatch')
    costs.update(id=r['id'],topology=r['topology'],seed=r['seed'],policy=r['policy'],mean_timely_pct=100*r['mean_timely'],
        worst_timely_pct=100*r['worst_party_timely'],total_fe=r['total_fe'],constraint_pair_checks=r['constraint_pair_checks'],
        constraint_wall_ns=r['constraint_wall_ns'],decisions=len(r['decisions']),retries=len(r['retries']),
        declared_install_budget_bytes=sum(d['install_budget_bytes'] for d in r['decisions']),
        missing_feedbacks=sum(f['reward'] is None for f in r['feedbacks']))
    return costs

def main():
    p=argparse.ArgumentParser();p.add_argument('--phase11-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    root=args.phase11_root.resolve();manifest=root/'results/native_manifest.json'
    if not manifest.exists():p.error('phase11 complete manifest is unavailable; restore its four delivered ZIPs first')
    runs=json.loads(manifest.read_text());xs=[r for r in runs if r['scenario']=='overload']
    if len(runs)!=216 or len(xs)!=72:raise ValueError('requires complete phase11 matrix, not a selected subset')
    rows=[case(root,r) for r in xs];index={(r['topology'],r['seed'],r['policy']):r for r in rows};paired=[]
    for topo in ('base','jitter_a','jitter_b'):
        for seed in range(970001,970007):
            a=index[topo,seed,'linucb_event_scalar4_failure_retry_mask'];b=index[topo,seed,'fixed_local']
            new=next(r for r in xs if r['id']==a['id']);fixed=next(r for r in xs if r['id']==b['id'])
            if new['hashes']['arrivals']!=fixed['hashes']['arrivals']:raise ValueError('unpaired offered traffic')
            keys=['report_data_bytes','initial_install_data_bytes','retry_install_data_bytes','total_control_data_bytes',
                  'global_ack_bytes','same_path_install_applications','duplicate_install_receipts','total_fe','constraint_pair_checks','decisions','retries','missing_feedbacks']
            paired.append(dict(topology=topo,seed=seed,timely_pp=a['mean_timely_pct']-b['mean_timely_pct'],
                worst_pp=a['worst_timely_pct']-b['worst_timely_pct'],delta={k:a[k]-b[k] for k in keys}))
    result=dict(status='passed',scope='offline observed cost decomposition, not causal mediation',
        original_cases=72,paired_conditions=18,original_trace_hashes_checked=True,cases=rows,paired=paired,
        limit='do not infer control-ACK attribution, CPU-injected delay, or retry causality from this decomposition')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(status='passed',overload_cases=72,paired_conditions=18)))
if __name__=='__main__':main()
