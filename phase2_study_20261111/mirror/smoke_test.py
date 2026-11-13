"""Technical smoke test (allowed by prereg): base topology, synthetic placeholder calibration,
generation_stop=60. Excluded from all analyses."""
import sys, os, random, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, HERE + '/../vendor')
import ccmirror as M
pts = {0:(0,0),1:(0,4),2:(40,0),3:(80,0),4:(40,35),5:(80,35),6:(60,-35),7:(100,-35),8:(20,-35),9:(120,0)}
rng0 = random.Random(1); arr = []
for f in (0, 1):
    t = 0
    while True:
        t += rng0.expovariate(5)
        if t >= 60: break
        arr.append((t, f))
arr.sort()
cal = dict(logit_k=0.2, logit_d0=60, hop_latency_s=0.007)
for arm in ('joint', 'post_exit'):
    t0 = time.time()
    fsm = M.run_free(pts, arr, [[30, 3]], (0.0, 40.0, 3), arm, 'horizon', 10, cal, 7, random.Random(3), generation_stop=60)
    print(arm, 'exits', [x / M.S for x in fsm.exits()], 'inst_after', fsm.installs_after_first_exit(), 'e1', fsm.e1(), '%.2fs' % (time.time() - t0))
    print('  ', [(r['t'] // M.S, r['reason'][:12], r['phi'], r.get('install')) for r in fsm.log][:12])
