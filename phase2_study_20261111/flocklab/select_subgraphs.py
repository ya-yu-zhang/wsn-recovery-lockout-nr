"""Registered subgraph rule: roles sink 9, data relays 2,3, control relays 4,5, others 6,7,8, sources 0,1.
Required links (both directions, day PRR >= 0.90): 0-2,1-2,2-3,3-9,0-4,1-4,4-5,5-9,3-5,6-4,7-4,8-4.
Backtracking over injective assignments, role order 9,5,4,3,2,0,1,6,7,8, candidate order shuffled
with seed 20261111, stop at 10,000 valid assignments; draw K=4 distinct node sets per day (seed 20261111).
Writes one trace CSV per selected subgraph in role space: src,dst,prr,bits for every ordered role pair."""
import json, os, random, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); T = os.path.join(HERE, 'traces')
REQ = [(0,2),(1,2),(2,3),(3,9),(0,4),(1,4),(4,5),(5,9),(3,5),(6,4),(7,4),(8,4)]
ORDER = [9,5,4,3,2,0,1,6,7,8]; K = 4; CAP = 10000; TH = 0.90
def main():
    meta = json.load(open(os.path.join(T, 'traces_meta.json'))); sel = {}
    for tag, m in sorted(meta.items()):
        d = json.load(open(os.path.join(T, m['file'])))
        prr = {tuple(map(int, k.split('-'))): v['prr'] for k, v in d['links'].items()}
        good = lambda a, b: prr.get((a, b), 0) >= TH and prr.get((b, a), 0) >= TH
        nodes = list(d['nodes']); random.Random(20261111).shuffle(nodes)
        found = []
        def bt(i, assign):
            if len(found) >= CAP: return
            if i == len(ORDER): found.append(dict(assign)); return
            role = ORDER[i]
            for n in nodes:
                if n in assign.values(): continue
                assign[role] = n
                if all(good(assign[a], assign[b]) for a, b in REQ if a in assign and b in assign and (role in (a, b))):
                    bt(i + 1, assign)
                del assign[role]
        bt(0, {})
        distinct = {}; 
        for a in found: distinct.setdefault(tuple(sorted(a.values())), a)
        keys = sorted(distinct); pick = random.Random(20261111).sample(keys, min(K, len(keys)))
        sel[tag] = dict(day=m['day'], n_valid_assignments=len(found), n_distinct_node_sets=len(keys), subgraphs=[])
        for k, key in enumerate(pick):
            a = distinct[key]; rows = ['src,dst,prr,bits']
            for x in range(10):
                for y in range(10):
                    if x == y: continue
                    v = d['links'].get(f'{a[x]}-{a[y]}')
                    rows.append(f'{x},{y},{0.0 if v is None else v["prr"]:.6f},{"" if v is None else v["bits"]}')
            fn = os.path.join(T, f'subgraph_{tag}{k}.csv'); open(fn, 'w').write('\n'.join(rows) + '\n')
            sel[tag]['subgraphs'].append(dict(id=f'{tag}{k}', roles={str(r): a[r] for r in range(10)}, file=os.path.basename(fn), sha256=hashlib.sha256(open(fn, 'rb').read()).hexdigest()))
    json.dump(sel, open(os.path.join(T, 'subgraphs.json'), 'w'), indent=1); print(json.dumps(sel, indent=1)[:2500])
if __name__ == '__main__': main()
