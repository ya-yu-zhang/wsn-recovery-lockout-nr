"""Checkpointed driver for dock2b (harness only; added after an interruption). Each case result (dock.mode_f with NetworkCQ,
identical seeds) is written to results/dock2b_<set>_cases/<folder>.json and skipped if present; the summary is then computed
by the same code as dock2b.main. Usage: dock2b_ckpt.py <probe|holdout> <out.json> [R]"""
import sys, os, json, concurrent.futures
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import dock2b
def one(args):
    f, Rn, d = args; p = os.path.join(d, os.path.basename(f) + '.json')
    if os.path.exists(p): return json.load(open(p))
    r = dock2b.dock.mode_f((f, Rn)); tmp = p + '.tmp'; json.dump(r, open(tmp, 'w')); os.replace(tmp, p); return r
def main():
    which, out = sys.argv[1], sys.argv[2]; Rn = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    d = os.path.join(HERE, '..', 'results', f'dock2b_{which}_cases'); os.makedirs(d, exist_ok=True)
    fs = dock2b.sets(which)
    with concurrent.futures.ProcessPoolExecutor(int(os.environ.get('PH2B_WORKERS', '6'))) as ex: rows = list(ex.map(one, [(f, Rn, d) for f in fs]))
    dock2b.dock.mode_f = lambda a, _rows={os.path.basename(f): r for f, r in zip(fs, rows)}: _rows[os.path.basename(a[0])]
    dock2b.concurrent.futures.ProcessPoolExecutor = concurrent.futures.ThreadPoolExecutor  # summary pass reads checkpoints only
    sys.argv = ['dock2b.py', which, out, str(Rn)]; dock2b.main()
if __name__ == '__main__': main()
