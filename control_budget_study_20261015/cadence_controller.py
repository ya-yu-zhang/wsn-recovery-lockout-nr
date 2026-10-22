"""Same-version received cohorts with explicit bounded observation age."""
from budget_controller import BudgetController
NS=1_000_000_000
B=5*NS

class CohortController(BudgetController):
    def service_view(self,obs,fresh):
        original=super().service_view(obs,fresh)
        if original.get('known')or original.get('reason')!='incomplete_or_sparse_generation_evidence':return original
        t=obs['time_ns'];bound=max(self.version_since.values())
        available={b for f,b in self.service_cache.entries if f==0 and b*B>=bound and (b+1)*B+200_000_000<=t and t-(b+1)*B<=20*NS}
        for end in sorted(available,reverse=True):
            buckets=[end-1,end]
            if any(b not in available for b in buckets):continue
            counts,proof,missing=self.service_cache.cohort(buckets)
            if any(missing)or len(counts)!=2 or min(counts)<20:continue
            timely=[sum(obs['timely_buckets'].get(str(b),[0,0])[f]for b in buckets)for f in(0,1)]
            assert all(0<=n<=d for n,d in zip(timely,counts))
            rates=[n/d for n,d in zip(timely,counts)]
            return dict(known=True,buckets=buckets,offered=counts,timely=timely,probabilities=rates,worst_timely=min(rates),earliest_current_version_ns=bound,version_by_source={str(k):v for k,v in self.visible_versions.items()},bucket_evidence=proof,cohort_end_age_ns=t-(end+1)*B,cohort_policy='latest_received_consecutive_pair_max20s',scope='historical same-version received cohort; not unobserved current service')
        return original

class ClosingController(CohortController):
    def assess_safety(self,obs):
        e=super().assess_safety(obs)
        s=self.service_evidence
        if e['reason']is None and s.get('known')and s['worst_timely']<.8:
            e['reason']='qualified_service_deficit';e['service_cohort']=s
        return e
    def interrupt_feedback(self,obs,evidence):
        if evidence['reason']=='qualified_service_deficit'and self.pending is not None:
            s=evidence['service_cohort']
            if min(s['buckets'])*B<self.pending['time_ns']:return None
        return super().interrupt_feedback(obs,evidence)
