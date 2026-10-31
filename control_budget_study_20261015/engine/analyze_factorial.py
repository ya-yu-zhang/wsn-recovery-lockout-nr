"""All registered paired effects; no significance claims from two layouts."""
import argparse,csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--allow-incomplete',action='store_true');a=p.parse_args()
 reg=json.loads((ROOT/'docs/factorial_development_registration.json').read_text())
 rows=json.loads((ROOT/'results/factorial_development_manifest.json').read_text())
 complete=len(rows)==len(reg['configs'])
 if not complete and not a.allow_incomplete:raise ValueError('incomplete registered development matrix')
 def byte_cost(row):return row['native']['control_psdu_bytes']
 by={(r['topology'],r['scenario'],r['model'],r['schedule'],r['freshness'],r['seed']):r for r in rows}
 contrasts=[]
 specifications=[('stable6_vs_'+b,('stable6',s,f),(b,s,f)) for b in ('legacy4','rule','resource') for s in ('periodic','lease') for f in ('fixed16','scaled')]
 specifications+=[('lease_vs_periodic_'+f,(m,'lease',f),(m,'periodic',f)) for m in ('stable6','legacy4','rule','resource') for f in ('fixed16','scaled')]
 specifications+=[('scaled_vs_fixed16_'+s,(m,s,'scaled'),(m,s,'fixed16')) for m in ('stable6','legacy4','rule','resource') for s in ('periodic','lease')]
 for scene in ('multi_failure','overload'):
  for name,target,baseline in specifications:
   pairs=[]
   for topology in ('base','jitter_b'):
    k=(topology,scene,*target,996201);b=(topology,scene,*baseline,996201)
    if k not in by or b not in by:continue
    x,y=by[k],by[b]
    assert x['hashes']['arrivals']==y['hashes']['arrivals'] and x['hashes']['positions']==y['hashes']['positions']
    pairs.append({'topology':topology,'timely_delta':x['worst_party_timely']-y['worst_party_timely'],'control_reduction':(byte_cost(y)-byte_cost(x))/byte_cost(y)})
   if pairs:contrasts.append(dict(scene=scene,name=name,target=target,baseline=baseline,pairs=pairs,mean_timely_delta=sum(x['timely_delta'] for x in pairs)/len(pairs),mean_control_reduction=sum(x['control_reduction'] for x in pairs)/len(pairs)))
 gates=[]
 if complete:
  for scene in ('multi_failure','overload'):
   def lookup(name,target):return next(c for c in contrasts if c['scene']==scene and c['name']==name and tuple(c['target'])==target)
   rule=lookup('stable6_vs_rule',('stable6','lease','fixed16'));resource=lookup('stable6_vs_resource',('stable6','lease','fixed16'));legacy=lookup('stable6_vs_legacy4',('stable6','lease','fixed16'));report=lookup('lease_vs_periodic_fixed16',('stable6','lease','fixed16'))
   checks={'rule_service':rule['mean_timely_delta']>=0,'resource_service':resource['mean_timely_delta']>=0,'legacy_service':legacy['mean_timely_delta']>=-.01,'report_service':report['mean_timely_delta']>=-.01,'report_control':report['mean_control_reduction']>=.05,'per_topology_robustness':all(p['timely_delta']>=-.03 for c in (rule,resource,legacy,report) for p in c['pairs'])}
   gates.append(dict(scene=scene,checks=checks,passed=all(checks.values())))
 out=ROOT/'analysis';out.mkdir(exist_ok=True)
 summary=dict(stage='development',formal_validation=False,registered_cases=len(reg['configs']),completed_cases=len(rows),complete=complete,comparisons=contrasts,development_gates=gates,formal_matrix_admitted=complete and all(x['passed'] for x in gates),feedback_valid=sum(f['reward'] is not None for r in rows for f in r['feedbacks']),feedback_total=sum(len(r['feedbacks']) for r in rows),audit_jobs=sum(r['audit']['mac_jobs'] for r in rows),LLM_runtime_calls=0)
 (out/'factorial_analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
 with (out/'factorial_run_metrics.csv').open('w',newline='') as handle:
  writer=csv.DictWriter(handle,fieldnames=['configuration_key','model','schedule','freshness','topology','scenario','seed','worst_timely','control_DATA_bytes','feedback_valid','feedback_total','evidence_directory']);writer.writeheader()
  for r in rows:writer.writerow({**{k:r[k] for k in ['configuration_key','model','schedule','freshness','topology','scenario','seed','evidence_directory']},'worst_timely':r['worst_party_timely'],'control_DATA_bytes':byte_cost(r),'feedback_valid':sum(f['reward'] is not None for f in r['feedbacks']),'feedback_total':len(r['feedbacks'])})
 print(json.dumps({k:v for k,v in summary.items() if k!='comparisons'},indent=2))

if __name__=='__main__':main()
