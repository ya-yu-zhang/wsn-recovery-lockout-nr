"""Read existing native evidence; no simulator imports, actions or new runs."""
from pathlib import Path
import argparse,collections,gzip,hashlib,json,math,zipfile

ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results'
OLD=ROOT.parent/'control_budget_study_20261015/results'
TARGET=(10,'multi_failure',2026101511)
BOUNDARIES=(0,65,145,225,330)

def read_json(z,path):return json.loads(z.read(path))
def digest(b):return hashlib.sha256(b).hexdigest()
def phase(t):
    for i,(a,b)in enumerate(zip(BOUNDARIES,BOUNDARIES[1:])):
        if a*10**9<=t<b*10**9:return i
    raise AssertionError(('generation outside registered horizon',t))
def key(row):
    c=row['configuration']
    return (int(c['topology'].split('_')[1]),c['scenario'],c['seed'])

def native_packets(z,case_path,row,probe=False):
    prefix=str(Path(case_path).parent/row['id'])
    name=prefix+'.protocol.jsonl.gz'
    generated={};delivered={};counts=collections.Counter();examples={};sha=hashlib.sha256()
    with z.open(name)as archive_entry,gzip.GzipFile(fileobj=archive_entry)as f:
        for line in f:
            sha.update(line);e=json.loads(line);kind=e['kind'];counts[kind]+=1
            if probe and kind not in examples:examples[kind]=e
            if kind=='generated':
                p=(e['flow'],e['sequence']);assert p not in generated;generated[p]=e
            elif kind=='delivered':
                p=(e['flow'],e['sequence']);assert p not in delivered;delivered[p]=e
    assert sha.hexdigest()==row['hashes']['.protocol.jsonl']
    assert set(delivered)<=set(generated)
    flow=[]
    for source in(0,1):
        offers=[0]*4;timely=[0]*4;late=[0]*4
        for p,e in generated.items():
            if p[0]!=source:continue
            i=phase(e['time_ns']);offers[i]+=1;d=delivered.get(p)
            if d is not None:
                assert d['generated_ns']==e['time_ns']
                if d['time_ns']-e['time_ns']<=200_000_000:timely[i]+=1
                else:late[i]+=1
        n=sum(offers);success=sum(timely)
        assert n==row['audit']['offered'][source]
        assert success==row['audit']['timely'][source]
        flow.append(dict(source=source,offered=n,timely=success,service=success/n,
            phases=[dict(begin_s=a,end_s=b,offered=offers[i],timely=timely[i],late=late[i],
                undelivered=offers[i]-timely[i]-late[i])for i,(a,b)in enumerate(zip(BOUNDARIES,BOUNDARIES[1:]))]))
    return dict(flows=flow,event_counts=dict(counts),native_event_examples=examples if probe else None)

def scalar_tree(obj,depth=0):
    if depth>5:return {'type':type(obj).__name__}
    if isinstance(obj,dict):return {k:scalar_tree(v,depth+1)for k,v in obj.items()}
    if isinstance(obj,list):
        if len(obj)<=8:return [scalar_tree(v,depth+1)for v in obj]
        return {'list_length':len(obj),'first_two':[scalar_tree(v,depth+1)for v in obj[:2]]}
    return obj

def controller_probe(z,case_path,row):
    prefix=str(Path(case_path).parent/row['id']);raw=z.read(prefix+'.controller.json')
    assert digest(raw)==row['hashes']['controller']
    c=json.loads(raw);out=[];rejections=collections.Counter()
    for s in c['steps']:
        obs=s['observation'];t=obs['time_ns']/1e9
        if s.get('rejection')is not None:rejections[str(s['rejection'])]+=1
        # Exact recorded diagnosis and constraints; large observation arrays omitted.
        thin={k:scalar_tree(v)for k,v in s.items()if k!='observation'}
        thin['time_s']=t
        thin['source_reports']=[{k:r.get(k)for k in('node','stamp_ns','received_ns','version','period_s','current_n','current_failed','epoch_first_bucket')}for r in obs['reports']if r['node']in(0,1)]
        thin['observation_other_fields']={k:scalar_tree(v)for k,v in obs.items()if k not in('reports','timely_buckets')}
        out.append(thin)
    return dict(controller_top_fields=list(c),step_top_fields=list(c['steps'][0]),
        rejection_counts=dict(rejections),installations=c.get('installations'),
        retries=c.get('retries'),feedback_waits=scalar_tree(c.get('feedback_waits')),
        safety_events=scalar_tree(c.get('safety_events')),steps=out,
        decisions=scalar_tree(row.get('decisions')),native_summary=scalar_tree(row.get('native')))

def compare(a,b,configuration):
    # a = treatment, b = Legacy; phase contributions use one full-run denominator per source.
    flows=[]
    for f in(0,1):
        aa,bb=a['flows'][f],b['flows'][f];assert aa['offered']==bb['offered']
        n=aa['offered'];v=[]
        for x,y in zip(aa['phases'],bb['phases']):
            assert x['offered']==y['offered']
            v.append(dict(begin_s=x['begin_s'],end_s=x['end_s'],offered=x['offered'],
                legacy_timely=y['timely'],treatment_timely=x['timely'],
                timely_delta=x['timely']-y['timely'],contribution_to_full_run_source_delta_pp=100*(x['timely']-y['timely'])/n))
        delta=100*(aa['service']-bb['service'])
        assert math.isclose(sum(p['contribution_to_full_run_source_delta_pp']for p in v),delta,abs_tol=1e-12)
        flows.append(dict(source=f,service_delta_pp=delta,phases=v))
    bottleneck=min((0,1),key=lambda f:a['flows'][f]['service'])
    legacy_worst=min(x['service']for x in b['flows'])
    correction=100*(b['flows'][bottleneck]['service']-legacy_worst)
    delta=100*(a['flows'][bottleneck]['service']-legacy_worst)
    assert math.isclose(flows[bottleneck]['service_delta_pp']+correction,delta,abs_tol=1e-12)
    return dict(configuration=configuration,flows=flows,treatment_bottleneck_source=bottleneck,
        legacy_bottleneck_source=min((0,1),key=lambda f:b['flows'][f]['service']),
        worst_source_delta_pp=delta,bottleneck_reference_correction_pp=correction)

def main():
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);a=p.parse_args()
    assert a.archive.stat().st_size==708954632
    with a.archive.open('rb')as f:
        sha=hashlib.file_digest(f,'sha256').hexdigest()
    assert sha=='fdf083436532c88613103363ea548f243cae0b5b525ab1cbc656ffa7d865674d'
    expected=json.loads((OLD/'horizon_development_manifest.json').read_text())
    audits=json.loads((OLD/'horizon_development_admission_audit.json').read_text())['records']
    expected_keys={r['configuration_key']for r in expected};case_hash={r['configuration_key']:r['case_sha256']for r in audits}
    records={};group={};parsed={};probes={};inputs=[]
    with zipfile.ZipFile(a.archive)as z:
        names=[n for n in z.namelist()if n.endswith('/case.json')];assert len(names)==40
        for name in names:
            raw=z.read(name);r=json.loads(raw);k=r['configuration_key'];assert k not in records
            assert digest(raw)==case_hash[k]
            assert r['audit']['status']=='passed'and r['bandit_updates']==[0,0,0,0]
            records[k]=(name,r);g=key(r);model=r['configuration']['model'];group.setdefault(g,{})[model]=k
            prefix=str(Path(name).parent/r['id'])
            for label,suffix in(('arrivals','_arrivals.csv'),('positions','_positions.csv')):
                assert digest(z.read(prefix+suffix))==r['hashes'][label]
            inputs.append(dict(configuration_key=k,group=list(g),model=model,
                arrivals_sha256=r['hashes']['arrivals'],positions_sha256=r['hashes']['positions']))
        assert set(records)==expected_keys
        for g,models in group.items():
            assert len(models)==5
            for field in('arrivals','positions'):
                assert len({records[k][1]['hashes'][field]for k in models.values()})==1
        selected=[k for k,(_,r)in records.items()if r['configuration']['model']in('legacy','full_v2')or key(r)==TARGET]
        assert len(selected)==19
        for k in selected:
            name,r=records[k];target=key(r)==TARGET
            parsed[k]=native_packets(z,name,r,probe=target)
            if target:probes[r['configuration']['model']]=controller_probe(z,name,r)
            print('READ_EXISTING_PROTOCOL',len(parsed),19,r['configuration'],flush=True)
        pairs=[]
        for g,models in sorted(group.items()):
            for m in(('full_v2','horizon','cohort','closing')if g==TARGET else('full_v2',)):
                k=models[m];pairs.append(compare(parsed[k],parsed[models['legacy']],records[k][1]['configuration']))
    result=dict(archive_sha256=sha,case_files_hash_checked=40,matched_input_cells_hash_verified=8,
        native_protocols_read=19,paired_comparisons=len(pairs),exploratory=True,new_simulation_runs=0,
        runtime_LLM_calls=0,selected_adverse_cell=list(TARGET),selection='largest adverse cell in previously inspected screen',
        phase_definition_s=list(BOUNDARIES),phase_assignment='generation time, not delivery time',
        source_diagnosis_sha256=digest(Path(__file__).read_bytes()),pairs=pairs,
        protocol_event_counts={k:v['event_counts']for k,v in parsed.items()},inputs=inputs)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS/'trace_phase_diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
    (RESULTS/'target_controller_probe.json').write_text(json.dumps(probes,indent=2)+'\n')
    (RESULTS/'target_native_schema.json').write_text(json.dumps({records[k][1]['configuration']['model']:v['native_event_examples']for k,v in parsed.items()if v['native_event_examples']is not None},indent=2)+'\n')
    print('COMPLETE_EXISTING_DATA_DIAGNOSIS',dict(cases=40,protocols=19,new_simulations=0),flush=True)

if __name__=='__main__':main()
