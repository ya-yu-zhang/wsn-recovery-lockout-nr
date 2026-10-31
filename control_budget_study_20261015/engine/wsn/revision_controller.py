"""Development revision: distinct objectives and settled visible service."""
import time
from wsn.controller import OriginalController
from wsn.feedback import ClosedBucketCache,BUCKET_NS
from wsn.operator_search import search_operator

class RevisionController(OriginalController):
    def __init__(self,policy,*args,**kwargs):
        super().__init__(policy,*args,**kwargs)
        self.service_cache=ClosedBucketCache();self.visible_versions={0:0,1:0};self.version_since={0:0,1:0}
        self.domain_cache={};self.service_evidence={'known':False,'reason':'unobserved'}
        # Factory selects this class only for the explicit _ops_ revision.
        self.search_mode='scalar';self.pair_masks=[sum(1<<n for n in set(ps[0])|set(ps[1])) for ps in self.catalog]
        if '_ctx6_' in policy:
            from wsn.base_controller import LinUCB,InterceptLinUCB
            if '_low4_' in policy:
                raise ValueError('ctx6 cannot use the legacy four-feature projection')
            self.bandit=(InterceptLinUCB if self.selection_mode=='intercept' else LinUCB)(d=6)

    def service_view(self,obs,fresh):
        self.service_cache.observe(obs);t=obs['time_ns']
        if '_epoch_' in self.policy:
            for f in (0,1):
                r=fresh.get(f)
                if r is not None:
                    anchor=r.get('epoch_first_bucket')
                    if type(anchor) is not int or anchor<0 or anchor*BUCKET_NS>r['stamp_ns']+BUCKET_NS:
                        raise ValueError('invalid received version epoch certificate')
                    if r['buckets'][0]!=[2**32-1,anchor]:raise ValueError('wire epoch marker mismatch')
                    self.visible_versions[f]=r['version'];self.version_since[f]=anchor*BUCKET_NS

        for f in (0,1):
            r=fresh.get(f)
            if r is not None and r['version']!=self.visible_versions[f]:
                self.visible_versions[f]=r['version'];self.version_since[f]=r['stamp_ns']
        if any(f not in fresh for f in (0,1)):return {'known':False,'reason':'missing_fresh_source'}
        if self.installation is not None and (not self.installation.closed or self.installation.outcome!='confirmed'):
            return {'known':False,'reason':'installation_unconfirmed'}
        if any(fresh[f]['version'] not in self.version_paths or self.version_paths[fresh[f]['version']][f]!=self.current[f] for f in (0,1)):
            return {'known':False,'reason':'unknown_installed_version'}
        bound=max(self.version_since.values());last=t//BUCKET_NS-1
        buckets=[b for b in range(max(0,last-2),last+1) if b*BUCKET_NS>=bound and (b+1)*BUCKET_NS+200_000_000<=t]
        if not buckets:return {'known':False,'reason':'no_settled_same_version_bucket'}
        counts,proof,missing=self.service_cache.cohort(buckets)
        if any(missing) or len(counts)!=2 or min(counts)<20:
            return {'known':False,'reason':'incomplete_or_sparse_generation_evidence','buckets':buckets,'counts':counts,'missing':missing}
        timely=[sum(obs['timely_buckets'].get(str(b),[0,0])[f] for b in buckets) for f in (0,1)]
        if any(not 0<=n<=d for n,d in zip(timely,counts)):raise ValueError('inconsistent settled service')
        rates=[n/d for n,d in zip(timely,counts)]
        return dict(known=True,buckets=buckets,offered=counts,timely=timely,probabilities=rates,worst_timely=min(rates),
            earliest_current_version_ns=bound,version_by_source={str(k):v for k,v in self.visible_versions.items()},bucket_evidence=proof,
            scope='received closed generation counts and sink-local timely deliveries; conditional on observed versions')

    def view(self,obs):
        reports,fresh,active,x,event=super().view(obs)
        self.service_evidence=self.service_view(obs,fresh)
        event['settled_service']=self.service_evidence
        event['poor_settled_service']=self.service_evidence.get('known',False) and self.service_evidence['worst_timely']<.8
        event['trigger_failure']=event['trigger_failure'] or event['poor_settled_service']
        known=self.service_evidence.get('known',False)
        if '_ctx6_' in self.policy:
            # A masked service value and an explicit missingness indicator form
            # a pair. Queue always retains its original observed-queue meaning.
            x=x[:4]+[1-self.service_evidence['worst_timely'] if known else 0.,0. if known else 1.]
            event['context_schema']='stable6-v1'
        else:
            x[3]=1-self.service_evidence['worst_timely'] if known else min(event['source_queue']/16,1)
        return reports,fresh,active,x,event

    def constraint_view(self,active,t):
        start=time.perf_counter_ns();mask=sum(1<<n for n in active);checks=0
        if mask not in self.domain_cache:
            good=[]
            for ps,bits in zip(self.catalog,self.pair_masks):
                checks+=1
                if bits&mask==bits:good.append(ps)
            # Geometry-only round-robin among first-relay groups retains low-hop
            # alternatives before long detours; no proxy score evaluated here.
            groups={}
            for ps in good:groups.setdefault((ps[0][1],ps[1][1]),[]).append(ps)
            pool=[];keys=sorted(groups)
            index=0
            while len(pool)<64:
                added=False
                for key in keys:
                    if index<len(groups[key]):pool.append(groups[key][index]);added=True
                    if len(pool)==64:break
                if not added:break
                index+=1
            self.domain_cache[mask]=tuple(pool)
        pool=list(self.domain_cache[mask]);checks+=1
        retained=[]
        for ps in [self.current]+list(reversed(self.memory))[:8]:
            checks+=1
            if all(n in active for p in ps for n in p) and ps not in retained:retained.append(ps)
        pool=(retained+[ps for ps in pool if ps not in retained])[:64]
        available=[bool(pool)]*4
        row=dict(time_ns=t,available=available,witnesses={str(a):pool[0] if pool else None for a in range(4)},
            candidate_pair_freshness_checks=checks,unselected_objective_evaluations=0,constraint_wall_ns=time.perf_counter_ns()-start,
            domain_rule='geometry relay-group round robin; cached by visible active mask',pool_size=len(pool))
        self.constraint_logs.append(row);return {a:pool for a in range(4)},row

    def search_candidates(self,action,candidates,fresh,active):
        return search_operator(action,candidates,fresh,active,self.points,self.current,self.service_evidence)

    def hold_admission(self,obs,proposal):
        reports,fresh,active,x,event=self.view(obs)
        if any(f not in fresh for f in (0,1)):return False,'missing_fresh_source'
        if proposal!=self.current:return False,'route_changed'
        if any(n not in active for p in proposal for n in p):return False,'route_not_observably_feasible'
        if self.installation is not None and (not self.installation.closed or self.installation.outcome!='confirmed'):
            return False,'installation_not_confirmed'
        if any(fresh[f]['version'] not in self.version_paths or self.version_paths[fresh[f]['version']][f]!=proposal[f] for f in (0,1)):
            return False,'unknown_installed_version'
        # Idempotence requires known installed paths, not a false claim that MAC
        # success proves end-to-end health. Poor service affects route search.
        return True,'identical_observably_installed_route'

