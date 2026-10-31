"""Counts completed source application MAC jobs by their immutable packet version.

Integration hooks must use source installation receipts and the native Job's
generation-version field. Do not pass the controller's desired version here.
"""
from collections import deque
from dataclasses import dataclass
import struct

NS=1_000_000_000
U32=(1<<32)-1

def integer(value,name,maximum=None):
    if type(value) is not int or value<0 or (maximum is not None and value>maximum):
        raise ValueError('invalid '+name)
    return value

@dataclass(frozen=True)
class Completion:
    node:int
    flow:int
    sequence:int
    generation_version:int
    generated_ns:int
    end_ns:int
    status:int

@dataclass(frozen=True)
class Snapshot:
    source:int
    stamp_ns:int
    installed_version:int
    current_n:int
    current_failed:int
    mixed_n:int
    mixed_failed:int

    def counter_bytes(self):
        """Two network-order uint32s; version uses existing report version field."""
        if self.current_failed>self.current_n:raise ValueError('failed exceeds n')
        return struct.pack('>II',integer(self.current_n,'current_n',U32),
                           integer(self.current_failed,'current_failed',U32))

class SourceHistory:
    def __init__(self,source,window_ns=20*NS):
        self.source=integer(source,'source')
        self.window_ns=integer(window_ns,'window_ns')
        if not self.window_ns:raise ValueError('zero window')
        self.installed_version=0;self.clock=0;self.history=deque();self.seen=set()
        self.version_intervals={0:[0,None]}

    def _clock(self,now):
        integer(now,'time')
        if now<self.clock:raise ValueError('source-local time moved backwards')
        self.clock=now
        while self.history and self.history[0].end_ns<now-self.window_ns:
            self.history.popleft()

    def installation_received(self,version,now):
        integer(version,'version',U32);self._clock(now)
        if version<=self.installed_version:return False
        self.version_intervals[self.installed_version][1]=now
        self.version_intervals[version]=[now,None]
        self.installed_version=version
        # Keep old in-flight jobs and mixed history. Filtering occurs at sample time.
        return True

    def completed(self,job):
        # Forwarded jobs, installation/report traffic, and other nodes are not
        # source application evidence. Admission drops never invoke this hook.
        if job.node!=self.source or job.flow!=self.source:return False
        integer(job.sequence,'sequence');integer(job.generation_version,'generation_version',U32)
        integer(job.generated_ns,'generated_ns');integer(job.end_ns,'end_ns');integer(job.status,'status')
        if job.generated_ns>job.end_ns:raise ValueError('completion predates generation')
        if job.generation_version>self.installed_version:raise ValueError('unobserved future generation version')
        interval=self.version_intervals.get(job.generation_version)
        if interval is None or job.generated_ns<interval[0] or (interval[1] is not None and job.generated_ns>interval[1]):
            raise ValueError('packet generation does not match actual installation interval')
        if job.sequence in self.seen:raise ValueError('duplicate terminal MAC job')
        self._clock(job.end_ns);self.seen.add(job.sequence);self.history.append(job);return True

    def snapshot(self,now):
        self._clock(now)
        current=[x for x in self.history if x.generation_version==self.installed_version]
        return Snapshot(self.source,now,self.installed_version,len(current),
            sum(x.status!=0 for x in current),len(self.history),sum(x.status!=0 for x in self.history))

def decode_counter_bytes(payload):
    if not isinstance(payload,bytes) or len(payload)!=8:raise ValueError('current-counter payload must be8bytes')
    n,failed=struct.unpack('>II',payload)
    if failed>n:raise ValueError('failed exceeds n')
    return n,failed

@dataclass(frozen=True)
class Event:
    eligible:bool
    reason:str
    sampled_version:int|None
    n:int|None
    failed:int|None
    fraction:float|None

def assess_report(report,now,mode='current',minimum=20,threshold=.2,max_age_ns=8*NS):
    """Gate only; never substitutes missing counters with mixed history or zero."""
    if mode not in ('current','mixed'):raise ValueError('unknown counter mode')
    integer(now,'time');integer(minimum,'minimum');integer(max_age_ns,'max_age')
    if minimum<1 or not 0<=threshold<=1:raise ValueError('invalid threshold')
    stamp=integer(report['stamp_ns'],'stamp_ns');received=integer(report['received_ns'],'received_ns')
    version=integer(report['version'],'version',U32)
    if not stamp<=received<=now:return Event(False,'invalid_time',version,None,None,None)
    if now-stamp>max_age_ns:return Event(False,'stale',version,None,None,None)
    names=('current_n','current_failed') if mode=='current' else ('n','failed')
    if any(k not in report for k in names):return Event(False,'counter_unavailable',version,None,None,None)
    n=integer(report[names[0]],names[0],U32);failed=integer(report[names[1]],names[1],U32)
    if failed>n:raise ValueError('failed exceeds n')
    fraction=failed/n if n else None
    if n<minimum:return Event(False,'insufficient_current_samples' if mode=='current' else 'insufficient_mixed_samples',version,n,failed,fraction)
    hit=fraction>=threshold
    return Event(hit,'failure_event' if hit else 'below_threshold',version,n,failed,fraction)
