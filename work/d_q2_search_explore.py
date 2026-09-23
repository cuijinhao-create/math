from __future__ import annotations
import json, sys, time
from pathlib import Path

ROOT=Path(r'E:\codexh\2026-09-23\ai')
sys.path.insert(0,str(ROOT/'outputs'))
import d_q2 as q2

PY_START=time.time()
BASE=json.loads((ROOT/'outputs'/'d_q2_results.json').read_text(encoding='utf-8'))
BOXES,BY=q2.read_boxes()
AIR=q2.q1.read_aircraft()
NODES=q2.q1.read_nodes()
DEM=q2.q1.Dem(next(q2.DATA.rglob('*.tif')))
ROUTES=q2.pair_routes(NODES,DEM)
DRONES,BATS=q2.read_resources()

def compile_trip(stops,model):
    q=q2.evaluate_trip(model,stops,BOXES,AIR,ROUTES,0)
    if q is None:return None
    out={k:q[k] for k in ('model','stops','boxes','mass','volume','energy')}
    out['duration']=q['return_time']
    out['offsets']=q['deliveries']
    out['charge']=q2.charge_to_full(q['return_soc'],next(x['charge_full_s'] for x in BATS.values() if x['model']==model))
    out['latest_hard']=min((BOXES[b]['hard_deadline']-t for b,t in q['deliveries'].items() if BOXES[b]['hard_deadline'] is not None),default=float('inf'))
    out['latest_expected']=min((BOXES[b]['expected']-t for b,t in q['deliveries'].items()),default=float('inf'))
    return out

TRIPS=[compile_trip(t['stops'],t['model']) for t in BASE['trips']]

def solve_type(tasks,model):
    nd=sum(d['model']==model for d in DRONES.values())
    nb=sum(b['model']==model for b in BATS.values())
    best=None
    count=0
    def rec(rem,d_av,b_av,records):
        nonlocal best,count
        if not rem:
            count+=1
            makespan=max((r['end'] for r in records),default=0)
            totalarr=sum(BOXES[b]['priority']*(r['start']+tasks[r['idx']]['offsets'][b]) for r in records for b in tasks[r['idx']]['boxes'])
            score=(makespan,totalarr)
            if best is None or score<best[0]:best=(score,records[:])
            return
        if best is not None and max(d_av)>=best[0][0] and len(rem)<=nd:
            pass
        di=min(range(nd),key=lambda k:(d_av[k],k))
        bi=min(range(nb),key=lambda k:(b_av[k],k))
        start=max(d_av[di],b_av[bi]);
        for k in sorted(rem,key=lambda i:(tasks[i]['latest_hard'],tasks[i]['latest_expected'])):
            t=tasks[k]
            if start>min(t['latest_hard'],t['latest_expected'])+1e-8:continue
            end=start+t['duration']
            if best is not None and end>best[0][0]+1e-8:continue
            oldd,oldb=d_av[di],b_av[bi]
            d_av[di]=end;b_av[bi]=end+t['charge']
            records.append(dict(idx=k,di=di,bi=bi,start=start,end=end))
            rec([i for i in rem if i!=k],d_av,b_av,records)
            records.pop();d_av[di]=oldd;b_av[bi]=oldb
    rec(list(range(len(tasks))),[0.0]*nd,[0.0]*nb,[])
    return best,count

for m in 'ABC':
    tasks=[t for t in TRIPS if t['model']==m]
    b,n=solve_type(tasks,m)
    print(m,'feasible schedules',n,'best',b[0] if b else None,'order',[tasks[r['idx']]['stops'][0]['service'] for r in b[1]] if b else None)
print('elapsed',time.time()-PY_START)
