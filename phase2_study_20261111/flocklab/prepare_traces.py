"""Registered FlockLab ingestion: Zenodo 10.5281/zenodo.3727526, platform sky (TelosB/CC2420),
channel 26, 0 dBm, 8-byte payload. Day A = 2019-09-15, Day B = 2020-01-22 (UTC). All tests of the
day in time order; per directed link the 100-bit rcv_stream strings are concatenated."""
import csv, json, os, sys, hashlib, collections
SRC = 'raw_on_request/flocklab_probe'
DAYS = {'A': ('2019-09-15', '2019-09/2019-09_FlockLab_sky.csv'), 'B': ('2020-01-22', '2020-01/2020-01_FlockLab_sky.csv')}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'traces'); os.makedirs(OUT, exist_ok=True)
def main():
    meta = {}
    for tag, (day, rel) in DAYS.items():
        rows = [r for r in csv.DictReader(open(os.path.join(SRC, rel))) if r['date_time'][:10] == day and r['rf_channel'] == '26' and r['tx_power'] == '0' and r['payload'] == '8']
        tests = sorted({(r['date_time'], int(r['test_number'])) for r in rows})
        order = {t[1]: i for i, t in enumerate(tests)}
        link = collections.defaultdict(dict); nodes = set(); n_missing = 0
        for r in rows:
            a, b = int(r['snd_id']), int(r['rcv_id']); nodes |= {a, b}
            if not r['rcv_stream'] or len(r['rcv_stream']) != 100: n_missing += 1; continue  # unrecorded (empty) row = no observation, not loss
            link[(a, b)][order[int(r['test_number'])]] = r['rcv_stream']
        out = {}
        for (a, b), per in link.items():
            bits = ''.join(per[i] for i in sorted(per))  # observed tests only, in time order
            out[f'{a}-{b}'] = dict(prr=bits.count('1') / len(bits), bits=bits)
        path = os.path.join(OUT, f'day{tag}_{day}.json'); json.dump(dict(day=day, tests=[t[1] for t in tests], nodes=sorted(nodes), links=out), open(path, 'w'))
        meta[tag] = dict(day=day, n_tests=len(tests), n_rows=len(rows), n_unrecorded_rows=n_missing, n_nodes=len(nodes), n_links=len(out), file=os.path.basename(path), sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(),
                         source_zip_sha256=hashlib.sha256(open(os.path.join(SRC, rel.split('/')[0] + '_pre.zip'), 'rb').read()).hexdigest())
    json.dump(meta, open(os.path.join(OUT, 'traces_meta.json'), 'w'), indent=1); print(json.dumps(meta, indent=1))
if __name__ == '__main__': main()
