"""Smoke test (excluded from analyses): base topology, synthetic arrivals, generation_stop 60 s."""
import sys, os, json, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vendor'))
import ccmirror_cq as Q
sys.path.insert(0, '/workspace/wsn_ablation/repo/control_budget_study_20261015/engine')
from wsn.topology import geometry
pts = geometry('base'); cal = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mirror', 'calibration.json')))
rng = random.Random(1); arr = sorted((rng.uniform(0, 60), f) for f in (0, 1) for _ in range(600))
for arm in ('joint', 'post_exit'):
    t0 = time.time(); fsm = Q.run_free_cq(pts, arr, [], (0, 40, 3), arm, 'horizon', 10, cal, 0, random.Random(2), 60)
    print(arm, 'exits', [x / 1e9 for x in fsm.exits()], 'E1', fsm.e1(True), 'wall', round(time.time() - t0, 2))
    print([ (r['t']//10**9, r['reason'], r['phi']) for r in fsm.log][:12])
print(Q.NetworkCQ.last.stats, 'CCA_R', round(Q.CCA_R, 1))
