"""Registered 3^(5-2) fractional factorial (resolution III). Writes doe/design.json (432 cases)
with the ns-3 configuration and the Mode-F mirror spec (points/arrivals from the frozen engine generators)."""
import sys, json, hashlib, itertools
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE.parent / 'common'))
import ns3run
F = ns3run.F
START = (0.0, 120.0, 240.0); LENGTH = (20.0, 60.0, 120.0); MASK = (1, 2, 3)
FAULTS = ([], [[100, 3], [180, 6]], [[145, 3], [225, 6]]); WAIT = (10, 15, 20)
LAYOUTS = tuple(range(2026111101, 2026111109)); SEEDS = tuple(range(2026111201, 2026111209)); ARMS = ('joint', 'post_exit')
FROZEN_LAYOUTS = {2026101501, 2026101521, 2026101522, 2026101523, 2026110301, 2026110302, 2026110303, 2026110304, 2026110401, 2026110402, 2026110403, 2026110404} | set(range(2026110410, 2026110418))
def points_design():
    pts = []
    for a, b, c in itertools.product(range(3), repeat=3):
        d = (a + b + c) % 3; e = (a + 2 * b) % 3
        pts.append(dict(idx=len(pts), A=a, B=b, C=c, D=d, E=e, drop_start=START[a], drop_end=START[a] + LENGTH[b], mask=MASK[c], faults=FAULTS[d], wait_s=WAIT[e]))
    return pts
def main():
    assert not set(LAYOUTS) & FROZEN_LAYOUTS
    cases = []
    for L, seed in zip(LAYOUTS, SEEDS):
        topo = f'budget_10_{L}'; pts = F.geometry(topo); arr = [(t, f) for t, f, _, _ in F.arrivals('multi_failure', seed, 330)]
        for p in points_design():
            for arm in ARMS:
                cfg = dict(stage='doe', topology=topo, scenario='multi_failure', seed=seed, arm=arm, faults=p['faults'], drop_install_start_sec=p['drop_start'],
                           drop_install_end_sec=p['drop_end'], drop_install_mask=p['mask'], wait_s=p['wait_s'], point=p['idx'])
                spec = dict(points={str(k): list(v) for k, v in pts.items()}, arrivals=arr, faults=p['faults'], arm=arm, model='horizon', wait_s=p['wait_s'], seed=seed,
                            drop=(p['drop_start'], p['drop_end'], p['mask']))
                cases.append(dict(key=ns3run.key_of(cfg), point=p, layout=L, arm=arm, ns3=cfg, mirror_spec=spec))
    assert len(cases) == 432
    (HERE / 'design.json').write_text(json.dumps(dict(n=len(cases), cases=cases)))
    print(len(cases), hashlib.sha256((HERE / 'design.json').read_bytes()).hexdigest())
if __name__ == '__main__': main()
