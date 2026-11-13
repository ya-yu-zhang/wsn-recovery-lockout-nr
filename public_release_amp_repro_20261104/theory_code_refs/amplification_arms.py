"""Amplification-stage arms (written 2026-11-03 before any amplification run).

All arms share the Horizon controller (HorizonController) and change exactly one
rule relative to Joint.  Arms:
  joint        implemented global confirmation contract (baseline, unchanged)
  post_exit    releases premise T only (identical rule to contract_ablation.PostExitMixin)
  sham_release computes the PostExit release condition and logs it, but does NOT
               release (no-op control for timing/bookkeeping artefacts)
  fs_relax_global / fs_relax_scoped
               competing relaxation of the failure-evidence predicate F_s only:
               a fresh current-version source report with n>=5 and failed/n>=0.10
               counts as positive recovery evidence (registered rule: n>=20, >=0.20)
  thresh_relax_global / thresh_relax_scoped
               competing relaxation of the service predicate only: settled worst-source
               timeliness < 0.95 (registered rule: < 0.80) counts as positive evidence
  wait_extend  competing timing hypothesis: bounded installation wait 20 s instead of
               10 s (more time for a confirmation to arrive); T itself unchanged
  *_global applies the relaxed predicate at every admission check; *_scoped applies it
  only while the current installation has exited unconfirmed (the T-blocked window),
  so the pre-exit trajectory is identical to Joint.
No wire format, native code, byte budget, report schedule or other threshold changes.
"""
from horizon_controller import HorizonController
from contract_ablation import PostExitMixin

class ArmMixin:
    ARM='joint'
    def __init__(self,*a,arm='joint',**k):
        self.arm=arm;self.arm_events=[]
        super().__init__(*a,**k)
        if arm=='wait_extend':self.install_exit_ns=20_000_000_000
    def _release_condition(self):
        inst=self.installation
        return inst is not None and inst.closed and inst.outcome=='abandoned_unconfirmed' and self.pending is None
    def step(self,obs):
        if self.arm in('post_exit','sham_release') and self._release_condition():
            inst=self.installation
            if not any(e['released_decision']==inst.decision for e in self.arm_events):
                self.arm_events.append(dict(time_ns=obs['time_ns'],released_decision=inst.decision,applied=self.arm=='post_exit',
                    missing_sources=[f for f in(0,1)if f not in inst.confirmations]))
            if self.arm=='post_exit':self.installation=None
        return super().step(obs)
    def _relaxed_failure(self):
        ev=self.safety_evidence or {}
        for d in (ev.get('source_failure_reports')or{}).values():
            if d.get('fresh') and d.get('n') is not None and d['n']>=5 and d.get('fraction') is not None and d['fraction']>=.10:return True
        return False
    def _scope_ok(self):
        if self.arm.endswith('_global'):return True
        inst=self.installation
        return inst is not None and inst.closed and inst.outcome=='abandoned_unconfirmed'
    def positive_recovery_evidence(self):
        base=super().positive_recovery_evidence()
        if self.arm.startswith('fs_relax') and self._scope_ok():return bool(base or self._relaxed_failure())
        if self.arm.startswith('thresh_relax') and self._scope_ok():
            return bool(base or (self.service_evidence.get('known',False) and self.service_evidence['worst_timely']<.95))
        return base

class AmplifiedHorizon(ArmMixin,HorizonController):pass
