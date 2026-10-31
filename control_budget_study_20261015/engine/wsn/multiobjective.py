"""Bounded observable Pareto recovery; no evolutionary-algorithm claim."""
import math
REFERENCE=(1.1,1.1,1.1)

def dominates(a,b):return all(x<=y for x,y in zip(a,b)) and any(x<y for x,y in zip(a,b))

def frontier(rows):
    """One deterministic representative for each non-dominated objective vector."""
    unique={}
    for r in rows:
        z=tuple(r['objectives'])
        if z not in unique or r['paths']<unique[z]['paths']:unique[z]=r
    return sorted([r for z,r in unique.items() if not any(dominates(w,z) for w in unique)],key=lambda r:(r['objectives'],r['paths']))

def hypervolume(points,reference=REFERENCE):
    """Exact union of minimization boxes; recursive axis slicing (small archives)."""
    ref=tuple(reference)
    if not ref or any(not math.isfinite(v) for v in ref):raise ValueError('invalid reference')
    ps=[]
    for p in points:
        p=tuple(p)
        if len(p)!=len(ref) or any(not math.isfinite(v) for v in p):raise ValueError('invalid objective')
        if any(v>r for v,r in zip(p,ref)):raise ValueError('point outside fixed reference')
        ps.append(p)
    if not ps:return 0.
    if len(ref)==1:return ref[0]-min(p[0] for p in ps)
    cuts=sorted(set(p[0] for p in ps)|{ref[0]});value=0.
    for x,y in zip(cuts,cuts[1:]):
        value+=(y-x)*hypervolume([p[1:] for p in ps if p[0]<=x],ref[1:])
    return value

def objectives(paths,fresh,active,points,unknown=False):
    if any(n not in active for p in paths for n in p):return None
    risks=[]
    for p in paths:
        value=0.
        for n in p[:-1]:
            r=fresh[n]
            risk=.45*min(max(r['depth']/16,0.),1.)+.35*min(max(r['busy']/max(1,r['cca']),0.),1.)+.2*min(max(r['mean_J_ns']/50_000_000,0.),1.)
            if unknown:
                samples=r.get('n',0);risk=max(risk,.5) if samples==0 else min(1.,risk+.15/math.sqrt(samples))
            value+=risk
        risks.append(value/6.)
    hops=sum(len(p)-1 for p in paths)
    length=sum(math.dist(points[a],points[b]) for p in paths for a,b in zip(p,p[1:]))
    shared=len(set(paths[0][1:-1])&set(paths[1][1:-1]))
    resource=.6*hops/12+.25*length/780+.15*shared/5
    z=tuple(risks+[resource])
    if any(not 0<=v<=1+1e-12 for v in z):raise ValueError('normalization bounds violated')
    return z

def merit(z,mode):
    if mode=='scalar':return sum(z)/3
    if mode=='pareto':return max(z)+.05*sum(z)
    if mode=='riskfirst':return max(z[:2])+.05*sum(z[:2])+.02*z[2]
    raise ValueError(mode)

def search(candidates,fresh,active,points,mode,unknown=False):
    evaluated=[]
    for paths in candidates:
        z=objectives(paths,fresh,active,points,unknown=unknown)
        evaluated.append(dict(paths=paths,objectives=z,score=merit(z,mode) if z is not None else None))
    valid=[r for r in evaluated if r['objectives'] is not None];archive=frontier(valid)
    selection=archive if mode in ('pareto','riskfirst') else valid
    best=min(selection,key=lambda r:(r['score'],r['paths'])) if selection else None
    hv=hypervolume([r['objectives'] for r in archive])
    return (best['paths'] if best else None),evaluated,dict(mode=mode,reference=REFERENCE,archive=archive,proxy_hypervolume=hv,
        selected_objectives=best['objectives'] if best else None,unknown_risk=unknown,selection_rule={'scalar':'mean','pareto':'max(z)+0.05*sum(z)','riskfirst':'max(z[:2])+0.05*sum(z[:2])+0.02*z[2]'}[mode],
        scope='received-report proxy objectives; no unselected future network outcome')
