"""Independent reference model of single-hop IEEE 802.15.4 unslotted CSMA-CA (E1 docking).

Written from the IEEE 802.15.4-2011 nonbeacon procedure (Sec. 5.1.1.4) and the
2.4 GHz O-QPSK PHY timing, using the same MAC constants that ns-3.44 configures
by default (macMinBE=3, macMaxBE=5, macMaxCSMABackoffs=4) and the study's
macMaxFrameRetries=2.  It shares no code with ns-3.  Channel model: every
station hears every other (5 m circle), any temporal overlap of two frames at
a receiver destroys both (no capture), a CCA is busy when any transmission
overlaps its 8-symbol window, and a transceiver is deaf while it turns around
or transmits.  Timing is kept in integer microseconds (1 symbol = 16 us).
"""
import heapq
import json
import math
import random
import sys

SYM = 16
UNIT = 20 * SYM          # aUnitBackoffPeriod
CCA = 8 * SYM
TURN = 12 * SYM          # aTurnaroundTime
ACK_DUR = (6 + 5) * 2 * SYM          # SHR+PHR (6 octets) + 5-octet ACK MPDU
ACK_WAIT = (20 + 12 + 10 + 12) * SYM  # macAckWaitDuration = 54 symbols
LIFS, SIFS = 40 * SYM, 12 * SYM
MIN_BE, MAX_BE, MAX_NB = 3, 5, 4
MAC_OVERHEAD = 11        # 9-octet short-address header (PAN ID compression) + 2-octet FCS


def simulate(stations, rate, payload=64, retries=2, stop_s=120., warm_s=5., seed=1, capacity=16,
             capture=False, cca_window='standard'):
    """Registered E1 reference: capture=False, cca_window='standard'.

    Diagnostic variants added after the registered comparison (E1 diagnosis, see PROTOCOL.md amendment):
    capture=True     -- a DATA frame that the coordinator locked onto first survives later overlaps, and an
                        ACK survives overlapping DATA (preamble capture; bounds SINR-based reception).
    cca_window='peak_reset' -- ns-3.44 PlmeCcaRequest resets the energy peak to zero, so a frame already on
                        the air that ends inside the 8-symbol window is not sensed.
    """
    rng = random.Random(seed)
    mpdu = payload + MAC_OVERHEAD
    data_dur = (6 + mpdu) * 2 * SYM
    ifs = LIFS if mpdu > 18 else SIFS
    stop, warm = int(stop_s * 1e6), int(warm_s * 1e6)
    ev, seq = [], [0]

    def push(t, kind, *args):
        seq[0] += 1
        heapq.heappush(ev, (t, seq[0], kind, args))

    tx = []                     # (start, end, src) of all transmissions (data src>=0, ACK src=-1-dst)
    coord_deaf = []             # coordinator turnaround/ACK intervals
    st = [dict(fifo=[], active=False, nb=0, be=MIN_BE, tries=0, req=0) for _ in range(stations)]
    c = dict(generated=0, queue_drops=0, requests=0, success=0, channel_access_failure=0, no_ack=0,
             cca=0, cca_busy=0, received=0)
    service = []

    def overlaps(a, b, exclude=None):
        return any(s <= b and e >= a for s, e, src in tx if src != exclude)

    def start_request(i, t):
        s = st[i]
        if s['active'] or not s['fifo']:
            return
        s['fifo'].pop(0)
        s['active'] = True
        s['req'] = t
        s['tries'] = 0
        if t >= warm:
            c['requests'] += 1
        start_csma(i, t)

    def start_csma(i, t):
        st[i]['nb'], st[i]['be'] = 0, MIN_BE
        backoff(i, t)

    def backoff(i, t):
        periods = rng.randrange(0, 2 ** st[i]['be'])
        push(t + periods * UNIT + CCA, 'cca_end', i, t + periods * UNIT)

    def finish(i, t, status):
        s = st[i]
        if s['req'] >= warm:
            c[status] += 1
            service.append(t - s['req'])
        s['active'] = False
        push(t + (ifs if status == 'success' else 0), 'next', i)

    for i in range(stations):
        push(int(rng.expovariate(rate) * 1e6), 'arrive', i)

    while ev:
        t, _, kind, args = heapq.heappop(ev)
        if t > stop + 5_000_000:
            break
        if kind == 'arrive':
            i, = args
            if t >= stop:
                continue
            if t >= warm:
                c['generated'] += 1
            s = st[i]
            if len(s['fifo']) + s['active'] < capacity:
                s['fifo'].append(t)
            elif t >= warm:
                c['queue_drops'] += 1
            start_request(i, t)
            push(t + max(1, int(rng.expovariate(rate) * 1e6)), 'arrive', i)
        elif kind == 'next':
            start_request(args[0], t)
        elif kind == 'cca_end':
            i, begin = args
            if cca_window == 'standard':
                busy = overlaps(begin, t, exclude=i)
            else:
                busy = any((s >= begin and s <= t) or (s <= t and e > t) for s, e, src in tx if src != i)
            if t >= warm:
                c['cca'] += 1
                c['cca_busy'] += busy
            s = st[i]
            if busy:
                s['nb'] += 1
                s['be'] = min(s['be'] + 1, MAX_BE)
                if s['nb'] > MAX_NB:
                    finish(i, t, 'channel_access_failure')
                else:
                    backoff(i, t)
            else:
                ts = t + TURN
                tx.append((ts, ts + data_dur, i))
                push(ts + data_dur, 'tx_end', i, ts)
        elif kind == 'tx_end':
            i, ts = args
            te = t
            if capture:
                clean = not any(s <= ts and e >= ts for s, e, src in tx if src != i)
            else:
                clean = not any(s <= te and e >= ts for s, e, src in tx if src != i)
            awake = not any(a <= te and b >= ts for a, b in coord_deaf)
            if clean and awake:
                if t >= warm:
                    c['received'] += 1
                a0 = te + TURN
                coord_deaf.append((te, a0 + ACK_DUR + TURN))
                tx.append((a0, a0 + ACK_DUR, -1 - i))
                push(a0 + ACK_DUR, 'ack_end', i, a0)
            push(te + ACK_WAIT, 'ack_timeout', i, te)
            st[i]['ack_pending'] = te
        elif kind == 'ack_end':
            i, a0 = args
            ok = capture or not any(s <= t and e >= a0 for s, e, src in tx if src >= 0 and src != i)
            s = st[i]
            if ok and s.get('ack_pending') is not None:
                s['ack_pending'] = None
                finish(i, t, 'success')
        elif kind == 'ack_timeout':
            i, te = args
            s = st[i]
            if s.get('ack_pending') != te:
                continue
            s['ack_pending'] = None
            if s['tries'] < retries:
                s['tries'] += 1
                start_csma(i, t)
            else:
                finish(i, t, 'no_ack')
        # discard intervals that can no longer overlap anything
        if len(tx) > 512:
            horizon = t - 10 * data_dur
            tx[:] = [x for x in tx if x[1] >= horizon]
            coord_deaf[:] = [x for x in coord_deaf if x[1] >= horizon]
    service.sort()
    q = (lambda f: service[int(f * (len(service) - 1))] / 1000 if service else 0.)
    c.update(simulator='independent python reference', capture=capture, cca_window=cca_window, stations=stations, rate=rate, payload=payload,
             retries=retries, seed=seed, stop_s=stop_s, warm_s=warm_s,
             service_mean_ms=(sum(service) / len(service) / 1000 if service else 0.),
             service_p50_ms=q(.5), service_p90_ms=q(.9))
    return c


if __name__ == '__main__':
    a = dict(x.split('=') for x in sys.argv[1:])
    print(json.dumps(simulate(int(a['stations']), float(a['rate']), seed=int(a.get('seed', 1)))))
