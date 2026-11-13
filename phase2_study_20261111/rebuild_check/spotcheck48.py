"""Rebuild spot-check: rerun 48 frozen Amp-2 confirm cases (fixed sampling seed 20261111)
with the rebuilt ns-3 libraries and the UNCHANGED registered binary; compare all outputs
byte-for-byte, except wall-clock fields and output paths. Writes nothing into frozen results."""
import sys,json,glob,os,gzip,random,re,hashlib,concurrent.futures
ROOTS='/workspace/wsn_ablation/repo/control_budget_study_20261015'
sys.path.insert(0,ROOTS);sys.path.insert(0,ROOTS+'/engine');os.chdir(ROOTS)
from run_study import ENGINE
from fast_native_run import one
from run_mechanisms import policy
from amplification_arms import AmplifiedHorizon
from pathlib import Path
OUT=Path('/workspace/scratch_phase2/repro48')
WALL=re.compile(r'(wall_ns|wall_seconds)$')
def strip(o,k=''):
    if isinstance(o,dict): return {a:strip(b,a) for a,b in o.items() if not WALL.search(a) and a!='command'}
    if isinstance(o,list): return [strip(x) for x in o]
    if isinstance(o,str) and o.startswith(('/workspace','/tmp')): return '<path>'
    return o
def run(cp):
    old=json.load(open(cp));c=old['configuration'];folder=OUT/old['configuration_key'];folder.mkdir(parents=True,exist_ok=True)
    one(ENGINE/'ns3/wsn-closed-loop',c['scenario'],policy('resource10_on'),c['seed'],folder=folder,profile='local15_event',topology=c['topology'],extended=True,
        source_only=True,generation_stop=330,faults=c['faults'],queue_discipline='fifo',epoch_certificate=True,report_retry=True,report_budget=True,report_retry_mode='always',
        controller_factory=AmplifiedHorizon,controller_kwargs={'pacing':True,'evidence_gate':True,'arm':c['arm']},unified_budget=True,protect_evidence=True,version_pacing=True,
        report_phase_seed=c['seed'],drop_install_start_sec=c.get('drop_install_start_sec',-1.0),drop_install_end_sec=c.get('drop_install_end_sec',-1.0),drop_install_mask=c.get('drop_install_mask',0))
    src=os.path.dirname(cp);res=[]
    for f in sorted(os.listdir(folder)):
        a=open(os.path.join(src,f),'rb').read();b=open(folder/f,'rb').read()
        if f.endswith('.gz'):a,b=gzip.decompress(a),gzip.decompress(b)
        if f.endswith(('controller.json','record.json')):
            same=strip(json.loads(a))==strip(json.loads(b));mode='json-minus-wall/path'
        else: same=a==b;mode='bytes'
        res.append((f,mode,same))
    return dict(case=old['configuration_key'],arm=c['arm'],topology=c['topology'],seed=c['seed'],files=len(res),all_match=all(s for _,_,s in res),mismatch=[f for f,_,s in res if not s])
if __name__=='__main__':
    cases=sorted(glob.glob('results/amplification2_confirm/*/case.json'));random.seed(20261111);pick=random.sample(cases,48)
    with concurrent.futures.ProcessPoolExecutor(6) as ex: rows=list(ex.map(run,pick))
    s=dict(n=len(rows),all_match=sum(r['all_match'] for r in rows),arms=sorted({r['arm'] for r in rows}),topologies=len({r['topology'] for r in rows}),rows=rows,
           binary_sha256=hashlib.sha256(open(ENGINE/'ns3/wsn-closed-loop','rb').read()).hexdigest())
    json.dump(s,open('/workspace/wsn_paper_priv/phase2_study_20261111/rebuild_check/spotcheck48_result.json','w'),indent=1)
    print('MATCH',s['all_match'],'/',s['n'],'arms',len(s['arms']),'topologies',s['topologies'],s['binary_sha256'])
