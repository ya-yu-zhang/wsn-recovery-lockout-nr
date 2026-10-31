"""Confirmation from received version reports, never simulator install truth."""
class Installation:
    def __init__(self,decision,time_ns,paths,retry_limit):
        self.decision=decision;self.time_ns=time_ns;self.paths=paths;self.retry_limit=retry_limit
        self.attempts=[0,0];self.confirmations={};self.closed=False;self.outcome=None;self.history=[]
    def observe(self,obs):
        if self.closed:return None
        t=obs['time_ns'];fresh={r['node']:r for r in obs['reports'] if r['node']<2 and t-r['stamp_ns']<=8_000_000_000}
        for f,r in fresh.items():
            if not r['stamp_ns']<=r['received_ns']<=t:raise ValueError('future confirmation')
            if r['stamp_ns']>=self.time_ns and r['version']==self.decision and f not in self.confirmations:
                self.confirmations[f]=dict(assessed_ns=t,stamp_ns=r['stamp_ns'],received_ns=r['received_ns'],version=r['version'])
        missing=[f for f in (0,1) if f not in self.confirmations];targets=[]
        if not missing:self.closed=True;self.outcome='confirmed'
        elif t>=self.time_ns+15_000_000_000:self.closed=True;self.outcome='confirmation_timeout'
        elif t>=self.time_ns+5_000_000_000:
            targets=[f for f in missing if self.attempts[f]<self.retry_limit and t>=self.time_ns+(self.attempts[f]+1)*5_000_000_000]
            for f in targets:self.attempts[f]+=1
        row=dict(decision=self.decision,time_ns=t,missing_sources=missing,retry_sources=targets,retry_counts=list(self.attempts),
            confirmations={str(k):v for k,v in sorted(self.confirmations.items())},closed=self.closed,outcome=self.outcome)
        self.history.append(row);return row
