"""Independent measured-observation controller; no original phase2 imports."""
from itertools import product
import math,time
from functools import lru_cache
import numpy as np

POINTS={0:(0,0),1:(0,4),2:(40,0),3:(80,0),4:(40,35),5:(80,35),6:(60,-35),7:(100,-35),8:(20,-35),9:(120,0)}
INITIAL=((0,2,3,9),(1,2,3,9));FRESH_NS=8_000_000_000


def all_paths(source,points=None):
    points=POINTS if points is None else points
    if len(points)>10:
        import heapq
        queue=[(0,0.,(source,))];completed=[];expanded=0
        while queue and len(completed)<32 and expanded<100000:
            hops,length,path=heapq.heappop(queue);expanded+=1
            if path[-1]==9:completed.append(path);continue
            if len(path)>=7:continue
            for n in sorted(points):
                d=math.dist(points[n],points[path[-1]])
                if n not in path and n!=1-source and d<=65:
                    heapq.heappush(queue,(hops+1,length+d,path+(n,)))
        return completed
    out=[]
    def visit(path):
        if path[-1]==9:out.append(tuple(path));return
        if len(path)>=7:return
        for n in sorted(points):
            if n not in path and n not in (1-source,) and math.dist(points[n],points[path[-1]])<=65:visit(path+[n])
    visit([source]);return sorted(out,key=lambda p:(len(p),sum(math.dist(points[a],points[b]) for a,b in zip(p,p[1:])),p))

@lru_cache(maxsize=8)
def catalog_for(signature):
    points=dict(signature)
    return tuple(sorted(product(all_paths(0,points),all_paths(1,points)),key=lambda ps:(sum(len(p) for p in ps),sum(math.dist(points[a],points[b]) for p in ps for a,b in zip(p,p[1:])),ps)))
CATALOG=catalog_for(tuple(sorted(POINTS.items())))



class LinUCB:
    def __init__(self,d=9,alpha=.6):self.A=np.repeat(np.eye(d)[None,:,:],4,axis=0);self.b=np.zeros((4,d));self.alpha=alpha;self.updates=[0]*4
    def scores(self,x):
        x=np.asarray(x);out=[]
        for a in range(4):
            invx=np.linalg.solve(self.A[a],x);out.append(float(self.b[a]@invx+self.alpha*math.sqrt(max(0.,x@invx))))
        return out
    def select(self,x):return int(np.argmax(self.scores(x)))
    def update(self,a,x,reward):
        x=np.asarray(x);self.A[a]+=np.outer(x,x);self.b[a]+=reward*x;self.updates[a]+=1

class InterceptLinUCB(LinUCB):
    def scores(self,x):return super().scores([x[0]]+[0.]*(len(x)-1))
    def update(self,a,x,reward):return super().update(a,[x[0]]+[0.]*(len(x)-1),reward)

class Low4LinUCB(LinUCB):
    """Physical 4D model using the predeclared first four observable features."""
    def __init__(self):super().__init__(d=4)
    def scores(self,x):return super().scores(x[:4])
    def update(self,a,x,reward):return super().update(a,x[:4],reward)


class Controller:
    def __init__(self,policy,report_profile='full5',points=None,action_stop_ns=80_000_000_000,selection_seed=0):
        self.points={int(k):tuple(v) for k,v in (POINTS if points is None else points).items()}
        if not 10<=len(self.points)<=64 or set(self.points)!=set(range(len(self.points))) or any(not math.isfinite(v) for xy in self.points.values() for v in xy):raise ValueError('invalid known geometry')
        self.catalog=catalog_for(tuple(sorted(self.points.items())))
        if report_profile not in ('full5','hybrid5_10','path_priority16','path_priority','lease10_20','lease10_15','local15_event'):raise ValueError(report_profile)
        self.report_profile=report_profile;self.is_bandit=policy.startswith('linucb');self.masked=policy.endswith('_mask') or policy=='linucb_mask';self.warmup_attempts=[];self.event_attempts=[];self.constraint_logs=[]
        if '_freshfixed_' in policy and '_freshscaled_' in policy:
            raise ValueError('freshness treatments must be mutually exclusive')
        self.search_mode='pareto' if '_pareto' in policy else 'scalar' if '_scalar' in policy else 'legacy'
        self.exploration_cap=next((int(v) for v in (0,2,4) if f'_pareto{v}_' in policy or f'_scalar{v}_' in policy),4)
        self.policy=policy;self.bandit=LinUCB();self.memory=[INITIAL];self.current=INITIAL;self.version_paths={0:INITIAL};self.pending=None;self.sequence=0;self.logs=[];self.feedbacks=[];self.last_pdr=1.;self.last_decision=-1
        if not isinstance(action_stop_ns,int) or action_stop_ns<10_000_000_000:raise ValueError('invalid action cutoff')
        self.action_stop_ns=action_stop_ns;self.selection_seed=selection_seed
        self.selection_mode=('random' if '_random_' in policy else 'frozen' if '_frozen_' in policy else 'intercept' if '_intercept_' in policy else 'low4' if '_low4_' in policy else 'full')
        self.train_bandit=self.selection_mode!='frozen'
        if self.selection_mode=='intercept':self.bandit=InterceptLinUCB()
        if self.selection_mode=='low4':self.bandit=Low4LinUCB()
    def fresh_limit(self,node,report):
        if node<2:return FRESH_NS
        if '_freshfixed_' in self.policy:return 16_000_000_000
        if '_freshscaled_' in self.policy:
            period=report.get('period_s')
            if period not in (5,10,15,20):raise ValueError('invalid advertised reporting period')
            return period*1_600_000_000
        if self.report_profile in ('hybrid5_10','path_priority16'):return 16_000_000_000
        if self.report_profile in ('path_priority','lease10_20','lease10_15'):return int(report.get('period_s',5)*1.6*1e9)
        return FRESH_NS
    def view(self,obs):
        t=obs['time_ns'];reports={r['node']:r for r in obs['reports']}
        for r in reports.values():
            if not r['stamp_ns']<=r['received_ns']<=t:raise ValueError('future observation')
        for f in range(2):
            if f in reports and reports[f]['version'] in self.version_paths:
                p=list(self.current);p[f]=self.version_paths[reports[f]['version']][f];self.current=tuple(p)
        if self.current not in self.memory:self.memory.append(self.current)
        fresh={n:r for n,r in reports.items() if t-r['stamp_ns']<=self.fresh_limit(n,r)};active=set(fresh)|{9}
        states={str(n):('unknown' if n not in reports else 'fresh' if n in fresh else 'expired') for n in self.points if n!=9}
        used=set(n for p in self.current for n in p[:-1]);missing=len(used-active)/max(1,len(used))
        busy=sum(r['busy'] for r in fresh.values())/max(1,sum(r['cca'] for r in fresh.values()))
        sourceq=max((fresh.get(f,{}).get('depth',0) for f in (0,1)),default=0)
        meanJ=sum(r['mean_J_ns'] for r in fresh.values())/max(1,len(fresh))/1e9
        counts=[]
        for f in (0,1):
            buckets=dict(fresh.get(f,{}).get('buckets',[]));counts.append(buckets.get(max(0,t//5_000_000_000-1),0)/5)
        x=[1.,missing,busy,min(sourceq/16,1),min(meanJ/.05,1),min(math.log1p(max(counts))/math.log(81),1),self.last_pdr,min(len(self.memory)/8,1),len(fresh)/(len(self.points)-1)]
        return reports,fresh,active,x,dict(missing=missing,busy=busy,source_queue=sourceq,observation_states=states,missing_means='unobserved or expired, not confirmed physical failure')
    def feedback(self,obs,reports):
        p=self.pending
        if p is None or obs['time_ns']<p['time_ns']+10_000_000_000:return None
        counts=[];reason=None
        for f in (0,1):
            r=reports.get(f)
            if r is None or r['stamp_ns']<p['time_ns']+5_000_000_000:reason='source report missing or sampled before cohort end';break
            buckets=dict(r['buckets'])
            if p['bucket'] not in buckets:reason='feedback cohort absent from report';break
            counts.append(buckets[p['bucket']])
        timely=obs['timely_buckets'].get(str(p['bucket']),[0,0]);reward=None;probs=None
        if reason is None and len(counts)==2 and all(counts):
            probs=[d/n for d,n in zip(timely,counts)]
            if any(v<0 or v>1 for v in probs):raise ValueError('inconsistent received feedback')
            fee=1998 if p['paths'] else 0
            reward=.75*sum(probs)/2+.25*min(probs)-.05*min(p['fe']/64,1)-.05*min(fee/1998,1)
            self.last_pdr=sum(probs)/2
            if self.is_bandit and self.train_bandit:self.bandit.update(p['action'],p['context'],reward)
        elif reason is None:reason='empty offered cohort'
        row=dict(decision=p['decision'],action=p['action'],time_ns=obs['time_ns'],cohort_start_ns=p['time_ns'],cohort_end_ns=p['time_ns']+5_000_000_000,
                 offered=counts,timely=timely,probabilities=probs,reward=reward,missing_reason=reason,updated_action=p['action'] if reward is not None and self.is_bandit and self.train_bandit else None,
                 inputs=[r for f in (0,1) if (r:=reports.get(f)) is not None])
        self.feedbacks.append(row);self.pending=None;return row
    def score(self,paths,fresh,active):
        if any(n not in active for p in paths for n in p):return None
        length=sum(math.dist(self.points[a],self.points[b]) for p in paths for a,b in zip(p,p[1:]))/400
        queues=sum(fresh.get(n,{}).get('depth',0)/16 for p in paths for n in p[:-1])
        busy=sum(fresh.get(n,{}).get('busy',0)/max(1,fresh.get(n,{}).get('cca',0)) for p in paths for n in p[:-1])
        shared=len(set(paths[0][1:-1])&set(paths[1][1:-1]))
        return .2*length+.4*queues+.3*busy+.1*shared
    def candidates(self,action,active):
        if action==1:return list(reversed(self.memory))[:8]
        if action in (2,3):
            # Topology filtering is not outcome evaluation. Record examined list;
            # every scalar feasibility/score evaluation consumes FE.
            return [ps for ps in self.catalog if all(n in active for p in ps for n in p)][:16 if action==2 else 64]
        pairs=[]
        # One interior-node splice around each original/current relay. Other
        # portions retained; endpoint/hop geometry verified before scoring.
        for n in sorted(self.points):
            if n in (0,1,9):continue
            for at in range(1,min(map(len,self.current))-1):
                ps=[]
                for p in self.current:
                    q=p[:at]+(n,)+p[at+1:]
                    if len(set(q))!=len(q) or any(math.dist(self.points[a],self.points[b])>65 for a,b in zip(q,q[1:])):break
                    ps.append(q)
                if len(ps)==2 and tuple(ps) not in pairs:pairs.append(tuple(ps))
        return ([self.current]+pairs)[:8]
    def constraint_view(self,active,t):
        start=time.perf_counter_ns();domains={0:self.candidates(0,active),1:self.candidates(1,active)}
        checks=0;witnesses={};available=[]
        for a in (0,1):
            good=[]
            for ps in domains[a]:
                checks+=1
                if all(n in active for p in ps for n in p):good.append(ps)
            available.append(bool(good));witnesses[str(a)]=good[0] if good else None
        large=[]
        for ps in self.catalog:
            checks+=1
            if all(n in active for p in ps for n in p):large.append(ps)
            if len(large)==64 and self.search_mode=='legacy':break
        if self.search_mode!='legacy' and len(large)>64:
            large=[large[i*(len(large)-1)//63] for i in range(64)]
        domains[2]=large[:16];domains[3]=large
        for a in (2,3):available.append(bool(domains[a]));witnesses[str(a)]=domains[a][0] if domains[a] else None
        row=dict(time_ns=t,available=available,witnesses=witnesses,candidate_pair_freshness_checks=checks,
                 unselected_objective_evaluations=0,constraint_wall_ns=time.perf_counter_ns()-start)
        self.constraint_logs.append(row);return domains,row
    def search_candidates(self,action,candidates,fresh,active):
        from wsn.multiobjective import search
        return search(candidates,fresh,active,self.points,self.search_mode,unknown=getattr(self,'unknown_risk',False))

    def exploration_candidates(self,allowed,attempts):
        return [a for a in allowed if attempts is not None and a not in attempts]

    def step(self,obs):
        start=time.perf_counter_ns();reports,fresh,active,x,event=self.view(obs);fb=self.feedback(obs,reports)
        reports,fresh,active,x,event=self.view(obs)
        paid=self.policy in ('linucb_paid','linucb_paid_mask') and len(self.warmup_attempts)<4
        observed_event=event['missing']>0 or event['busy']>.35 or event['source_queue']>2 or event.get('trigger_failure',False)
        event_explore=self.policy.startswith('linucb_event') and self.sequence>0 and observed_event and len(self.event_attempts)<self.exploration_cap
        source_fresh=all(f in fresh for f in (0,1));trigger=paid or self.sequence==0 or observed_event
        base=dict(kind='step',observation=obs,event=event,context=x,decision=None,feedback=fb,constraints=None)
        if self.pending is not None or obs['time_ns']>=self.action_stop_ns or not trigger or (paid and not source_fresh):return '-1 0 0',base
        domains=None;mask=None
        if self.masked:
            domains,mask=self.constraint_view(active,obs['time_ns']);base['constraints']=mask
            if not any(mask['available']):base['rejection']='all_arms_infeasible';return '-1 0 0',base
        allowed=[a for a in range(4) if mask is None or mask['available'][a]]
        phase='event_policy';ordinal=None
        attempts=self.warmup_attempts if paid else self.event_attempts if event_explore and source_fresh else None
        eligible=self.exploration_candidates(allowed,attempts)
        if eligible:
            action=eligible[0];attempts.append(action);phase='paid_warmup' if paid else 'event_exploration';ordinal=len(attempts)
        elif self.policy.startswith('force'):
            action=next(int(c) for c in self.policy if c.isdigit()) if self.policy!='force_cycle' else self.sequence%4
        elif self.policy=='fixed_local':action=0
        elif self.policy=='fixed_history':action=1
        elif self.policy.startswith('event_rule'):
            preferred=2 if event['missing'] or event.get('trigger_failure',False) else 3 if event['busy']>.35 else 1
            action=preferred if preferred in allowed else allowed[0]
        elif self.selection_mode=='random':
            from wsn.rng import uniform
            action=allowed[min(int(uniform(self.selection_seed,'phase15-action',self.sequence)*len(allowed)),len(allowed)-1)]
        elif self.is_bandit:
            scores=self.bandit.scores(x);action=max(allowed,key=lambda a:(scores[a],-a))
        else:raise ValueError(self.policy)
        cand=domains[action] if domains is not None else self.candidates(action,active);evaluated=[];best=None;search_info=None
        if self.search_mode!='legacy':
            paths,evaluated,search_info=self.search_candidates(action,cand,fresh,active)
        else:
            for paths in cand:
                score=self.score(paths,fresh,active);evaluated.append(dict(paths=paths,score=score))
                if score is not None and (best is None or (score,paths)<best):best=(score,paths)
            paths=best[1] if best else None
        fe=max(1,len(evaluated));self.sequence+=1;decision=self.sequence
        if paths:self.version_paths[decision]=paths
        record=dict(decision=decision,time_ns=obs['time_ns'],action=action,context=x,paths=paths,fe=fe,
                    evaluated=evaluated,search=search_info,exploration_cap=self.exploration_cap,event=event,bucket=obs['time_ns']//5_000_000_000,
                    compute_wall_ns=time.perf_counter_ns()-start,declared_search_delay_ns=fe*20_000,
                    install_budget_bytes=1998 if paths else 0,ucb_scores=self.bandit.scores(x) if self.is_bandit else None,
                    selection_phase=phase,warmup_ordinal=ordinal,report_profile=self.report_profile,constraints=mask)
        record['selection_rule']=('forced_exploration' if phase in ('paid_warmup','event_exploration') else
                                  'random_feasible' if self.selection_mode=='random' else
                                  'frozen_ucb_score' if self.selection_mode=='frozen' else
                                  'intercept_ucb_score' if self.selection_mode=='intercept' else
                                  'linucb_score' if self.is_bandit else 'deterministic_policy')
        record['updates_before_selection']=list(self.bandit.updates)
        self.pending=record;self.logs.append(record);self.last_decision=obs['time_ns']
        chunks=[str(action),str(decision),str(fe)]
        for f in range(2):chunks+=[str(len(paths[f]))]+list(map(str,paths[f])) if paths else ['0']
        base['decision']=record;return ' '.join(chunks),base
