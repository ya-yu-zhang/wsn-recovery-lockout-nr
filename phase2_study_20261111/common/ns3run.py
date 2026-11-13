"""Phase-2 ns-3 case executor (FlockLab replay and DOE). Wraps the frozen engine read-only:
same controller (AmplifiedHorizon), same CLI settings as run_amplification2.execute, raw output
outside the frozen tree (/workspace/scratch_phase2). Additions, all declared in the phase-2 prereg:
  * install wait override (DOE factor E) via DOEHorizon (sets install_exit_ns after construction);
  * FlockLab geometry 'flock_*' = 4x3 grid at 6 m;
  * optional trace binary through flocklab/trace_wrapper.sh with PH2_TRACE_* environment variables."""
import sys, os, json, hashlib, traceback
from pathlib import Path
ENGROOT = Path('/workspace/wsn_ablation/repo/control_budget_study_20261015')
sys.path.insert(0, str(ENGROOT)); sys.path.insert(0, str(ENGROOT / 'engine'))
import fast_native_run as F
from run_mechanisms import policy
from amplification_arms import AmplifiedHorizon
from audit_case import audit
from analyze_contract_ablation import post_exit
NATIVE = ENGROOT / 'engine/ns3/wsn-closed-loop'
HERE = Path(__file__).resolve().parent.parent
TRACE_WRAPPER = HERE / 'flocklab/trace_wrapper.sh'
SCRATCH = Path('/workspace/scratch_phase2')
_geometry = F.geometry
def geometry(name):
    if name.startswith('flock_'):
        return {i: (6.0 * (i % 4), 6.0 * (i // 4)) for i in range(10)}
    return _geometry(name)
F.geometry = geometry
class DOEHorizon(AmplifiedHorizon):
    def __init__(self, *a, wait_s=None, **k):
        super().__init__(*a, **k)
        if wait_s is not None: self.install_exit_ns = int(wait_s) * 1_000_000_000
def key_of(c): return hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()[:20]
def execute(c, subdir):
    key = key_of(c); folder = SCRATCH / subdir / key; folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'case.json').exists(): return json.loads((folder / 'case.json').read_text())
    binary = NATIVE
    if c.get('trace_mode'):
        binary = TRACE_WRAPPER
        os.environ['PH2_TRACE_FILE'] = c['trace_file']; os.environ['PH2_TRACE_MODE'] = str(c['trace_mode']); os.environ['PH2_TRACE_SEED'] = str(c['seed'])
    elif c.get('trace_binary_neutral'):
        binary = TRACE_WRAPPER; os.environ['PH2_TRACE_FILE'] = ''; os.environ['PH2_TRACE_MODE'] = '0'; os.environ['PH2_TRACE_SEED'] = '0'
    try:
        kw = {'pacing': True, 'evidence_gate': True, 'arm': c['arm']}
        if c.get('wait_s') is not None: kw['wait_s'] = c['wait_s']
        row = F.one(binary, c['scenario'], policy('resource10_on'), c['seed'], folder=folder, profile='local15_event', topology=c['topology'], extended=True,
                    source_only=True, generation_stop=330, faults=c['faults'], queue_discipline='fifo', epoch_certificate=True, report_retry=True,
                    report_budget=True, report_retry_mode='always', controller_factory=DOEHorizon, controller_kwargs=kw,
                    unified_budget=True, protect_evidence=True, version_pacing=True, report_phase_seed=c['seed'],
                    drop_install_start_sec=c.get('drop_install_start_sec', -1.0), drop_install_end_sec=c.get('drop_install_end_sec', -1.0),
                    drop_install_mask=c.get('drop_install_mask', 0))
        row.update(configuration=c, configuration_key=key, evidence_directory=str(folder))
        row['audit'] = audit(row, folder)
        row['gate'] = post_exit(folder, row)
        row['fs_after_last_exit'] = fs_after_last_exit(folder, row)
        tl = list(folder.glob('*.tracelinks.csv'))
        if tl: row['tracelinks_file'] = str(tl[0])
        tmp = folder / 'case.staging'; tmp.write_text(json.dumps(row, indent=1) + '\n'); tmp.replace(folder / 'case.json')
        return row
    except BaseException:
        (folder / 'FAILED_ATTEMPT.txt').write_text(traceback.format_exc()); raise
def fs_after_last_exit(folder, case):
    """True if any step at/after the last unconfirmed exit (before action stop) logs an eligible fresh F_s source report."""
    c = json.loads(next(folder.glob('*.controller.json')).read_text())
    exits = sorted({h['time_ns'] for i in case['installations'] for h in i['history'] if h.get('outcome') == 'abandoned_unconfirmed' and h.get('closed') and not h.get('late_confirmation')})
    if not exits: return None
    for s in c['steps']:
        t = s['observation']['time_ns']
        if exits[-1] <= t < case['action_stop_ns']:
            ev = (s.get('event') or {}).get('safety_evidence') or (s.get('event') or {})
            fr = ev.get('source_failure_reports') or {}
            if any(isinstance(d, dict) and d.get('eligible') for d in fr.values()): return True
    return False
def compact(r):
    g = r['gate']; a = r['audit']
    return dict(key=r['configuration_key'], configuration=r['configuration'], audit=a['status'], worst_source_service=a['worst_source_service'],
                unconfirmed_exits=g['unconfirmed_exits'], E1=g['lockout_to_stop'], installs_after_exit=g.get('installs_after_exit', 0),
                gate_closed=bool(g['unconfirmed_exits']) and g.get('installs_after_exit', 0) == 0, first_authorized_s=g['first_authorized_s'],
                fs_after_last_exit=r['fs_after_last_exit'], tracelinks_file=r.get('tracelinks_file'), id=r['id'], folder=r['evidence_directory'])
