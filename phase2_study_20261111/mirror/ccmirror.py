"""Independent SimPy mirror of the confirmation-contract recovery gate (phase-2 docking).

Written from the manuscript specification (Sec. 3.2-3.7: pacing, evidence-qualified
recovery, Prop. 1, FSM S1-S6) and the documented constants. It does NOT import the original
controller (wsn.*, horizon_controller, ...).

Intra-tick order (declared spec choice; the paper leaves it implicit):
  (1) PostExit release check on the state at the end of the previous tick;
  (2) feedback-pending expiry (decision + 10 s);
  (3) installation observation (confirmation / unconfirmed exit / one retry per source at +5 s);
  (4) settled-service predicate Psi and failure eligibility F_s, then Phi;
  (5) decision (exogenous in Mode C; own rule in Mode F).
Times are integer nanoseconds.
"""
import math, heapq
S = 1_000_000_000
BUCKET = 5 * S
U32 = (1 << 32) - 1
INITIAL = ((0, 2, 3, 9), (1, 2, 3, 9))
REASONS = ('missing_fresh_source', 'installation_unconfirmed', 'unknown_installed_version',
           'no_settled_same_version_bucket', 'incomplete_or_sparse_generation_evidence', 'known')


class Installation:
    def __init__(self, decision, t, paths, wait_ns):
        self.decision = decision; self.t = t; self.paths = paths; self.deadline = t + wait_ns
        self.conf = {}; self.attempts = [0, 0]; self.closed = False; self.outcome = None
        self.exit_ns = None; self.late = False

    def observe(self, t, reports):
        """Spec: confirmation = fresh (<=8 s) source report of this version stamped at/after the decision."""
        if self.closed and self.outcome != 'abandoned_unconfirmed':
            return []
        for f in (0, 1):
            r = reports.get(f)
            if r and 0 <= t - r['stamp_ns'] <= 8 * S and r['version'] == self.decision and r['stamp_ns'] >= self.t and f not in self.conf:
                self.conf[f] = t
        missing = [f for f in (0, 1) if f not in self.conf]
        retry = []
        if not missing:
            if self.closed: self.late = True
            self.closed = True; self.outcome = 'confirmed'
        elif not self.closed and t >= self.deadline:
            self.closed = True; self.outcome = 'abandoned_unconfirmed'; self.exit_ns = t
        elif not self.closed and t >= self.t + 5 * S:
            retry = [f for f in missing if self.attempts[f] < 1 and t >= self.t + (self.attempts[f] + 1) * 5 * S]
            for f in retry: self.attempts[f] += 1
        return retry


class GateFSM:
    """model in {full_v2, horizon, cohort, closing}; arm in {joint, post_exit, sham_release,
    wait_extend, thresh_relax_scoped}."""
    def __init__(self, model='horizon', arm='joint', wait_s=10, action_stop_ns=320 * S):
        self.model = model; self.arm = arm
        self.wait_ns = (20 if arm == 'wait_extend' else wait_s) * S
        self.action_stop = action_stop_ns
        self.inst = None; self.installs = []; self.pending = None
        self.version_paths = {0: INITIAL}; self.current = list(INITIAL)
        self.visible = {0: 0, 1: 0}; self.since = {0: 0, 1: 0}
        self.cache = {}; self.seq = 0; self.log = []; self.releases = []

    # ---- spec helpers -------------------------------------------------
    def source_view_ns(self, r):
        if self.model == 'full_v2':
            return 16 * S if r.get('period_s') == 15 else 8 * S
        return 16 * S

    def _cache(self, t, reports):
        cutoff = t - 60 * S
        self.cache = {k: v for k, v in self.cache.items() if (k[1] + 1) * BUCKET >= cutoff}
        for f in (0, 1):
            r = reports.get(f)
            if not r: continue
            for b, n in r['buckets']:
                if b == U32 or (b + 1) * BUCKET > r['stamp_ns'] or (b + 1) * BUCKET < cutoff: continue
                self.cache.setdefault((f, b), n)

    def _versions(self, reports):
        for f in (0, 1):
            r = reports.get(f)
            if not r: continue
            if r['version'] != self.visible[f]:
                self.visible[f] = r['version']
                anchor = r.get('epoch_first_bucket')
                self.since[f] = anchor * BUCKET if isinstance(anchor, int) else r['stamp_ns']
            if r['version'] in self.version_paths:
                self.current[f] = self.version_paths[r['version']][f]

    def _cohort(self, buckets):
        counts = []
        for f in (0, 1):
            if any((f, b) not in self.cache for b in buckets): return None
            counts.append(sum(self.cache[f, b] for b in buckets))
        return counts

    def psi(self, t, reports, timely):
        fresh = {f: r for f, r in reports.items() if f in (0, 1) and 0 <= t - r['stamp_ns'] <= self.source_view_ns(r)}
        if any(f not in fresh for f in (0, 1)): return 'missing_fresh_source', None
        if self.inst is not None and not (self.inst.closed and self.inst.outcome == 'confirmed'):
            return 'installation_unconfirmed', None
        if any(fresh[f]['version'] not in self.version_paths or self.version_paths[fresh[f]['version']][f] != self.current[f] for f in (0, 1)):
            return 'unknown_installed_version', None
        bound = max(self.since.values()); last = t // BUCKET - 1
        buckets = [b for b in range(max(0, last - 2), last + 1) if b * BUCKET >= bound and (b + 1) * BUCKET + 200_000_000 <= t]
        reason = None
        if not buckets: reason = 'no_settled_same_version_bucket'
        else:
            counts = self._cohort(buckets)
            if counts is None or min(counts) < 20: reason = 'incomplete_or_sparse_generation_evidence'
        if reason is not None and self.model in ('cohort', 'closing'):
            # latest two consecutive closed buckets received for both sources, start >= epoch,
            # end >= 0.2 s before t, cohort end age <= 20 s, >= 20 offered per source
            for b in range(last, max(-1, last - 5), -1):
                pair = [b - 1, b]
                if pair[0] < 0 or pair[0] * BUCKET < bound or (b + 1) * BUCKET + 200_000_000 > t or t - (b + 1) * BUCKET > 20 * S: continue
                c = self._cohort(pair)
                if c is not None and min(c) >= 20:
                    buckets, reason = pair, None; break
        if reason is not None: return reason, None
        counts = self._cohort(buckets)
        tim = [sum(timely.get(str(b), [0, 0])[f] for b in buckets) for f in (0, 1)]
        return 'known', min(n / d for n, d in zip(tim, counts))

    def fs_eligible(self, t, reports):
        out = []
        for f in (0, 1):
            r = reports.get(f)
            if r and 0 <= t - r['stamp_ns'] <= 8 * S and r.get('current_n') is not None and r['current_n'] >= 20 and r['current_failed'] >= 0.2 * r['current_n']:
                out.append(f)
        return out

    def threshold(self):
        if self.arm == 'thresh_relax_scoped' and self.inst is not None and self.inst.closed and self.inst.outcome == 'abandoned_unconfirmed':
            return 0.95
        return 0.8

    # ---- one decision tick -------------------------------------------
    def tick(self, obs, decision=None, evaluated=None, own_policy=None):
        t = obs['time_ns']; reports = {r['node']: r for r in obs['reports']}
        released = False
        if self.arm in ('post_exit', 'sham_release') and self.inst is not None and self.inst.closed \
                and self.inst.outcome == 'abandoned_unconfirmed' and self.pending is None:
            if not any(d == self.inst.decision for d in self.releases):
                self.releases.append(self.inst.decision)
            if self.arm == 'post_exit': self.inst = None; released = True
        if self.pending is not None and t >= self.pending + 10 * S: self.pending = None
        self._versions(reports); self._cache(t, reports)
        retry = self.inst.observe(t, reports) if self.inst is not None else []
        reason, worst = self.psi(t, reports, obs['timely_buckets'])
        fs = self.fs_eligible(t, reports)
        poor = reason == 'known' and worst < self.threshold()
        phi = bool(poor or fs)
        row = dict(t=t, reason=reason, worst=worst, fs=fs, phi=phi, released=released, retry=retry,
                   T=None if self.inst is None else (self.inst.outcome or 'waiting'))
        if own_policy is not None and decision is None:
            decision = own_policy(self, obs, row)
            evaluated = row.get('evaluated')
        row['evaluated'] = evaluated
        if decision is not None and t < self.action_stop:
            did, paths = decision
            self.seq += 1
            self.version_paths[did] = tuple(tuple(p) for p in paths); self.current = [tuple(p) for p in paths]
            self.inst = Installation(did, t, paths, self.wait_ns); self.installs.append(self.inst); self.pending = t
            row['install'] = did
        self.log.append(row)
        return row

    # ---- endpoints ----------------------------------------------------
    def exits(self):
        return sorted(i.exit_ns for i in self.installs if i.exit_ns is not None and not i.late)

    def e1(self, use_mask=True):
        ex = self.exits()
        if not ex: return False
        last = ex[-1]
        after = [r for r in self.log if last <= r['t'] < self.action_stop and (r['evaluated'] or not use_mask)]
        return bool(after) and all(r['reason'] == 'installation_unconfirmed' and 'install' not in r for r in after)

    def installs_after_first_exit(self):
        ex = self.exits()
        if not ex: return 0
        return sum(1 for r in self.log if ex[0] <= r['t'] < self.action_stop and 'install' in r)


# ---------------------------------------------------------------------------
# Mode F: abstract SimPy network
# ---------------------------------------------------------------------------
def phase_s(seed, i):
    if not seed: return 5.1 + i * .02
    m = (1 << 64) - 1
    z = (seed * 2654435761 + i * 11400714819323198485) & m
    z ^= z >> 29
    return 5.05 + (z % 950) / 1000.


def catalog(points):
    def paths(src):
        out = []
        def visit(p):
            if p[-1] == 9: out.append(tuple(p)); return
            if len(p) >= 7: return
            for n in sorted(points):
                if n not in p and n != 1 - src and math.dist(points[n], points[p[-1]]) <= 65: visit(p + [n])
        visit([src])
        L = lambda p: sum(math.dist(points[a], points[b]) for a, b in zip(p, p[1:]))
        return sorted(out, key=lambda p: (len(p), L(p), p))
    a, b = paths(0), paths(1)
    L = lambda ps: sum(math.dist(points[x], points[y]) for p in ps for x, y in zip(p, p[1:]))
    return sorted(((p, q) for p in a for q in b), key=lambda ps: (sum(len(p) for p in ps), L(ps), ps))


def monitor_path(n):
    if n == 5: return (5, 9)
    if n == 4: return (4, 5, 9)
    if n == 3: return (3, 5, 9)
    return (n, 4, 5, 9)


class Network:
    def __init__(self, env, rng, points, arrivals, faults, drop, calib, seed, generation_stop=330):
        import simpy  # noqa
        self.env = env; self.rng = rng; self.points = points; self.cal = calib
        self.alive = {n: True for n in points}; self.faults = faults; self.drop = drop
        self.version = {0: 0, 1: 0}; self.since = {0: 0, 1: 0}; self.path = {0: INITIAL[0], 1: INITIAL[1]}
        self.gen = {0: {}, 1: {}}; self.timely = {}; self.latest = {}
        self.hist = {0: [], 1: []}  # (end_ns, failed, version)
        self.last_emit = {n: 0 for n in points}; self.seed = seed; self.gstop = generation_stop
        env.process(self._faults()); env.process(self._arrivals(arrivals))
        for n in points:
            if n != 9: env.process(self._reports(n))

    def now(self): return int(round(self.env.now * S))

    def hop_ok(self, a, b, retries=0):
        if not (self.alive[a] and self.alive[b]): return False
        d = math.dist(self.points[a], self.points[b])
        k, d0 = self.cal['logit_k'], self.cal['logit_d0']
        p = 1 / (1 + math.exp(k * (d - d0)))
        p = 1 - (1 - p) ** (1 + retries)
        return self.rng.random() < p

    def _faults(self):
        for when, relay in sorted(self.faults):
            yield self.env.timeout(max(0, when - self.env.now)); self.alive[relay] = False

    def _arrivals(self, arrivals):
        for t, f in arrivals:
            yield self.env.timeout(max(0, t - self.env.now))
            now = self.now(); b = now // BUCKET
            self.gen[f][b] = self.gen[f].get(b, 0) + 1
            p = self.path[f]; ok = True; hops = 0
            for a, c in zip(p, p[1:]):
                good = self.hop_ok(a, c); hops += 1
                if a == f: self.hist[f].append((now, not good, self.version[f]))
                if not good: ok = False; break
            if ok and hops * self.cal['hop_latency_s'] <= 0.2:
                self.timely.setdefault(b, [0, 0])[f] += 1

    def _deliver(self, path, critical):
        for a, c in zip(path, path[1:]):
            if not self.hop_ok(a, c, retries=1 if critical else 0): return None
        return len(path) - 1

    def _reports(self, n):
        yield self.env.timeout(phase_s(self.seed, n))
        while self.env.now + 5. < self.gstop + 15:
            if self.alive[n]:
                now = self.now()
                if n < 2:
                    cur = [h for h in self.hist[n] if h[0] >= now - 20 * S and h[2] == self.version[n]]
                    failure = len(cur) >= 10 and sum(h[1] for h in cur) > 0.2 * len(cur)
                    urgent = now - self.since[n] < 15 * S or failure
                    period = 5 if urgent else 15
                else:
                    period = 15
                if self.last_emit[n] == 0 or now - self.last_emit[n] >= period * S:
                    self.last_emit[n] = now
                    hops = self._deliver(monitor_path(n), critical=n < 2)
                    if hops is not None:
                        b = now // BUCKET
                        rep = dict(node=n, stamp_ns=now, received_ns=now + int(hops * self.cal['hop_latency_s'] * S),
                                   version=self.version[n] if n < 2 else 0, period_s=period)
                        if n < 2:
                            cur = [h for h in self.hist[n] if h[0] >= now - 20 * S and h[2] == self.version[n]]
                            rep['current_n'] = len(cur); rep['current_failed'] = sum(h[1] for h in cur)
                            rep['epoch_first_bucket'] = -(-self.since[n] // BUCKET)
                            rep['buckets'] = [[U32, rep['epoch_first_bucket']]] + [[b - k, self.gen[n].get(b - k, 0)] for k in (1, 2, 3) if b - k >= 0]
                        else:
                            rep['buckets'] = []
                        self.latest[n] = rep
            yield self.env.timeout(5.)

    def send_install(self, decision, paths, targets):
        now = self.now(); t = now / S
        for f in targets:
            start, end, mask = self.drop
            if start >= 0 and t >= start and (end < 0 or t < end) and (mask >> f) & 1: continue
            hops = self._deliver((9, 5, 4, f), critical=False)
            if hops is not None and decision > self.version[f]:
                self.version[f] = decision; self.since[f] = now + int(hops * self.cal['hop_latency_s'] * S); self.path[f] = tuple(paths[f])

    def observation(self):
        t = self.now()
        reps = [r for r in self.latest.values() if r['received_ns'] <= t]
        return dict(time_ns=t, reports=reps, timely_buckets={str(b): list(v) for b, v in self.timely.items()})


def run_free(points, arrivals, faults, drop, arm, model, wait_s, calib, seed, rng, generation_stop=330):
    import simpy
    env = simpy.Environment(); net = Network(env, rng, points, arrivals, faults, drop, calib, seed, generation_stop)
    fsm = GateFSM(model=model, arm=arm, wait_s=wait_s, action_stop_ns=(generation_stop - 10) * S)
    cat = catalog(points)
    def policy(fsm_, obs, row):
        t = obs['time_ns']; reps = {r['node']: r for r in obs['reports']}
        relay_fresh = {n for n, r in reps.items() if n >= 2 and 0 <= t - r['stamp_ns'] <= 8 * S}
        used = {n for p in fsm_.current for n in p[1:-1]}
        if fsm_.seq == 0:
            row['evaluated'] = True; return (1, cat[0])
        if fsm_.pending is not None: row['evaluated'] = False; return None
        missing = bool(used - relay_fresh)
        ev = missing or row['phi']
        row['evaluated'] = ev
        if not ev or not row['phi']: return None
        if fsm_.inst is not None and not fsm_.inst.closed:
            return None  # installation wait in progress
        if fsm_.inst is not None and fsm_.inst.outcome != 'confirmed' and not row['fs']:
            return None  # T unconfirmed and no eligible F_s: Prop. 1 (Phi would be 0 anyway)
        for pair in cat:
            if all(n in relay_fresh for p in pair for n in p[1:-1]):
                return (fsm_.seq + 1, pair)
        return None
    def driver():
        yield env.timeout(10.)
        while env.now + 5. < generation_stop + 15 + 1e-9:
            obs = net.observation()
            row = fsm.tick(obs, own_policy=policy)
            for f in row.get('retry', []):
                net.send_install(fsm.inst.decision, fsm.inst.paths, [f])
            if 'install' in row:
                net.send_install(row['install'], fsm.inst.paths, [0, 1])
            yield env.timeout(5.)
    env.process(driver()); env.run(until=generation_stop + 20)
    return fsm
