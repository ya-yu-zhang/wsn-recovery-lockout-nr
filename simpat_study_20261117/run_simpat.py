"""Registered closed-loop stages of the SIMPAT simulation study (see PROTOCOL.md).

Usage: python run_simpat.py --stage {smoke,contract,scale,sensitivity} [--shard i --shards n]
       python run_simpat.py --list STAGE      (print the frozen configuration count)
"""
from pathlib import Path
import argparse, gzip, hashlib, json, os, shutil, sys, time, traceback

STUDY = Path(__file__).resolve().parent
BASE = STUDY.parent / 'control_budget_study_20261015'
for p in (BASE, BASE / 'engine'):
    sys.path.insert(0, str(p))

from contract_controllers import FACTORIES  # noqa: E402
from lockout import describe  # noqa: E402

ORIGINAL_LAYOUT = 2026101501
ORIGINAL_SEEDS = (2026101511, 2026101512)
NEW_LAYOUTS = tuple(range(2026111701, 2026111711))      # ten fresh layout seeds
NEW_SEEDS = (2026111711, 2026111712)                    # two fresh input seeds
SCENARIOS = ('multi_failure', 'overload')


def cfg(n, layout, scenario, seed, model, contract='joint', install_exit_s=10, control_rate=305, stage=''):
    return dict(topology=f'budget_{n}_{layout}', scenario=scenario, seed=seed, model=model, contract=contract,
                install_exit_s=install_exit_s, control_rate=control_rate, generation_stop=330, stage=stage)


def configs(stage):
    out = []
    if stage == 'smoke':
        a = (10, ORIGINAL_LAYOUT, 'multi_failure', 2026101511)
        out = [cfg(*a, 'legacy', stage=stage)]
        out += [cfg(*a, m, c, stage=stage) for m in ('full_v2', 'horizon') for c in ('joint', 'post_exit')]
        out += [cfg(40, NEW_LAYOUTS[0], 'multi_failure', NEW_SEEDS[0], 'horizon', stage=stage)]
    elif stage == 'contract':
        out = [cfg(n, ORIGINAL_LAYOUT, s, k, m, c, stage=stage) for n in (10, 20) for s in SCENARIOS
               for k in ORIGINAL_SEEDS for m in ('full_v2', 'horizon', 'cohort', 'closing')
               for c in ('joint', 'post_exit')]
    elif stage == 'scale':
        arms = [('legacy', 'joint'), ('full_v2', 'joint'), ('full_v2', 'post_exit'),
                ('horizon', 'joint'), ('horizon', 'post_exit')]
        out = [cfg(n, L, s, k, m, c, stage=stage) for n in (10, 20, 40) for L in NEW_LAYOUTS for s in SCENARIOS
               for k in NEW_SEEDS for m, c in arms]
    elif stage == 'sensitivity':
        settings = [dict(install_exit_s=w) for w in (5, 15, 20)] + [dict(control_rate=r) for r in (152, 610)]
        out = [cfg(10, L, s, k, 'horizon', c, stage=stage, **st) for st in settings for L in NEW_LAYOUTS
               for s in SCENARIOS for k in NEW_SEEDS for c in ('joint', 'post_exit')]
    elif stage == 'cca_patch':
        arms = [('legacy', 'joint'), ('horizon', 'joint'), ('horizon', 'post_exit')]
        out = [dict(cfg(n, L, s, k, m, c, stage=stage), ns3_variant='cca_peak_init') for n in (10, 20, 40)
               for L in NEW_LAYOUTS for s in SCENARIOS for k in NEW_SEEDS for m, c in arms]
    elif stage == 'all':
        # one execution of every remaining registered stage; records still land per stage
        out = configs('contract') + configs('scale') + configs('sensitivity')
    else:
        raise ValueError(stage)
    return out


def key(c):
    return hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()[:20]


def execute(c, workdir, keep_transcript):
    from fast_native_run import one
    from run_mechanisms import policy
    from audit_case import audit
    k = key(c)
    folder = workdir / k
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    legacy = c['model'] == 'legacy'
    kwargs = dict(pacing=not legacy, evidence_gate=not legacy, contract=c['contract'])
    if c['install_exit_s'] != 10:
        kwargs['install_exit_s'] = c['install_exit_s']
    start = time.time()
    row = one(BASE / 'engine/ns3/wsn-closed-loop', c['scenario'], policy('resource10_on'), c['seed'], folder=folder,
              profile='local15_event', topology=c['topology'], extended=True, source_only=True, generation_stop=330,
              faults=[[65, 2], [145, 3], [225, 6]] if c['scenario'] == 'multi_failure' else [],
              queue_discipline='fifo', epoch_certificate=True, report_retry=True, report_budget=True,
              report_retry_mode='always', controller_factory=FACTORIES[c['model']], controller_kwargs=kwargs,
              unified_budget=not legacy, protect_evidence=True, version_pacing=not legacy,
              control_rate=c['control_rate'], report_phase_seed=c['seed'])
    a = audit(row, folder)
    controller = json.loads((folder / (row['id'] + '.controller.json')).read_text())
    steps = controller['steps']
    releases = [s['contract_release'] for s in steps if s.get('contract_release')]
    lock = describe(steps, row['action_stop_ns'], releases)
    out = dict(configuration=c, configuration_key=k, audit=a, wall_seconds=time.time() - start,
               estimated_radio_joules=row['estimated_radio_joules'], bandit_updates=row['bandit_updates'],
               lockout=lock, hashes=row['hashes'], native_command=row['command'][1:])
    if keep_transcript:
        (STUDY / 'results' / c['stage'] / 'transcripts').mkdir(parents=True, exist_ok=True)
        payload = (folder / (row['id'] + '.controller.json')).read_bytes()
        (STUDY / 'results' / c['stage'] / 'transcripts' / (k + '.controller.json.gz')).write_bytes(
            gzip.compress(payload, compresslevel=9, mtime=0))
    return out, folder


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--stage')
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--shards', type=int, default=1)
    p.add_argument('--list')
    p.add_argument('--keep-raw', action='store_true')
    a = p.parse_args()
    if a.list:
        cs = configs(a.list)
        print(len(cs), len({key(c) for c in cs}))
        return
    os.environ.setdefault('TMPDIR', str(BASE / 'build_tmp'))
    cs = configs(a.stage)[a.shard::a.shards]
    raw = STUDY / 'raw' / a.stage
    done = set()
    for c in cs:
        target = STUDY / 'results' / c['stage'] / f'shard_{a.shard:02d}_of_{a.shards:02d}.jsonl'
        if target.exists():
            done |= {json.loads(x)['configuration_key'] for x in target.read_text().splitlines() if x.strip()}
    if True:
        for i, c in enumerate(cs):
            if key(c) in done:
                continue
            results = STUDY / 'results' / c['stage']
            results.mkdir(parents=True, exist_ok=True)
            target = results / f'shard_{a.shard:02d}_of_{a.shards:02d}.jsonl'
            keep = c['stage'] in ('smoke', 'contract')
            try:
                out, folder = execute(c, raw, keep)
            except BaseException:
                fail = results / f'failures_shard_{a.shard:02d}.txt'
                with fail.open('a') as f:
                    f.write(json.dumps(c) + '\n' + traceback.format_exc() + '\n')
                raise
            with target.open('a') as h:
                h.write(json.dumps(out, sort_keys=True) + '\n')
            if not a.keep_raw:
                shutil.rmtree(folder)
            print('DONE', i + 1, len(cs), c['topology'], c['scenario'], c['seed'], c['model'], c['contract'],
                  c['install_exit_s'], c['control_rate'], round(out['audit']['worst_source_service'], 6),
                  out['audit']['control_DATA_bytes'], 'L_broad', out['lockout']['broad_lockout'],
                  'L_strict', out['lockout']['strict_lockout'], 'wall', round(out['wall_seconds'], 1), flush=True)


if __name__ == '__main__':
    main()
