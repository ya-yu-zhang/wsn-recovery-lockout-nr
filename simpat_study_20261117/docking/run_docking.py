"""E1 docking: ns-3.44 lr-wpan versus the independent reference on a registered grid."""
from pathlib import Path
import concurrent.futures, json, subprocess, sys

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
NS = STUDY.parent / 'ns3_vendor/ns-allinone-3.44/ns-3.44'
sys.path.insert(0, str(HERE))
from csma_reference import simulate  # noqa: E402

STATIONS = (2, 4, 8, 12, 16)
LOADS = (0.05, 0.15, 0.30, 0.45, 0.60)   # aggregate offered DATA airtime fraction
REPLICATIONS = (1, 2, 3, 4, 5)
DATA_AIRTIME_S = (6 + 64 + 11) * 2 * 16e-6


def grid():
    return [dict(stations=n, load=g, rate=g / (n * DATA_AIRTIME_S), seed=r)
            for n in STATIONS for g in LOADS for r in REPLICATIONS]


def compile_binary():
    b = NS / 'build'
    out = HERE / 'csma-docking'
    cmd = ['g++', '-std=c++20', '-O2', '-I', str(b / 'include'), str(HERE / 'csma_docking.cc'), '-L', str(b / 'lib'),
           '-Wl,-rpath,' + str(b / 'lib')]
    cmd += ['-lns3.44-' + x for x in ('lr-wpan', 'spectrum', 'mobility', 'propagation', 'antenna', 'network', 'stats', 'core')]
    subprocess.run(cmd + ['-o', str(out)], check=True)
    return out


def ns3_case(binary, c):
    out = HERE / f"tmp_{c['stations']}_{c['load']}_{c['seed']}.json"
    subprocess.run([str(binary), f"--stations={c['stations']}", f"--rate={c['rate']!r}", '--payload=64', '--retries=2',
                    '--stop=120', '--warm=5', '--seed=1', f"--run={c['seed']}", f'--output={out}'], check=True)
    r = json.loads(out.read_text())
    out.unlink()
    r['load'] = c['load']
    return r


def ref_case(c):
    r = simulate(c['stations'], c['rate'], payload=64, retries=2, stop_s=120., warm_s=5., seed=1000 + c['seed'])
    r['load'] = c['load']
    return r


def main():
    results = STUDY / 'results' / 'docking'
    results.mkdir(parents=True, exist_ok=True)
    binary = compile_binary()
    cases = grid()
    if '--ns3-only' in sys.argv:            # E5: patched simulator, reference already recorded
        ns3 = [ns3_case(binary, c) for c in cases]
        (results / sys.argv[sys.argv.index('--ns3-only') + 1]).write_text(
            ''.join(json.dumps(r, sort_keys=True) + '\n' for r in ns3))
        print('DOCKING_DONE', len(ns3), flush=True)
        return
    with concurrent.futures.ProcessPoolExecutor(4) as pool:
        ref = list(pool.map(ref_case, cases))
    ns3 = [ns3_case(binary, c) for c in cases]
    (results / 'reference.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in ref))
    (results / 'ns3.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in ns3))
    print('DOCKING_DONE', len(ref), len(ns3), flush=True)


if __name__ == '__main__':
    main()
