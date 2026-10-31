"""Four observable route operating points; equal FE budget, no future labels."""
import math
from wsn.multiobjective import objectives,frontier,hypervolume,REFERENCE

NAMES=('resource','worst_source_risk','relay_separation','route_stability')

def search_operator(action,candidates,fresh,active,points,current,service):
    rows=[]
    poor=service.get('known',False) and service['worst_timely']<.8
    for paths in candidates:
        z=objectives(paths,fresh,active,points,unknown=False)
        shared=len(set(paths[0][1:-1])&set(paths[1][1:-1]))/5
        changes=sum(paths[f]!=current[f] for f in (0,1))/2
        if z is None:score=None
        elif action==0:score=.85*z[2]+.15*sum(z[:2])/2
        elif action==1:score=.85*max(z[:2])+.15*z[2]
        elif action==2:score=.55*shared+.35*max(z[:2])+.10*z[2]
        elif action==3:score=.55*max(z[:2])+.25*z[2]+(.02 if poor else .20)*changes
        else:raise ValueError('invalid operator')
        rows.append(dict(paths=paths,objectives=z,score=score,shared_relay_fraction=shared,changed_source_fraction=changes))
    valid=[r for r in rows if r['score'] is not None]
    # A poor settled current-route cohort is a reason to consider alternatives;
    # it is not evidence of the outcome of any unselected route.
    alternatives=[r for r in valid if r['paths']!=current]
    choice=alternatives if poor and alternatives else valid
    best=min(choice,key=lambda r:(r['score'],r['paths'])) if choice else None
    archive=frontier(valid)
    return best['paths'] if best else None,rows,dict(mode='observable_operator',operator=NAMES[action],reference=REFERENCE,archive=archive,
        proxy_hypervolume=hypervolume([r['objectives'] for r in archive]),selected_objectives=best['objectives'] if best else None,
        poor_settled_service=poor,scope='received report proxy only; no counterfactual reward or physical liveness')
