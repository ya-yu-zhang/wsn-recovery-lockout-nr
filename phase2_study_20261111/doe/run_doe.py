"""Run the registered DOE on ns-3 (frozen native binary). Requires doe/predictions_FDOE.json (hashed) to exist first."""
import sys, json, concurrent.futures, traceback, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE.parent / 'common'))
import ns3run
def main():
    W = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    pred = HERE / 'predictions_FDOE.json'; assert pred.exists(), 'prospective predictions must be frozen first (H3)'
    design = json.load(open(HERE / 'design.json')); cs = [d['ns3'] for d in design['cases']]
    rows = []; fails = []
    with concurrent.futures.ProcessPoolExecutor(W) as pool:
        fut = {pool.submit(ns3run.execute, c, 'doe'): c for c in cs}
        for f in concurrent.futures.as_completed(fut):
            try: r = f.result(); rows.append(ns3run.compact(r)); print('DONE', len(rows), r['configuration']['topology'], r['configuration']['point'], r['configuration']['arm'], r['audit']['status'], flush=True)
            except BaseException: fails.append(dict(configuration=fut[f], traceback=traceback.format_exc())); print('FAILED', fut[f], flush=True)
    json.dump(dict(n_cases=len(cs), n_done=len(rows), failures=fails, predictions_sha256=hashlib.sha256(pred.read_bytes()).hexdigest(), rows=rows), open(HERE / 'runs.json', 'w'), indent=1)
if __name__ == '__main__': main()
