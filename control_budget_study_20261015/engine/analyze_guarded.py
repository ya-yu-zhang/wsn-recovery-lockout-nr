"""Complete registered development analysis; no post-hoc primary selection."""
import collections, csv, json
from pathlib import Path
from run_guarded import MODELS, PROFILES, registration, identity

ROOT=Path(__file__).resolve().parent


def main():
 reg=registration('development');rows=json.loads((ROOT/'results/guarded_development_manifest.json').read_text())
 assert len(rows)==48 and {r['configuration_key']for r in rows}=={identity(c)for c in reg['configs']}
 by={(r['topology'],r['scenario'],r['model'],r['schedule']):r for r in rows}
 for scene in ('multi_failure','overload'):
  for topology in ('base','jitter_b'):
   cell=[r for r in rows if r['scenario']==scene and r['topology']==topology]
   assert len({(r['hashes']['arrivals'],r['hashes']['positions'])for r in cell})==1,'paired inputs differ'
 comparisons=[];gates=[]
 def compare(scene,model,schedule,other_model,other_schedule):
  pairs=[]
  for topology in ('base','jitter_b'):
   a=by[topology,scene,model,schedule];b=by[topology,scene,other_model,other_schedule]
   pairs.append(dict(topology=topology,service_delta=a['worst_party_timely']-b['worst_party_timely'],
                     control_reduction=1-a['native']['control_psdu_bytes']/b['native']['control_psdu_bytes']))
  result=dict(scene=scene,target=[model,schedule],baseline=[other_model,other_schedule],pairs=pairs,
              mean_service_delta=sum(p['service_delta']for p in pairs)/2,
              mean_control_reduction=sum(p['control_reduction']for p in pairs)/2)
  comparisons.append(result);return result
 for scene in ('multi_failure','overload'):
  for schedule in PROFILES:
   for other in ('intercept6','rule','resource'):compare(scene,'stable6',schedule,other,schedule)
  for model in MODELS:
   compare(scene,model,'guard15',model,'periodic');compare(scene,model,'guard15',model,'lease20')
  # Primary contrasts are specified before native execution in the registration.
  find=lambda target,baseline:next(c for c in comparisons if c['scene']==scene and c['target']==target and c['baseline']==baseline)
  report=find(['stable6','guard15'],['stable6','periodic'])
  rule=find(['stable6','guard15'],['rule','guard15'])
  resource=find(['stable6','guard15'],['resource','guard15'])
  context=find(['stable6','guard15'],['intercept6','guard15'])
  trained=sum(d['selection_rule']=='linucb_score' and sum(d['updates_before_selection'])>0
              for topology in ('base','jitter_b')for d in by[topology,scene,'stable6','guard15']['decisions'])
  g=reg['gates'];checks=dict(
   report_service=report['mean_service_delta']>=g['report_service_margin'],
   report_control=report['mean_control_reduction']>=g['report_control_reduction'],
   rule_service=rule['mean_service_delta']>=g['rule_service_margin'],
   resource_service=resource['mean_service_delta']>=g['resource_service_margin'],
   context_practical_gain=((context['mean_service_delta']>=g['context_service_gain']and
                            context['mean_control_reduction']>=-g['context_cost_increase_limit'])or
                           (context['mean_service_delta']>=g['context_alternative_service_margin']and
                            context['mean_control_reduction']>=g['context_alternative_control_reduction'])),
   per_topology_robustness=all(p['service_delta']>=g['worst_topology_service_margin']for c in (report,rule,resource,context)for p in c['pairs']))
  gates.append(dict(scene=scene,checks=checks,trained_ucb_choices=trained,passed=all(checks.values())))
 # Opportunity minimum is pooled across the four primary development cases.
 opportunity=sum(g['trained_ucb_choices']for g in gates)>=reg['gates']['primary_trained_ucb_choices_minimum']
 metrics=[]
 for row in rows:
  steps=json.loads((ROOT/row['evidence_directory']/(row['id']+'.controller.json')).read_text())['steps']
  metrics.append(dict(configuration_key=row['configuration_key'],topology=row['topology'],scene=row['scenario'],
                      model=row['model'],schedule=row['schedule'],worst_party_timely=row['worst_party_timely'],
                      control_data_bytes=row['native']['control_psdu_bytes'],ack_bytes=row['native']['ack_psdu_bytes'],
                      radio_joules=row['estimated_radio_joules'],mac_jobs=row['audit']['mac_jobs'],
                      decisions=len(row['decisions']),valid_feedback=sum(f['reward']is not None for f in row['feedbacks']),
                      trained_ucb_choices=sum(d['selection_rule']=='linucb_score'and sum(d['updates_before_selection'])>0 for d in row['decisions']),
                      service_known_snapshots=sum(s['event']['settled_service']['known']for s in steps),
                      snapshots=len(steps)))
 with (ROOT/'analysis/guarded_run_metrics.csv').open('w',newline='')as file:
  writer=csv.DictWriter(file,fieldnames=list(metrics[0]));writer.writeheader();writer.writerows(metrics)
 output=dict(stage='development',formal_validation=False,registered_cases=48,completed_cases=48,complete=True,
             comparisons=comparisons,development_gates=gates,learning_opportunity_gate=opportunity,
             formal_matrix_admitted=all(g['passed']for g in gates)and opportunity,
             audit_jobs=sum(r['audit']['mac_jobs']for r in rows),LLM_runtime_calls=0,
             caveat='Even a development pass only permits preregistration of untouched validation; it is not submission clearance.')
 (ROOT/'analysis/guarded_analysis.json').write_text(json.dumps(output,indent=2)+'\n')
 print(json.dumps({k:v for k,v in output.items()if k!='comparisons'},indent=2))


if __name__=='__main__':main()
