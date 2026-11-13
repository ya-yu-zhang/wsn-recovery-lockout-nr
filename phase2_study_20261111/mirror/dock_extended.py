"""Exploratory (E) Mode-C rescoring over every frozen result set whose arm/model the mirror implements (Addendum 1).
Unsupported arms (fs_relax_*, thresh_relax_global) and the 'legacy' controller are counted but not scored. Read-only."""
import sys, os, json, glob, collections, concurrent.futures
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import dock
SUP_ARMS = {'joint', 'post_exit', 'sham_release', 'wait_extend', 'thresh_relax_scoped'}; SUP_MODELS = {'horizon', 'cohort', 'closing', 'full_v2'}
SETS = ['amplification2_confirm', 'amplification2_manip_check', 'amplification_check', 'amplification_confirm', 'amplification_pilot',
        'amplification_pilot2', 'amplification_pilot3', 'contract_ablation', 'contract_generalization']
LATE = os.environ.get('PH2_EXITS_INCL_LATE') == '1'
if LATE:  # variant: count every wait exit, including ones later rescued by a late confirmation (frozen post_exit() convention)
    dock.M.GateFSM.exits = lambda self: sorted(i.exit_ns for i in self.installs if i.exit_ns is not None)
def safe(f):
    try: return dock.mode_c(f)
    except Exception as e: return dict(folder=os.path.basename(f), error=repr(e)[:300])
def main():
    jobs = []; skipped = collections.Counter()
    for s in SETS:
        for f in sorted(glob.glob(f'{dock.R}/{s}/*/case.json')):
            cfg = json.load(open(f))['configuration']
            ok = (cfg.get('arm') in SUP_ARMS) if 'arm' in cfg else (cfg.get('contract') in ('joint', 'post_exit') and cfg.get('model') in SUP_MODELS)
            if ok: jobs.append((s, os.path.dirname(f)))
            else: skipped[(s, cfg.get('arm') or f"{cfg.get('contract')}/{cfg.get('model')}")] += 1
    with concurrent.futures.ProcessPoolExecutor(6) as ex: res = list(ex.map(safe, [f for _, f in jobs]))
    by = collections.defaultdict(list)
    for (s, _), r in zip(jobs, res): r['set'] = s; by[s].append(r)
    summ = {}
    for s, rs in by.items():
        ok = [r for r in rs if 'error' not in r]
        summ[s] = dict(n=len(rs), errors=len(rs) - len(ok), C1=sum(r['C1'] for r in ok), C2=sum(r['C2'] for r in ok),
                       phi_agree=sum(r['phi_agree'] for r in ok), phi_eval=sum(r['phi_eval'] for r in ok), reason_agree=sum(r['reason_agree'] for r in ok), ticks=sum(r['ticks'] for r in ok),
                       per_arm={a: dict(n=len(v), C1=sum(x['C1'] for x in v), C2=sum(x['C2'] for x in v)) for a in sorted({r['arm'] for r in ok}) for v in [[x for x in ok if x['arm'] == a]]})
    out = dict(summary=summ, skipped={f'{k[0]}:{k[1]}': v for k, v in skipped.items()},
               mismatches=[dict(set=r['set'], folder=r['folder'], arm=r.get('arm'), C1=r.get('C1'), C2=r.get('C2'), error=r.get('error'), reason_mismatch=r.get('reason_mismatch'), phi_mismatch=r.get('phi_mismatch'), ns3=r.get('ns3'), mirror=r.get('mirror'))
                           for rs in by.values() for r in rs if 'error' in r or not (r['C1'] and r['C2'] and r['phi_agree'] == r['phi_eval'] and r['reason_agree'] == r['ticks'])])
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
    print(json.dumps(summ, indent=1)); print('skipped', out['skipped']); print('n_mismatch', len(out['mismatches']))
if __name__ == '__main__': main()
