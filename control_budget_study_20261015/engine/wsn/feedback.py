"""Bounded cache of closed, actually received source generation buckets."""
BUCKET_NS=5_000_000_000
RETENTION_NS=60_000_000_000
U32=(1<<32)-1

class ClosedBucketCache:
    def __init__(self):
        self.entries={};self.clock=0

    def observe(self,obs):
        t=obs['time_ns']
        if type(t) is not int or t<self.clock:raise ValueError('invalid cache clock')
        self.clock=t
        cutoff=t-RETENTION_NS
        self.entries={key:value for key,value in self.entries.items() if (key[1]+1)*BUCKET_NS>=cutoff}
        for r in obs['reports']:
            if not r['stamp_ns']<=r['received_ns']<=t:raise ValueError('future cache observation')
            f=r['node']
            if f not in (0,1):continue
            for b,n in r['buckets']:
                if type(b) is not int or type(n) is not int or not 0<=b<=U32 or not 0<=n<=U32:raise ValueError('invalid generation bucket')
                if b==U32 or (b+1)*BUCKET_NS>r['stamp_ns'] or (b+1)*BUCKET_NS<cutoff:continue
                key=(f,b)
                if key in self.entries:
                    if self.entries[key]['count']!=n:raise ValueError('conflicting closed generation count')
                    continue
                self.entries[key]=dict(source=f,bucket=b,count=n,stamp_ns=r['stamp_ns'],received_ns=r['received_ns'],visible_ns=t)

    def cohort(self,buckets):
        counts=[];evidence=[];missing=[]
        for f in (0,1):
            absent=[b for b in buckets if (f,b) not in self.entries];missing.append(absent)
            evidence.extend(dict(self.entries[f,b]) for b in buckets if (f,b) in self.entries)
            if absent or len(counts)!=f:continue
            counts.append(sum(self.entries[f,b]['count'] for b in buckets))
        return counts,evidence,missing
