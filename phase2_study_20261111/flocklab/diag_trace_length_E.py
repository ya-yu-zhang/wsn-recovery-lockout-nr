"""Exploratory (E), read-only: stream length of each replayed FlockLab link vs frames evaluated on it per run (R2 wrap-around)."""
import json, csv, statistics
from pathlib import Path
H=Path(__file__).parent
runs={r['key']:r for r in json.load(open(H/'results_full/runs.json'))['rows']}
audit=json.load(open(H/'results_full/link_audit.json'))
lens={}
for f in (H/'traces').glob('subgraph_*.csv'):
    for r in csv.DictReader(open(f)): lens[(f.stem.split('_')[1],int(r['src']),int(r['dst']))]=len(r['bits'])
stat={'A':[], 'B':[]}; wrap={'A':0,'B':0}; tot={'A':0,'B':0}; maxratio={'A':0,'B':0}
for a in audit:
    c=runs[a['key']]['configuration']
    if c['trace_mode']!=2: continue
    d=c['day']
    for L in a['links']:
        n=lens.get((c['subgraph'],L['src'],L['dst']))
        if not n or L['evaluated']==0: continue
        tot[d]+=1; wrap[d]+= L['evaluated']>n; maxratio[d]=max(maxratio[d],L['evaluated']/n)
for d in 'AB':
    ls=[v for k,v in lens.items() if k[0].startswith(d) and v>0]
    stat[d]=dict(stream_len_min=min(ls),stream_len_median=statistics.median(ls),stream_len_max=max(ls),
                 R2_link_runs_with_frames=tot[d],R2_link_runs_wrapping=wrap[d],max_evaluated_over_length=round(maxratio[d],2))
json.dump(stat,open(H/'results_full/trace_length_diagnostic_E.json','w'),indent=1); print(json.dumps(stat,indent=1))
