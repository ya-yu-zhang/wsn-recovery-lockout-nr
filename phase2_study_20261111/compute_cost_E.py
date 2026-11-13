"""(E) Read-only extraction of execution scale and wall-clock spans for the application-experience paragraph.
Sources: file-system modification times of the per-run output files written by the registered runs (no estimate,
no re-run), the CHANGELOG entries for technical incidents, and run counts from the frozen summaries.
Wall-clock span = last minus first output-file mtime of a batch; it excludes start-up before the first output file.
For the replay batch the earliest files belong to one case (flock_B0, N, joint) completed in a foreground diagnostic
before the third launch and reused from cache (CHANGELOG 18:01), so the span of the third launch itself is reported
separately (third_launch.span_min). Runs were parallel; CPU time is not recorded and is not reported."""
import json, os, datetime as dt
from pathlib import Path
H = Path(__file__).resolve().parent; S = Path('raw_on_request/scratch_phase2')
def span(d, exclude=()):
    fs = [p for p in Path(d).rglob('*') if p.is_file() and not any(x in p.parts for x in exclude)]; ts = sorted(p.stat().st_mtime for p in fs)
    f = lambda t: dt.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
    return dict(dir=str(d), files=len(fs), bytes=sum(p.stat().st_size for p in fs), first_mtime=f(ts[0]), last_mtime=f(ts[-1]),
                span_min=round((ts[-1] - ts[0]) / 60, 1))
out = dict(note=__doc__.strip(), timezone='America/Los_Angeles (box clock)', machine=dict(logical_cpus=os.cpu_count(), mem_gb=round(os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 2**30, 1)),
  batches={
    'trace_replay_full_192': dict(runs=json.load(open(H / 'flocklab/results_full/summary.json'))['n_done'], workers=4, **span(S / 'flocklab_full'),
        reused_foreground_case_dir='239e5252d0c4cf6b39bb', third_launch=span(S / 'flocklab_full', exclude=('239e5252d0c4cf6b39bb',))),
    'factorial_432': dict(runs=json.load(open(H / 'doe/summary.json'))['n_done'], workers=3, **span(S / 'doe')),
    'mode_fprime_holdout_108x100': dict(cases=108, replications_per_case=100, **span(H / 'results/dock2b_holdout_cases')),
  },
  concurrency='trace replay (4 workers) and factorial (3 workers) ran concurrently on the same machine (CHANGELOG 18:01)',
  incidents=[l.strip() for l in open(H / 'CHANGELOG.md') if any(k in l for k in ('OOM kill', 'BrokenProcessPool', 'per-case checkpoint'))])
(H / 'compute_cost_E.json').write_text(json.dumps(out, indent=1)); print(json.dumps(out['batches'], indent=1)); print(out['machine'])
