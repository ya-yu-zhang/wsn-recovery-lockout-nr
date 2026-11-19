"""Registered lockout descriptors computed from one controller transcript.

Definitions (frozen in PROTOCOL.md before any SIMPAT-stage outcome was seen):

* unconfirmed exit: an installation row whose outcome first becomes
  ``abandoned_unconfirmed`` (the bounded wait ended without both confirmations).
* evaluated check: a post-bootstrap step at which the controller reached the
  evidence-qualified admission predicate (``constraints.evidence_qualified_admission``).
* rejected check: an evaluated check with ``allowed`` false.
* post-exit window: from an unconfirmed exit to the next route decision, or to
  the action stop when no further decision occurs.
* broad lockout (L_broad): some post-exit window reaches the action stop with no
  route decision, no confirmation of that transaction (late or otherwise) and at
  least one rejected check.
* strict lockout (L_strict): L_broad, and every evaluated check in that window
  is rejected while the settled-service reason is ``installation_unconfirmed``,
  with at least three such checks.
"""


def _reason(step):
    s = (step.get('event') or {}).get('settled_service') or {}
    return s.get('reason') if not s.get('known') else 'known'


def describe(steps, action_stop_ns, contract_releases=()):
    exits = []
    for i, s in enumerate(steps):
        inst = s.get('installation')
        if inst and inst.get('outcome') == 'abandoned_unconfirmed' and inst.get('closed') \
                and not inst.get('late_confirmation'):
            if not exits or exits[-1]['decision'] != inst['decision']:
                exits.append(dict(index=i, decision=inst['decision'], time_ns=s['observation']['time_ns']))
    decisions = [(i, s['decision']) for i, s in enumerate(steps) if s.get('decision') and s['decision'].get('paths')]
    late = {s['installation']['decision'] for s in steps
            if s.get('installation') and s['installation'].get('late_confirmation')}
    windows = []
    for e in exits:
        nxt = next((i for i, d in decisions if i > e['index']), None)
        end = nxt if nxt is not None else len(steps)
        checks = rejected = unconfirmed_rejected = 0
        reasons = {}
        for s in steps[e['index']:end]:   # the exit step's own admission check belongs to the window
            if s['observation']['time_ns'] >= action_stop_ns:
                break
            adm = (s.get('constraints') or {}).get('evidence_qualified_admission')
            if adm is None:
                continue
            checks += 1
            r = _reason(s)
            reasons[r] = reasons.get(r, 0) + 1
            if not adm['allowed']:
                rejected += 1
                if r == 'installation_unconfirmed':
                    unconfirmed_rejected += 1
        to_stop = nxt is None or steps[nxt]['observation']['time_ns'] >= action_stop_ns
        broad = to_stop and e['decision'] not in late and rejected >= 1
        strict = broad and checks >= 3 and unconfirmed_rejected == checks
        windows.append(dict(exit_time_s=e['time_ns'] / 1e9, decision=e['decision'],
                            next_decision_time_s=(steps[nxt]['observation']['time_ns'] / 1e9 if nxt is not None else None),
                            evaluated_checks=checks, rejected_checks=rejected,
                            rejected_installation_unconfirmed=unconfirmed_rejected,
                            settled_service_reasons=reasons, late_confirmation=e['decision'] in late,
                            reaches_action_stop=to_stop, broad_lockout=broad, strict_lockout=strict))
    post_bootstrap_decisions = sum(1 for _, d in decisions if d['decision'] > 1)
    return dict(unconfirmed_exits=len(exits), windows=windows,
                broad_lockout=any(w['broad_lockout'] for w in windows),
                strict_lockout=any(w['strict_lockout'] for w in windows),
                route_decisions=len(decisions), post_bootstrap_route_decisions=post_bootstrap_decisions,
                contract_releases=len(contract_releases),
                first_release_s=(contract_releases[0]['time_ns'] / 1e9 if contract_releases else None))
