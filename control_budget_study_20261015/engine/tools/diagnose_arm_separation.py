"""Offline proxy menu separation; never supplies counterfactual rewards online."""
import collections,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from wsn.controller import Controller
from wsn.operator_search import search_operator
from audit_closed_loop import clean
from run_observable import registration,atomic

def canonical(paths):return tuple(tuple(p)for p in paths)if paths is not None else None
def main():
    reg=registration('development');runs=json.loads((ROOT/'results/observable_development_manifest.json').read_text());assert len(runs)==len(reg['configs'])==112
    records=[];checks=0
    for r in runs:
        if(r['model'],r['profile'])!=('stable6','obs_full'):continue
        c=Controller(r['policy'],r['report_profile'],points=r['points'],action_stop_ns=r['action_stop_ns'],selection_seed=r['selection_seed'])
        folder=ROOT/r['evidence_directory'];steps=json.loads((folder/(r['id']+'.controller.json')).read_text())['steps']
        for step in steps:
            reply,replay=c.step(step['observation']);assert clean(replay)==clean(step)
            d=step['decision']
            if d is None:continue
            o=step['observation'];t=o['time_ns'];fresh={p['node']:p for p in o['reports']if 0<=t-p['stamp_ns']<=c.fresh_limit(p['node'],p)};active=set(fresh)|{9}
            # All four revised operators share this geometry-filtered pool.
            # Reuse the exact selected pool and legally visible state; all
            # additional objective work is offline and explicitly charged.
            pool=[canonical(x['paths'])for x in d['evaluated']]
            menus={};fees={}
            for action in range(4):
                path,evaluated,info=search_operator(action,pool,fresh,active,c.points,c.current,d['event']['settled_service'])
                menus[str(action)]=canonical(path);fees[str(action)]=len(evaluated)
            selected=canonical(d['paths']or d.get('admission',{}).get('proposed_paths'));assert menus[str(d['action'])]==selected
            checks+=1;unique=len(set(menus.values()));scores=d.get('ucb_scores')
            records.append(dict(configuration_key=r['configuration_key'],scene=r['scenario'],decision=d['decision'],time_ns=t,selected_action=d['action'],
                                proxy_route_menu_by_action=menus,distinct_route_proposals=unique,offline_objective_evaluations=sum(fees.values()),
                                online_selected_objective_evaluations=d['fe'],known_service=d['event']['settled_service']['known'],
                                updates_before_selection=d['updates_before_selection'],ucb_scores=scores,
                                unselected_end_to_end_rewards_evaluated=0,offline_only=True,used_for_online_selection=False))
    assert checks>0
    counts=collections.Counter(x['distinct_route_proposals']for x in records)
    summary=dict(complete=True,primary_decisions=checks,distinct_menu_count_histogram=dict(counts),
                 identical_four_arm_menu_fraction=sum(x['distinct_route_proposals']==1 for x in records)/checks,
                 offline_extra_objective_evaluations=sum(x['offline_objective_evaluations']-x['online_selected_objective_evaluations']for x in records),
                 primary_selected_actions=dict(collections.Counter(x['selected_action']for x in records)),
                 unselected_end_to_end_rewards_evaluated=0,online_training_changed=False,LLM_runtime_calls=0,
                 scope='offline proxy-route distinctness at observed primary decision states; not actual alternative rewards, regrets, or arm equivalence under future states')
    atomic(ROOT/'analysis/observable_arm_separation.json',dict(summary=summary,decision_records=records));print(json.dumps(summary))
if __name__=='__main__':main()
