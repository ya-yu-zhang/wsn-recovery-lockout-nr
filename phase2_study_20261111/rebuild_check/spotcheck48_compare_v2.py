"""Comparison v2 for the 48 reruns already produced by spotcheck48.py (no new simulation).
Change vs v1 (logged deviation): record.json field hashes.controller is SHA256 of controller.json,
which itself contains wall-clock fields (compute_wall_ns, constraint_wall_ns, wall_seconds).
v2 accepts a hashes.controller difference ONLY if (i) each side equals sha256 of its own
controller.json bytes and (ii) the two controller.json files are equal after removing wall-clock
fields and paths. Every other byte / field must match."""
import json,os,gzip,hashlib,glob,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from spotcheck48 import strip
FROZEN='/workspace/wsn_ablation/repo/control_budget_study_20261015/results/amplification2_confirm'
NEW='/workspace/scratch_phase2/repro48'
rows=[]
for k in sorted(os.listdir(NEW)):
    bad=[];checked=0
    for f in sorted(os.listdir(f'{NEW}/{k}')):
        a=open(f'{FROZEN}/{k}/{f}','rb').read();b=open(f'{NEW}/{k}/{f}','rb').read();checked+=1
        if f.endswith('.gz'):a,b=gzip.decompress(a),gzip.decompress(b)
        if f.endswith('controller.json'):
            if strip(json.loads(a))!=strip(json.loads(b)):bad.append(f)
        elif f.endswith('record.json'):
            A=json.loads(a);B=json.loads(b)
            ca=open(glob.glob(f'{FROZEN}/{k}/*.controller.json')[0],'rb').read();cb=open(glob.glob(f'{NEW}/{k}/*.controller.json')[0],'rb').read()
            okhash=A['hashes']['controller']==hashlib.sha256(ca).hexdigest() and B['hashes']['controller']==hashlib.sha256(cb).hexdigest()
            A['hashes'].pop('controller');B['hashes'].pop('controller')
            if not okhash or strip(A)!=strip(B):bad.append(f)
        elif a!=b:bad.append(f)
    rows.append(dict(case=k,files=checked,mismatch=bad))
out=dict(n=len(rows),all_match=sum(not r['mismatch'] for r in rows),rows=rows)
json.dump(out,open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'spotcheck48_result_v2.json'),'w'),indent=1)
print('MATCH',out['all_match'],'/',out['n'],'files',sum(r['files'] for r in rows))
