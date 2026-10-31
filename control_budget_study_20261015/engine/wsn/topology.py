"""Three registered ten-node geometries, generated without service outcomes."""
from wsn.rng import uniform
BASE={0:(0,0),1:(0,4),2:(40,0),3:(80,0),4:(40,35),5:(80,35),6:(60,-35),7:(100,-35),8:(20,-35),9:(120,0)}
def geometry(name):
    if name.startswith('budget_'):
        _,count,seed=name.split('_');count=int(count);seed=int(seed)
        if count not in (10,20,40):raise ValueError('unsupported study scale')
        p={n:tuple(float(v)+12*(uniform(seed,'budget-layout',n,axis)-.5)for axis,v in enumerate(xy))if n not in(0,1,9)else xy for n,xy in BASE.items()}
        for n in range(10,count):p[n]=(20+80*uniform(seed,'extra-x',n),-40+80*uniform(seed,'extra-y',n))
        return p
    if name=='base':return dict(BASE)
    if name.startswith('protect_'):
        seed=int(name.split('_')[1])
        if seed not in (1032301,1032302,1032303,1032304):raise ValueError('unregistered protection geometry')
        return {n:tuple(float(v)+12*(uniform(seed,'protection-geometry-v1',n,axis)-.5) for axis,v in enumerate(xy)) if n not in (0,1,9) else xy for n,xy in BASE.items()}
    if name.startswith('review_'):
        seed=int(name.split('_')[1])
        if seed not in (1031301,1031302,1031303,1031304):raise ValueError('unregistered review geometry')
        return {n:tuple(float(v)+12*(uniform(seed,'review-geometry-v1',n,axis)-.5) for axis,v in enumerate(xy)) if n not in (0,1,9) else xy for n,xy in BASE.items()}
    if name.startswith('heldout_'):
        seed=int(name.split('_')[1])
        if seed not in range(994301,994307):raise ValueError('unregistered heldout geometry')
        return {n:tuple(float(v)+16*(uniform(seed,'submission-geometry',n,axis)-.5) for axis,v in enumerate(xy)) if n not in (0,1,9) else xy for n,xy in BASE.items()}
    if name not in ('jitter_a','jitter_b'):raise ValueError(name)
    seed={'jitter_a':970201,'jitter_b':970202}[name]
    return {n:tuple(float(v)+16*(uniform(seed,'phase11geometry',n,axis)-.5) for axis,v in enumerate(xy)) if n not in (0,1,9) else xy for n,xy in BASE.items()}
