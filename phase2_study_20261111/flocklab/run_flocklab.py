"""Registered FlockLab replay runs. Usage: run_flocklab.py <probe|full|neutral> [workers]"""
import sys, json, concurrent.futures, traceback
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE.parent / 'common'))
import ns3run
SC = {'N': dict(scenario='multi_failure', faults=[[145, 3], [225, 6]]),
      'M1': dict(scenario='multi_failure', faults=[[145, 3], [225, 6]], drop_install_start_sec=0.0, drop_install_end_sec=200.0, drop_install_mask=3)}
SEEDS = (2026111301, 2026111302, 2026111303, 2026111304)
def cases(which):
    sel = json.load(open(HERE / 'traces/subgraphs.json')); out = []
    if which == 'neutral':
        for L in (2026110410, 2026110411):
            out.append(dict(stage='neutral', topology=f'budget_10_{L}', seed=2026110611, arm='joint', recipe='M1_drop_both_0_200_dn36', trace_binary_neutral=True, **SC['M1']))
        return out
    for tag in (('A',) if which == 'probe' else ('A', 'B')):
        sgs = sel[tag]['subgraphs'][:2] if which == 'probe' else sel[tag]['subgraphs']
        for sg in sgs:
            for mode in ((2,) if which == 'probe' or tag == 'B' else (2, 1)):
                for seed in (SEEDS[:1] if which == 'probe' else SEEDS):
                    for sc in ('N', 'M1'):
                        for arm in ('joint', 'post_exit'):
                            out.append(dict(stage=which, day=tag, subgraph=sg['id'], trace_file=str(HERE / 'traces' / sg['file']), trace_sha256=sg['sha256'],
                                            trace_mode=mode, topology=f'flock_{sg["id"]}', seed=seed, arm=arm, scenario_tag=sc, **SC[sc]))
    return out
def main():
    which = sys.argv[1]; W = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    cs = cases(which); print('CASES', which, len(cs), flush=True); rows = []; fails = []
    with concurrent.futures.ProcessPoolExecutor(W) as pool:
        fut = {pool.submit(ns3run.execute, c, 'flocklab_' + which): c for c in cs}
        for f in concurrent.futures.as_completed(fut):
            try: r = f.result(); rows.append(ns3run.compact(r)); print('DONE', len(rows), r['configuration'].get('subgraph'), r['configuration'].get('scenario_tag'), r['configuration']['arm'], r['audit']['status'], flush=True)
            except BaseException: fails.append(dict(configuration=fut[f], traceback=traceback.format_exc())); print('FAILED', fut[f], flush=True)
    out = HERE / f'results_{which}'; out.mkdir(exist_ok=True)
    json.dump(dict(n_cases=len(cs), n_done=len(rows), failures=fails, rows=sorted(rows, key=lambda r: json.dumps(r['configuration'], sort_keys=True))), open(out / 'runs.json', 'w'), indent=1)
if __name__ == '__main__': main()
