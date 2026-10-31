"""All registered mechanism contrasts, full costs and descriptive gates."""
import collections,csv,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from run_mechanisms import registration,MODELS
from run_aligned import atomic
def gain(c):
    return (c['mean_service_delta']>=.005 and c['mean_DATA_reduction']>=-.05)or(c['mean_service_delta']>=-.005 and c['mean_DATA_reduction']>=.05)
def contrast(rows,target,baseline,scene):
    aa={(r['topology'],r['seed']):r for r in rows if r['model']==target and r['scenario']==scene}
    bb={(r['topology'],r['seed']):r for r in rows if r['model']==baseline and r['scenario']==scene};pairs=[]
    assert len(aa)==len(bb)==4
    for k,a in sorted(aa.items()):
        b=bb[k];assert a['hashes']['arrivals']==b['hashes']['arrivals']and a['hashes']['positions']==b['hashes']['positions']
        pairs.append(dict(topology=k[0],seed=k[1],service_delta=a['worst_party_timely']-b['worst_party_timely'],
            DATA_reduction=1-a['native']['control_psdu_bytes']/b['native']['control_psdu_bytes'],
            total_ACK_delta=a['native']['ack_psdu_bytes']-b['native']['ack_psdu_bytes'],
            radio_energy_delta=a['estimated_radio_joules']-b['estimated_radio_joules']))
    return dict(target=target,baseline=baseline,scene=scene,pairs=pairs,
        mean_service_delta=float(np.mean([p['service_delta']for p in pairs])),mean_DATA_reduction=float(np.mean([p['DATA_reduction']for p in pairs])),
        mean_radio_energy_delta=float(np.mean([p['radio_energy_delta']for p in pairs])))
def main():
    reg=registration('development');rows=json.loads((ROOT/'results/mechanism_development_manifest.json').read_text());assert len(rows)==len(reg['configs'])==64
    assert all(r['audit']['status']=='passed'for r in rows)
    contrasts=[contrast(rows,'resource10_on',m,s)for m in MODELS if m!='resource10_on'for s in ('multi_failure','overload')]
    factorial=[];gates=[]
    for s in ('multi_failure','overload'):
        off=contrast(rows,'resource10_off','resource15_off',s);on=contrast(rows,'resource10_on','resource15_on',s)
        retry10=contrast(rows,'resource10_on','resource10_off',s);retry15=contrast(rows,'resource15_on','resource15_off',s)
        factorial.append(dict(scene=s,deadline_effect_retry_on=on,deadline_effect_retry_off=off,
            retry_effect_deadline10=retry10,retry_effect_deadline15=retry15,
            service_interaction=on['mean_service_delta']-off['mean_service_delta']))
        checks=dict(isolated_deadline_gain=gain(on),report_retry_value=gain(retry10))
        gates.append(dict(scene=s,checks=checks,passed=all(checks.values())))
    metrics=[]
    for r in rows:
        a=r['audit'];fb=r['feedbacks'];exits=a['observable_control']['unconfirmed_installation_exits']
        metrics.append(dict(key=r['configuration_key'],model=r['model'],scene=r['scenario'],topology=r['topology'],seed=r['seed'],
            worst_timely=r['worst_party_timely'],mean_timely=r['mean_timely'],DATA=r['native']['control_psdu_bytes'],total_ACK=r['native']['ack_psdu_bytes'],radio_joules=r['estimated_radio_joules'],
            decisions=len(r['decisions']),FE=r['total_fe'],qualified_feedback=sum(f['reward']is not None for f in fb),censored_feedback=sum(f['reward']is None for f in fb),
            install_exits=exits,late_confirmations=a['observable_control']['late_installation_reconciliations'],
            report_retry_schedules=a['report_recovery']['report_retry_schedules'],retry_DATA=a['report_recovery']['extra_report_data_bytes'],
            ordinary_relay_emitted=a['observable_control']['relay_reports_emitted']))
    result=dict(complete=True,cases=64,functional_cases=8,primary='resource10_on',comparisons=contrasts,factorial=factorial,gates=gates,
        total_decisions=sum(m['decisions']for m in metrics),learning_updates=0,LLM_runtime_calls=0,exposures=0,
        formal_matrix_admitted=False,ready_to_submit=False,prior_learning_claim_supported=False,scope=reg['independent_input_scope'],
        limitations=reg['limitations'],statistical_claim='descriptive means and per-cell effects; no p-values or superiority guarantee')
    atomic(ROOT/'analysis/mechanism_analysis.json',result)
    with (ROOT/'analysis/mechanism_metrics.csv').open('w',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
    print(json.dumps({k:v for k,v in result.items()if k not in ('comparisons','factorial','limitations')}))
if __name__=='__main__':main()
