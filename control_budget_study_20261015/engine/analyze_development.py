"""All registered phase16 paired results, including protocol reaction costs."""
import csv,io,json,statistics as stats
from pathlib import Path
from run_closed_loop import ROOT
from run_development import configurations,source_hashes,identity,MODELS
from audit_closed_loop import audit_case,read
from cost_accounting import reconcile

def main():
    reg=json.loads((ROOT/'docs/development_registration.json').read_text());assert reg['source_sha256']==source_hashes() and reg['configs']==configurations()
    rows=json.loads((ROOT/'results/development_manifest.json').read_text());expected={(c['group'],c['method'],c['scenario'],c['topology'],c['seed']) for c in configurations()}
    assert len(rows)==len(expected) and {identity(r) for r in rows}==expected
    cases=[];audits=[]
    for r in rows:
        audit=audit_case(r,ROOT/'results/development');audits.append(audit)
        prefix=ROOT/'results/development'/r['id'];messages=[json.loads(x) for x in read(Path(str(prefix)+'.protocol.jsonl.gz')).decode().splitlines()]
        jobs=[[int(v) for v in row] for row in list(csv.reader(io.StringIO(read(Path(str(prefix)+'.jobs.csv.gz')).decode())))[1:]]
        cost=reconcile(messages,jobs,r);assert cost['generated_by_party']==r['native']['offered'] and cost['timely_by_party']==r['native']['timely']
        full=[d for d in r['decisions'] if d['selection_rule']=='linucb_score'];waits=r['feedback_waits'];fbs=r['feedbacks']
        assert len(fbs)==len(r['decisions']) and len({w['decision'] for w in waits})==len(waits)
        if r['model']=='frozen':assert r['bandit_updates']==[0]*4
        cases.append(dict(id=r['id'],study_group=r['study_group'],method=r['method'],model=r['model'],protocol=r['protocol'],scenario=r['scenario'],topology=r['topology'],seed=r['seed'],
            mean_timely=r['mean_timely'],worst_party_timely=r['worst_party_timely'],decisions=len(r['decisions']),total_fe=r['total_fe'],
            valid_feedback=sum(f['reward'] is not None for f in fbs),missing_feedback=sum(f['reward'] is None for f in fbs),feedback_valid_fraction=sum(f['reward'] is not None for f in fbs)/len(fbs) if fbs else None,
            updates_by_arm=r['bandit_updates'],full_ucb_choices_after_update=sum(sum(d['updates_before_selection'])>0 for d in full),
            wait_transactions=len(waits),recovered_after_wait=sum(f.get('recovered_after_wait',False) for f in fbs),extra_wait_seconds=sum(f.get('extra_wait_ns',0) for f in fbs)/1e9,
            observed_event_ticks_blocked=sum(w['observed_event_blocked'] for w in waits),
            control_data_bytes=cost['total_control_data_bytes'],report_data_bytes=cost['report_data_bytes'],initial_install_data_bytes=cost['initial_install_data_bytes'],retry_install_data_bytes=cost['retry_install_data_bytes'],global_ack_bytes=cost['global_ack_bytes'],source_queue_mean_ms=cost['classes']['source_application']['queue_mean_ms'],costs=cost))
        print('analysis audited',len(cases),'/',len(rows),flush=True)
    bykey={(c['method'],c['scenario'],c['seed']):c for c in cases};native={(r['method'],r['scenario'],r['seed']):r for r in rows};pairs=[]
    def compare(group,method,reference,scenario,seed):
        a=bykey[method,scenario,seed];b=bykey[reference,scenario,seed]
        assert all(native[method,scenario,seed]['hashes'][k]==native[reference,scenario,seed]['hashes'][k] for k in ('arrivals','positions'))
        return dict(group=group,method=method,reference=reference,scenario=scenario,topology='base',seed=seed,worst_timely_pp=100*(a['worst_party_timely']-b['worst_party_timely']),mean_timely_pp=100*(a['mean_timely']-b['mean_timely']),**{k:a[k]-b[k] for k in ('valid_feedback','missing_feedback','decisions','total_fe','control_data_bytes','report_data_bytes','extra_wait_seconds','observed_event_ticks_blocked','full_ucb_choices_after_update')})
    for scene in ('multi_failure','overload'):
        for seed in (983201,983202):
            for model in MODELS:pairs.append(compare('protocol','grace5_'+model,'baseline20_'+model,scene,seed))
            for protocol in ('baseline20','grace5'):
                for ref in ('random','intercept','frozen'):pairs.append(compare('learning',protocol+'_full',protocol+'_'+ref,scene,seed))
    summaries=[]
    for group,method,ref,scene in sorted({(p['group'],p['method'],p['reference'],p['scenario']) for p in pairs}):
        subset=[p for p in pairs if (p['group'],p['method'],p['reference'],p['scenario'])==(group,method,ref,scene)]
        summaries.append(dict(group=group,method=method,reference=ref,scenario=scene,paired_streams=len(subset),positive=sum(p['worst_timely_pp']>1e-12 for p in subset),negative=sum(p['worst_timely_pp']<-1e-12 for p in subset),**{'mean_'+k:stats.mean(p[k] for p in subset) for k in ('worst_timely_pp','mean_timely_pp','valid_feedback','missing_feedback','decisions','total_fe','control_data_bytes','report_data_bytes','extra_wait_seconds','observed_event_ticks_blocked')}))
    aggregates=[]
    for protocol in ('baseline20','grace5'):
        sub=[c for c in cases if c['protocol']==protocol]
        totals={k:sum(c[k] for c in sub) for k in ('decisions','valid_feedback','missing_feedback','wait_transactions','recovered_after_wait','extra_wait_seconds','observed_event_ticks_blocked','full_ucb_choices_after_update')}
        aggregates.append(dict(protocol=protocol,native_runs=len(sub),valid_feedback_fraction=totals['valid_feedback']/totals['decisions'],**totals))
    out=dict(status='passed',registered_native_cases=len(rows),native_jobs=sum(a['mac_jobs'] for a in audits),cases=cases,paired_differences=pairs,summaries=summaries,protocol_aggregates=aggregates,
        all_native_records_and_registered_source_sha_checked=True,all_cached_count_provenance_checked=True,formal_matrix=False,learning_benefit_established=False,
        limitation='One known10-node geometry, two new streams per scenario; repeated controller variants share offered streams. Descriptive only. Event ticks blocked are observed opportunities, not proven feasible lost actions. More feedback can delay recovery.',LLM_calls=0,original_phase2_optimizer_integrated=False)
    (ROOT/'results/development_analysis.json').write_text(json.dumps(out,indent=2));(ROOT/'results/development_audit.json').write_text(json.dumps(dict(status='passed',cases=audits),indent=2))
    print(json.dumps({k:out[k] for k in ('status','registered_native_cases','native_jobs','protocol_aggregates','summaries')},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
