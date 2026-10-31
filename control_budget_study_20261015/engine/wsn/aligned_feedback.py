"""Received version-qualified buckets. No native installation truth is accepted."""
from wsn.feedback import BUCKET_NS,RETENTION_NS,U32

class VersionBucketCache:
 def __init__(self):self.entries={};self.clock=0
 def observe(self,obs):
  t=obs['time_ns']
  if type(t)is not int or t<self.clock:raise ValueError('invalid cache clock')
  self.clock=t;self.entries={k:v for k,v in self.entries.items()if(k[2]+1)*BUCKET_NS>=t-RETENTION_NS}
  for r in obs['reports']:
   if r['node']not in(0,1):continue
   if not r['stamp_ns']<=r['received_ns']<=t:raise ValueError('future version evidence')
   anchor=r.get('epoch_first_bucket')
   if type(anchor)is not int or anchor<0 or r['buckets'][0]!=[U32,anchor]:raise ValueError('invalid version certificate')
   if anchor*BUCKET_NS>r['stamp_ns']+BUCKET_NS:raise ValueError('future epoch certificate')
   for b,n in r['buckets']:
    if type(b)is not int or type(n)is not int or not 0<=n<=U32:raise ValueError('invalid bucket')
    if b==U32 or b<anchor or(b+1)*BUCKET_NS>r['stamp_ns']or(b+1)*BUCKET_NS<t-RETENTION_NS:continue
    key=(r['node'],r['version'],b)
    proof=dict(source=r['node'],version=r['version'],epoch_first_bucket=anchor,bucket=b,count=n,stamp_ns=r['stamp_ns'],received_ns=r['received_ns'],visible_ns=t)
    if key in self.entries:
     if self.entries[key]['count']!=n or self.entries[key]['epoch_first_bucket']!=anchor:raise ValueError('conflicting version bucket')
    else:self.entries[key]=proof
 def cohort(self,versions,bucket):
  evidence=[dict(self.entries[f,versions[f],bucket])for f in(0,1)if(f,versions[f],bucket)in self.entries]
  missing=[f for f in(0,1)if(f,versions[f],bucket)not in self.entries]
  counts=[self.entries[f,versions[f],bucket]['count']for f in(0,1)]if not missing else[]
  return counts,evidence,missing
