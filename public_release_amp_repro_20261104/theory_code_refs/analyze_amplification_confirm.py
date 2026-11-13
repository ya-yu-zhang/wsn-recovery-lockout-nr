"""Pre-registered endpoint + threshold evaluation for the amplification confirm stage.
Frozen together with results/amplification_confirm_registration.json."""
import json,math,collections,sys
from pathlib import Path
from analyze_amplification import load
ROOT=Path(__file__).resolve().parent;R=ROOT/'results'
COMPETING=('wait_extend','thresh_relax_scoped');MIN_GAIN_PP=1.0
def opened(arm,joint):
    """Gate re-opened with explained same-direction effect (pre-registered)."""
    return bool(arm['authorized']>=1 and arm.get('installs_after_exit',0)>=1 and 100*(arm['worst_source_service']-joint['worst_source_service'])>=MIN_GAIN_PP)
def fisher_one_sided(a,b,c,d):
    # P(X>=a) for 2x2 [[a,b],[c,d]] hypergeometric, rows=strata, col0=lockout
    n=a+b+c+d;r1=a+b;c1=a+c
    def p(x):return math.comb(c1,x)*math.comb(n-c1,r1-x)/math.comb(n,r1)
    return sum(p(x) for x in range(a,min(r1,c1)+1))
def wilson(k,n,z=1.96):
    if n==0:return(None,None)
    ph=k/n;den=1+z*z/n;cen=(ph+z*z/(2*n))/den;h=z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/den;return(max(0,cen-h),min(1,cen+h))
def main(stage='confirm'):
    rows=load(stage);cells=collections.defaultdict(dict)
    for r in rows:
        c=r['configuration'];cells[(c['topology'],c['seed'],c.get('stratum'))][c['arm']]=r
    table=[];sham_ok=True
    for (topo,seed,stratum),arms in sorted(cells.items()):
        j=arms['joint']
        row=dict(topology=topo,seed=seed,stratum=stratum,joint_service=j['worst_source_service'],joint_control=j['control_DATA_bytes'],joint_lockout_to_stop=j['lockout_to_stop'],joint_unconfirmed_exit=bool(j['exits']),
                 joint_first_exit_s=j['exits'][0][0] if j['exits'] else None,joint_blocked_checks=j['blocked_unconfirmed'],audits=sorted({a['audit_status'] for a in arms.values()}),arms={})
        for name,a in arms.items():
            row['arms'][name]=dict(service=a['worst_source_service'],control=a['control_DATA_bytes'],delta_service_pp=100*(a['worst_source_service']-j['worst_source_service']),
                delta_control_pct=100*(a['control_DATA_bytes']/j['control_DATA_bytes']-1),authorized_after_exit=a['authorized'],first_authorized_s=a['first_authorized_s'],installs_after_exit=a.get('installs_after_exit',0),
                lockout_to_stop=a['lockout_to_stop'],first_exit_s=a['exits'][0][0] if a['exits'] else None,opened=opened(a,j) if name!='joint' else None)
        s=arms.get('sham_release')
        if s is None or s['worst_source_service']!=j['worst_source_service'] or s['control_DATA_bytes']!=j['control_DATA_bytes']:sham_ok=False;row['sham_mismatch']=True
        table.append(row)
    lock=[r for r in table if r['joint_lockout_to_stop']]
    S1=len(lock)>=3 and len({r['topology'] for r in lock})>=2
    pe_ok=[r for r in lock if r['arms']['post_exit']['opened'] and r['arms']['post_exit']['first_exit_s']==r['joint_first_exit_s']]
    S2=len(pe_ok)>=2
    comp={k:[r['topology']+'/'+str(r['seed']) for r in pe_ok if r['arms'][k]['opened']] for k in COMPETING+('sham_release','fs_relax_scoped','fs_relax_global','thresh_relax_global')}
    S3=bool(pe_ok) and sham_ok and any(len(comp[k])==0 for k in COMPETING)
    strata=collections.Counter((r['stratum'],r['joint_lockout_to_stop']) for r in table)
    a=strata[('weak_control_hop',True)];b=strata[('weak_control_hop',False)];c=strata[('contrast',True)];d=strata[('contrast',False)]
    nonlock=[r for r in table if not r['joint_lockout_to_stop']]
    side={k:dict(changed=sum(1 for r in nonlock if abs(r['arms'][k]['delta_service_pp'])>1e-9 or r['arms'][k]['control']!=r['joint_control']),up=sum(1 for r in nonlock if r['arms'][k]['delta_service_pp']>1e-9),down=sum(1 for r in nonlock if r['arms'][k]['delta_service_pp']<-1e-9),
              mean_delta_service_pp=sum(r['arms'][k]['delta_service_pp'] for r in nonlock)/max(1,len(nonlock)),mean_delta_control_pct=sum(r['arms'][k]['delta_control_pct'] for r in nonlock)/max(1,len(nonlock))) for k in table[0]['arms'] if k!='joint'} if table else {}
    summary=dict(stage=stage,cells=len(table),runs=len(rows),all_audits_passed=all(r['audits']==['passed'] for r in table),sham_identical_to_joint_all_cells=sham_ok,
        lockout_cells=[dict(topology=r['topology'],seed=r['seed'],stratum=r['stratum'],first_exit_s=r['joint_first_exit_s'],blocked=r['joint_blocked_checks'],**{k:dict(d=round(v['delta_service_pp'],3),dc=round(v['delta_control_pct'],3),opened=v['opened'],auth=v['first_authorized_s']) for k,v in r['arms'].items() if k!='joint'}) for r in lock],
        unconfirmed_exit_cells=sum(r['joint_unconfirmed_exit'] for r in table),
        incidence=dict(overall=[len(lock),len(table)],overall_wilson95=wilson(len(lock),len(table)),weak_control_hop=[a,a+b],contrast=[c,c+d],fisher_one_sided_p=fisher_one_sided(a,b,c,d) if table else None),
        thresholds=dict(S1=dict(met=S1,lockout_cells=len(lock),layouts=sorted({r['topology'] for r in lock})),S2=dict(met=S2,post_exit_opened=[r['topology']+'/'+str(r['seed']) for r in pe_ok]),
                        S3=dict(met=S3,replicating_cells_by_arm=comp),A_tier=S1 and S2 and S3),
        nonlockout_side_effects=side,table=table)
    (R/f'amplification_{stage}_summary.json').write_text(json.dumps(summary,indent=1)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in('table','nonlockout_side_effects')},indent=1))
if __name__=='__main__':main(*(sys.argv[1:]))
