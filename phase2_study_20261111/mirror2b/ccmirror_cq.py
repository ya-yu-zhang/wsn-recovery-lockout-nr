"""Phase-2b contention/queue submodel for the SimPy mirror (Mode F'). Every constant is taken a priori from the ns-3 driver
source (engine/ns3/*.cc|*.h) or the ns-3.44 LrWpan defaults; nothing is fitted to gate outcomes. The per-hop link quality is
the FROZEN Phase-2 calibration h(d) (mirror/calibration.json, a per-MAC-job success probability), converted to a per-attempt
success q = 1 - (1 - h)^(1/3) for 3 MAC attempts (macMaxFrameRetries = 2, driver l.503).
Implemented ns-3 rules (driver line refs):
  * per-node FIFO queue, capacity 16 including the active frame (l.155, l.186; queueDiscipline fifo -> epoch::Select index 0);
  * unslotted CSMA/CA, macMinBE 3, macMaxBE 5, macMaxCSMABackoffs 4, unit backoff 20 symbols, CCA 8 symbols,
    turnaround 12 symbols, ACK wait 54 symbols, 16 us/symbol, 32 us/octet, 6 octets PHY overhead;
    channel-access failure ends the job; CCA busy if another node within ccaRadius = 10^((-S-10-46.6777)/30) m is on air (l.234);
  * PSDU sizes: data 64+36+11 = 111 B, report 80+36+11 = 127 B, install 64+36+11 = 111 B, ACK 5 B;
  * unified control budget per node: rate 305 B/s, burst 4572 B, reserve 1524 B for non-priority, 381 B per control frame,
    priority = install frames, source reports, and relay reports while leased (l.176-181, l.376);
  * report retry: once per (source, stamp, node) after a failed MAC job, delay 20 ms + ((seq*2654435761+node) mod 40) ms,
    only if within stamp + 3 s (l.205-214; report-retry byte budget not modelled);
  * local state = depth bin + 4*[busy*100 > cca*35 over the last 20 s of flow<2 jobs] + 8*leased (wsn-local-report.h);
    relay lease 12 s after receiving a data frame (l.311); source period 5 s if (<15 s since install) or failure or
    state != state at the last emission, else 15 s (unified_control_budget.h); relay period 15 s, or 10 s when urgent
    (leased state changed) (wsn-local-report.h); failure = currentN >= 10 and currentFailed*100 > currentN*20 (l.368),
    20 s window of current-version source jobs (version_failure_history.h);
  * timely = delivered at the sink within 200 ms of generation (l.160).
Not modelled (declared): hidden-terminal collisions and capture beyond h(d), the report-retry byte budget, the PHY turn-on delays, and the priority-lease effects on the data path."""
import math, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mirror'))
import ccmirror as M
S = M.S; BUCKET = M.BUCKET; U32 = M.U32
SYM = 16e-6; UNIT = 20 * SYM; CCA_T = 8 * SYM; TURN = 12 * SYM; ACKWAIT = 54 * SYM; OCT = 32e-6
AIR = lambda psdu: (psdu + 6) * OCT
PSDU = {'data': 111, 'report': 127, 'install': 111}; ACK = 5
MIN_BE, MAX_BE, MAX_NB, MAX_RETRIES = 3, 5, 4, 2
CAP = 16; RATE, BURST, RESERVE, RESV = 305., 4572., 1524., 381.
RX_SENS = -106.58
CCA_R = 10 ** ((-RX_SENS - 10 - 46.6777) / 30)

class Frame:
    __slots__ = ('kind', 'flow', 'seq', 'path', 'cursor', 'gen_ns', 'version', 'body', 'retried')
    def __init__(self, kind, flow, seq, path, gen_ns, version=0, body=None):
        self.kind = kind; self.flow = flow; self.seq = seq; self.path = tuple(path); self.cursor = 0
        self.gen_ns = gen_ns; self.version = version; self.body = body; self.retried = set()

class NetworkCQ:
    def __init__(self, env, rng, points, arrivals, faults, drop, calib, seed, generation_stop=330):
        import simpy
        self.simpy = simpy; self.env = env; self.rng = rng; self.points = points; self.cal = calib
        self.alive = {n: True for n in points}; self.drop = drop; self.seed = seed; self.gstop = generation_stop
        self.version = {0: 0, 1: 0}; self.since = {0: 0, 1: 0}; self.path = {0: M.INITIAL[0], 1: M.INITIAL[1]}
        self.gen = {0: {}, 1: {}}; self.timely = {}; self.latest = {}
        self.src_hist = {0: [], 1: []}       # (end_ns, failed, generation_version)
        self.hist = {n: [] for n in points}  # (end_ns, cca, busy) of flow<2 jobs at node n
        self.queue = {n: [] for n in points}; self.active = {n: None for n in points}; self.wake = {n: env.event() for n in points}
        self.onair = {}; self.credit = {n: (BURST, 0.0) for n in points}; self.lease = {n: -1 for n in points}
        self.last_emit = {n: 0 for n in points}; self.last_state = {n: 0 for n in points}
        self.seq = 0; self.ctl_seq = 0; self.retry_keys = set(); self.sink_seen = set()
        self.stats = dict(cca=0, busy=0, caf=0, noack=0, qdrop=0, bdrop=0, reports=0, urgent=0); NetworkCQ.last = self
        env.process(self._faults(faults)); env.process(self._arrivals(arrivals))
        for n in points:
            if n != 9: env.process(self._reports(n))
            env.process(self._server(n))
    def now(self): return int(round(self.env.now * S))
    def q_attempt(self, a, b):
        if not (self.alive[a] and self.alive[b]): return 0.0
        d = math.dist(self.points[a], self.points[b]); k, d0 = self.cal['logit_k'], self.cal['logit_d0']
        h = 1 / (1 + math.exp(k * (d - d0))); return 1 - (1 - h) ** (1 / 3)
    def _faults(self, faults):
        for when, relay in sorted(faults):
            yield self.env.timeout(max(0, when - self.env.now)); self.alive[relay] = False; self.queue[relay].clear()
    # ---- queueing and budget ------------------------------------------------
    def enqueue(self, n, fr):
        if not self.alive[n]: return False
        if len(self.queue[n]) + (self.active[n] is not None) >= CAP: self.stats['qdrop'] += 1; return False
        if fr.kind in ('report', 'install'):
            prio = fr.kind == 'install' or (fr.body['node'] < 2) or bool(fr.body.get('leased'))
            c, last = self.credit[n]; t = self.env.now; c = min(BURST, c + (t - last) * RATE)
            need = RESV + (0 if prio else RESERVE)
            if c >= need: self.credit[n] = (c - RESV, t)
            else: self.credit[n] = (c, t); self.stats['bdrop'] += 1; return False
        self.queue[n].append(fr)
        if not self.wake[n].triggered: self.wake[n].succeed()
        return True
    def busy_at(self, n):
        t = self.env.now; p = self.points[n]
        return any(v != n and end > t and math.dist(self.points[v], p) <= CCA_R for v, end in self.onair.items())
    def _server(self, n):
        env = self.env
        while True:
            if not self.queue[n]:
                self.wake[n] = env.event(); yield self.wake[n]; continue
            if not self.alive[n]: self.queue[n].clear(); continue
            fr = self.queue[n].pop(0); self.active[n] = fr; nxt = fr.path[fr.cursor + 1]
            cca = busy = 0; ok = False; status = 'noack'
            for attempt in range(MAX_RETRIES + 1):
                nb, be = 0, MIN_BE; access = False
                while True:
                    yield env.timeout(self.rng.randrange(2 ** be) * UNIT + CCA_T); cca += 1
                    if self.busy_at(n):
                        busy += 1; nb += 1; be = min(be + 1, MAX_BE)
                        if nb > MAX_NB: break
                    else: access = True; break
                if not access: status = 'caf'; break
                air = AIR(PSDU[fr.kind]); self.onair[n] = env.now + air; yield env.timeout(air)
                if self.rng.random() < self.q_attempt(n, nxt):
                    yield env.timeout(TURN); self.onair[nxt] = env.now + AIR(ACK); yield env.timeout(AIR(ACK)); ok = True; break
                yield env.timeout(ACKWAIT)
            end = self.now(); self.stats['cca'] += cca; self.stats['busy'] += busy
            if not ok: self.stats[status] += 1
            if fr.flow < 2:
                self.hist[n].append((end, cca, busy))
                if n == fr.flow: self.src_hist[n].append((end, not ok, fr.version))
            self.active[n] = None
            if ok: self.arrive(nxt, fr)
            elif fr.kind == 'report' and fr.body['node'] < 2:
                key = (fr.body['node'], fr.body['stamp_ns'], n)
                delay = 0.020 + ((fr.seq * 2654435761 + n) % 40) / 1000.
                if key not in self.retry_keys and self.now() + int(delay * S) <= fr.body['stamp_ns'] + 3 * S:
                    self.retry_keys.add(key); env.process(self._retry(n, fr, delay))
    def _retry(self, n, fr, delay):
        yield self.env.timeout(delay); self.ctl_seq += 1; fr.seq = self.ctl_seq; self.enqueue(n, fr)
    def arrive(self, node, fr):
        if not self.alive[node]: return
        fr.cursor += 1
        if fr.flow < 2 and 2 <= node <= 8: self.lease[node] = max(self.lease[node], self.now() + 12 * S)
        if fr.cursor + 1 < len(fr.path): self.enqueue(node, fr); return
        now = self.now()
        if fr.kind == 'data':
            if (fr.flow, fr.seq) in self.sink_seen: return
            self.sink_seen.add((fr.flow, fr.seq))
            if now - fr.gen_ns <= 200_000_000: self.timely.setdefault(fr.gen_ns // BUCKET, [0, 0])[fr.flow] += 1
        elif fr.kind == 'report':
            rep = dict(fr.body); rep['received_ns'] = now; old = self.latest.get(rep['node'])
            if old is None or old['stamp_ns'] <= rep['stamp_ns']: self.latest[rep['node']] = rep
        elif fr.kind == 'install':
            f, decision, paths = fr.body['target'], fr.body['decision'], fr.body['paths']
            if decision > self.version[f]: self.version[f] = decision; self.since[f] = now; self.path[f] = tuple(paths[f])
    # ---- traffic --------------------------------------------------------------
    def _arrivals(self, arrivals):
        for t, f in arrivals:
            yield self.env.timeout(max(0, t - self.env.now))
            now = self.now(); b = now // BUCKET; self.gen[f][b] = self.gen[f].get(b, 0) + 1; self.seq += 1
            self.enqueue(f, Frame('data', f, self.seq, self.path[f], now, self.version[f]))
    def state(self, n, now):
        depth = len(self.queue[n]) + (self.active[n] is not None)
        cca = sum(h[1] for h in self.hist[n] if h[0] >= now - 20 * S); busy = sum(h[2] for h in self.hist[n] if h[0] >= now - 20 * S)
        b = 0 if depth == 0 else 1 if depth <= 2 else 2 if depth <= 8 else 3
        return b + 4 * (cca != 0 and busy * 100 > cca * 35) + 8 * (self.lease[n] > now)
    def _reports(self, n):
        yield self.env.timeout(M.phase_s(self.seed, n))
        while self.env.now + 5. < self.gstop + 15:
            if self.alive[n]:
                now = self.now(); st = self.state(n, now); last = self.last_emit[n]
                if n < 2:
                    cur = [h for h in self.src_hist[n] if h[0] >= now - 20 * S and h[2] == self.version[n]]
                    failure = len(cur) >= 10 and sum(h[1] for h in cur) * 100 > len(cur) * 20
                    urgent = now - self.since[n] < 15 * S or failure or st != self.last_state[n]
                    period = 5 if urgent else 15; emit = last == 0 or now - last >= period * S
                else:
                    urgent = st >= 8 and st != self.last_state[n]; period = 10 if urgent else 15
                    emit = last == 0 or now - last >= 15 * S or (urgent and now - last >= 10 * S)
                if emit:
                    self.last_emit[n] = now; self.last_state[n] = st; self.stats['reports'] += 1; self.stats['urgent'] += urgent
                    b = now // BUCKET
                    rep = dict(node=n, stamp_ns=now, version=self.version[n] if n < 2 else 0, period_s=period, leased=self.lease[n] > now)
                    if n < 2:
                        cur = [h for h in self.src_hist[n] if h[0] >= now - 20 * S and h[2] == self.version[n]]
                        rep['current_n'] = len(cur); rep['current_failed'] = sum(h[1] for h in cur)
                        rep['epoch_first_bucket'] = -(-self.since[n] // BUCKET)
                        rep['buckets'] = [[U32, rep['epoch_first_bucket']]] + [[b - k, self.gen[n].get(b - k, 0)] for k in (1, 2, 3) if b - k >= 0]
                    else: rep['buckets'] = []
                    self.ctl_seq += 1; self.enqueue(n, Frame('report', 65000, self.ctl_seq, M.monitor_path(n), now, body=rep))
            yield self.env.timeout(5.)
    def send_install(self, decision, paths, targets):
        t = self.now() / S
        for f in targets:
            start, end, mask = self.drop
            if start >= 0 and t >= start and (end < 0 or t < end) and (mask >> f) & 1: continue
            self.ctl_seq += 1
            self.enqueue(9, Frame('install', 65001, self.ctl_seq, (9, 5, 4, f), self.now(), body=dict(target=f, decision=decision, paths=paths)))
    def observation(self):
        t = self.now(); reps = [r for r in self.latest.values() if r['received_ns'] <= t]
        return dict(time_ns=t, reports=reps, timely_buckets={str(b): list(v) for b, v in self.timely.items()})

def run_free_cq(points, arrivals, faults, drop, arm, model, wait_s, calib, seed, rng, generation_stop=330):
    """Same FSM and same decision policy as Phase-2 Mode F (ccmirror.run_free), with NetworkCQ in place of Network."""
    orig = M.Network
    try:
        M.Network = NetworkCQ
        return M.run_free(points, arrivals, faults, drop, arm, model, wait_s, calib, seed, rng, generation_stop)
    finally:
        M.Network = orig
