"""Rebuild local version protection and queue admission from native events."""
import collections,gzip,json
def audit_messages(messages,mode,retry_enabled):
    queues=collections.defaultdict(list);seen={};generated={};classified=[]
    schedules={(x['node'],x['parent_sequence'],x['time_ns'])for x in messages if x['kind']=='report_retry_scheduled'}
    budgets={(x['node'],x['parent_sequence'],x['time_ns']):x for x in messages if x['kind']=='report_budget_admission'}
    observed=0
    for x in messages:
        kind=x['kind'];node=x.get('node');t=x['time_ns']
        if kind=='report_generated':
            r=x['report'];generated[r['node'],r['stamp_ns']]=r
        elif kind=='report_local_observation':
            key=(node,x['source']);v=x['version'];stamp=x['stamp_ns'];r=generated[x['source'],stamp]
            assert stamp<=t and r['version']==v and x['source']<2
            if key not in seen or v>seen[key][0]:seen[key]=(v,[])
            version,stamps=seen[key]
            if v==version and stamp not in stamps and len(stamps)<2:stamps.append(stamp)
            critical=v==version and stamp in stamps
            assert critical==x['critical'];observed+=1
        elif kind=='queue_arrival':
            if x['accepted']:queues[node].append((x['flow'],x['sequence']))
        elif kind=='queue_choice':assert queues[node].pop(x['selected_index'])==(x['flow'],x['sequence'])
        elif kind=='queue_purge':assert queues[node].pop(0)==(x['flow'],x['sequence'])
        elif kind=='report_retry_classified':
            version,stamps=seen[(node,x['source'])]
            critical=version==x['version'] and x['stamp_ns'] in stamps
            waiting=len(queues[node]);allowed=mode=='always' or waiting<=4 or (mode=='critical_queue' and critical)
            assert retry_enabled and x['mode']==mode and x['waiting_depth']==waiting
            assert x['critical']==critical and x['admitted']==allowed
            key=(node,x['parent_sequence'],t)
            if not allowed:assert key not in budgets and key not in schedules
            else:assert key in budgets and (key in schedules)==budgets[key]['admitted']
            classified.append(x)
    return dict(status='passed',local_observation_count=observed,classified_count=len(classified),
        critical_congested_policy_admitted=sum(x['admitted']and x['critical']and x['waiting_depth']>4 for x in classified),
        critical_congested_retries_scheduled=sum(x['critical']and x['waiting_depth']>4 and (x['node'],x['parent_sequence'],x['time_ns'])in schedules for x in classified),
        congested_suppressed=sum(not x['admitted'] for x in classified),
        routine_congested_suppressed=sum(not x['admitted']and not x['critical'] for x in classified),
        critical_congested_suppressed=sum(not x['admitted']and x['critical'] for x in classified),
        local_queue_and_observed_versions_independently_rebuilt=True,
        critical_scope='first two locally observed distinct stamps per source version; proxy, not sink acknowledgement')
def audit_selective_retry(row,folder):
    messages=[json.loads(s)for s in gzip.open(str(folder/row['id'])+'.protocol.jsonl.gz','rt')]
    return audit_messages(messages,row['report_retry_mode'],row['report_retry'])
