"""D题问题二可行排程：实体无人机、共享电池与逐箱交付时刻。

运行：python d_q2.py [输出目录] [D题数据目录]
依赖：openpyxl、Pillow。问题二允许单点或多点架次；本版构造单点基线。
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from math import ceil
from pathlib import Path
import json
import sys

from openpyxl import load_workbook

sys.path.insert(0,str(Path(__file__).parent))
import d_q1 as q1

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DATA=(Path(sys.argv[2]) if len(sys.argv)>2 else q1.DATA)
BASE=DATA/'无人机应急物资运输基础数据'
q1.DATA=DATA
q1.BASE=BASE
EPS=1e-8


def read_boxes():
    ws=load_workbook(BASE/'物资需求与配送时限.xlsx',read_only=True,data_only=True)['逐箱货箱清单']
    boxes={}; by=defaultdict(list)
    for r in list(ws.values)[1:]:
        if not r[0]:continue
        hard=[]
        if r[2]=='医疗物资' and r[7] is not None: hard.append(float(r[7]))
        if r[5]=='是' and r[6] is not None:hard.append(float(r[6]))
        x=dict(id=r[0],service=r[1],kind=r[2],mass=float(r[3]),volume=float(r[4]),
               first=r[5]=='是',hard_deadline=min(hard) if hard else None,
               expected=float(r[7]) if r[7] is not None else None,priority=float(r[8]))
        boxes[x['id']]=x;by[x['service']].append(x['id'])
    assert len(boxes)==80
    return boxes,dict(by)


def read_resources():
    ws=load_workbook(BASE/'运输无人机数据.xlsx',read_only=True,data_only=True).active
    rows=list(ws.values)
    drones={}
    batteries={}
    for r in rows:
        if isinstance(r[0],str) and r[0].startswith('U') and r[1] in 'ABC':
            drones[r[0]]=dict(id=r[0],model=r[1],available=0.0,sorties=[])
    for r in rows:
        if isinstance(r[0],str) and r[0] in 'ABC' and isinstance(r[1],int) and isinstance(r[2],(int,float)):
            for k in range(1,r[1]+1):
                bid=f'{r[0]}-BAT-{k:02d}'
                batteries[bid]=dict(id=bid,model=r[0],charge_full_s=float(r[2]),available=0.0,sorties=[])
    assert len(drones)==8 and len(batteries)==14
    return drones,batteries


def charge_to_full(soc,full_time):
    if soc<0.90:
        return full_time*(0.65*(0.90-soc)/0.90+0.35)
    return full_time*0.35*(1-soc)/0.10


def pair_routes(nodes,dem):
    routes={}
    keys=list(nodes)
    for i,j in combinations(keys,2):
        ni,nj=nodes[i],nodes[j]
        terrain,ncells=dem.max_on_segment(ni,nj)
        cruise=terrain+50
        ai=ni['ground']+(30 if i!='O01' else 0)
        aj=nj['ground']+(30 if j!='O01' else 0)
        if cruise+EPS<max(ai,aj):raise ValueError(f'Cruise below terminal altitude: {i},{j}')
        d=q1.haversine(ni['lon'],ni['lat'],nj['lon'],nj['lat'])
        routes[(i,j)]=dict(distance=d,terrain_max=terrain,cruise=cruise,
                           climb=cruise-ai,descend=cruise-aj,cells=ncells)
        routes[(j,i)]=dict(distance=d,terrain_max=terrain,cruise=cruise,
                           climb=cruise-aj,descend=cruise-ai,cells=ncells)
    return routes


def leg(ac,route,payload):
    e=q1.segment_energy(ac,route['distance'],route['climb'],payload)
    t=route['climb']/ac['climb_speed']+route['distance']/ac['cruise_speed']+route['descend']/ac['descend_speed']
    return e,t


def evaluate_trip(model,stops,boxes,aircraft,routes,start):
    ac=aircraft[model]
    ids=[bid for stop in stops for bid in stop['boxes']]
    assert len(ids)==len(set(ids))
    total_mass=sum(boxes[bid]['mass'] for bid in ids)
    total_volume=sum(boxes[bid]['volume'] for bid in ids)
    if total_mass>ac['maxload']+EPS or total_volume>ac['maxvolume']+EPS:return None
    t=start+ac['prepare']+len(ids)*ac['load_each']
    energy=0.0;current='O01';carrying=total_mass;delivery={}
    for stop in stops:
        e,dt=leg(ac,routes[(current,stop['service'])],carrying)
        t+=dt;energy+=e
        t+=ac['handoff_base']+len(stop['boxes'])*ac['handoff_each']
        for bid in stop['boxes']:delivery[bid]=t
        carrying-=sum(boxes[bid]['mass'] for bid in stop['boxes'])
        current=stop['service']
    e,dt=leg(ac,routes[(current,'O01')],0.0)
    t+=dt;energy+=e
    if energy>(1-ac['reserve'])*ac['battery']+EPS:return None
    return dict(model=model,stops=stops,boxes=ids,mass=total_mass,volume=total_volume,
                energy=energy,load_start=start,return_time=t,deliveries=delivery,
                return_soc=1-energy/ac['battery'])


def choose_direct_group(site,model,remaining,required,boxes,aircraft,routes,start):
    """Try all subsets at one site and return useful high-load alternatives."""
    items=list(remaining)
    req=set(required)
    if not req.issubset(items):return []
    n=len(items)
    ac=aircraft[model]
    masks=[]
    rmask=sum(1<<i for i,bid in enumerate(items) if bid in req)
    mass=[0.0]*(1<<n);vol=[0.0]*(1<<n)
    for mask in range(1,1<<n):
        bit=mask&-mask;k=bit.bit_length()-1;old=mask^bit
        mass[mask]=mass[old]+boxes[items[k]]['mass']
        vol[mask]=vol[old]+boxes[items[k]]['volume']
        if mask&rmask!=rmask or mass[mask]>ac['maxload']+EPS or vol[mask]>ac['maxvolume']+EPS:continue
        masks.append(mask)
    # Energetic feasibility is evaluated with the complete route. Since for a
    # direct route energy increases with cargo, inspecting the highest-load
    # candidates first usually finds a strong group quickly.
    threshold=min((boxes[bid]['hard_deadline'] for bid in req),default=None)
    if threshold is None:
        threshold=min(boxes[bid]['expected'] for bid in items)
    masks.sort(key=lambda m:(
        sum(1 for i in range(n) if m&(1<<i) and boxes[items[i]]['expected']<=threshold),
        sum(boxes[items[i]]['priority'] for i in range(n) if m&(1<<i) and boxes[items[i]]['expected']<=threshold),
        mass[m],m.bit_count()),reverse=True)
    valid=[]
    for mask in masks:
        ids=[items[i] for i in range(n) if mask&(1<<i)]
        trip=evaluate_trip(model,[dict(service=site,boxes=ids)],boxes,aircraft,routes,start)
        if trip is not None:
            valid.append(trip)
            if len(valid)>=3:break
    if req:
        trip=evaluate_trip(model,[dict(service=site,boxes=sorted(req))],boxes,aircraft,routes,start)
        if trip is not None and tuple(trip['boxes']) not in {tuple(v['boxes']) for v in valid}:
            valid.append(trip)
    return valid


def hard_misses(trip,boxes):
    return [(bid,t,boxes[bid]['hard_deadline']) for bid,t in trip['deliveries'].items()
            if boxes[bid]['hard_deadline'] is not None and t>boxes[bid]['hard_deadline']+EPS]


def apply_trip(trip,drone,battery,boxes,remaining,trips):
    assert not hard_misses(trip,boxes),hard_misses(trip,boxes)
    trip=dict(trip)
    trip['id']=f'Q2-{len(trips)+1:02d}'
    trip['drone']=drone['id'];trip['battery']=battery['id']
    trip['battery_ready_after_charge']=trip['return_time']+charge_to_full(trip['return_soc'],battery['charge_full_s'])
    assert trip['load_start']+EPS>=max(drone['available'],battery['available'])
    drone['available']=trip['return_time'];drone['sorties'].append(trip['id'])
    battery['available']=trip['battery_ready_after_charge'];battery['sorties'].append(trip['id'])
    for bid in trip['boxes']:
        assert bid in remaining[boxes[bid]['service']]
        remaining[boxes[bid]['service']].remove(bid)
    trips.append(trip)


def first_wave(boxes,remaining,aircraft,routes,drones,batteries,trips):
    sites=sorted(s for s,ids in remaining.items() if any(boxes[x]['hard_deadline'] is not None and boxes[x]['hard_deadline']<=3600 for x in ids))
    assert len(sites)==8,sites
    # All eight physical aircraft leave on one first wave. Enumerate the 420
    # model allocations and select the one delivering the most mass while
    # satisfying every 3600 s hard deadline.
    options={}
    for s in sites:
        req=[x for x in remaining[s] if boxes[x]['hard_deadline'] is not None and boxes[x]['hard_deadline']<=3600]
        for m in 'ABC':
            candidates=choose_direct_group(s,m,remaining[s],req,boxes,aircraft,routes,0.0)
            candidates=[x for x in candidates if not hard_misses(x,boxes)]
            if candidates:options[(s,m)]=min(candidates,key=lambda x:(-x['mass'],-len(x['boxes']),x['energy']))
    best=None
    for asites in combinations(sites,4):
        left=[s for s in sites if s not in asites]
        for bsites in combinations(left,2):
            assignment={s:'A' for s in asites}
            assignment.update({s:'B' for s in bsites})
            assignment.update({s:'C' for s in left if s not in bsites})
            if any((s,assignment[s]) not in options for s in sites):continue
            selected=[options[(s,assignment[s])] for s in sites]
            key=(-sum(x['mass'] for x in selected),
                 -sum(len(x['boxes']) for x in selected),
                 sum(x['energy'] for x in selected),
                 max(max(x['deliveries'].values()) for x in selected))
            if best is None or key<best[0]:best=(key,assignment)
    if best is None:raise RuntimeError('No feasible first-wave allocation')
    assigned=best[1]
    for m in 'ABC':
        model_sites=sorted(s for s in sites if assigned[s]==m)
        ds=sorted((d for d in drones.values() if d['model']==m),key=lambda x:x['id'])
        bs=sorted((b for b in batteries.values() if b['model']==m),key=lambda x:x['id'])
        for s,d,b in zip(model_sites,ds,bs):
            apply_trip(options[(s,m)],d,b,boxes,remaining,trips)
    return assigned


def next_dispatch(boxes,remaining,aircraft,routes,drones,batteries,trips):
    pending=[bid for ids in remaining.values() for bid in ids]
    if not pending:return False
    target=min((boxes[bid] for bid in pending),key=lambda x:(x['expected'],x['hard_deadline'] is None,x['service']))['service']
    required={bid for bid in remaining[target] if boxes[bid]['hard_deadline'] is not None}
    candidates=[]
    for d in drones.values():
        m=d['model']
        for b in batteries.values():
            if b['model']!=m:continue
            start=max(d['available'],b['available'])
            for trip in choose_direct_group(target,m,remaining[target],required,boxes,aircraft,routes,start):
                misses=hard_misses(trip,boxes)
                if misses:continue
                delivered=trip['deliveries']
                soft_late=sum(boxes[bid]['priority']*max(0,t-boxes[bid]['expected']) for bid,t in delivered.items())
                # Favor service completion and timely deliveries. Different
                # fleet states can produce different start times.
                leftover_mass=sum(boxes[bid]['mass'] for bid in remaining[target] if bid not in trip['boxes'])
                completion=(leftover_mass>EPS)
                key=(soft_late,completion,trip['return_time'],trip['energy'],-trip['mass'])
                candidates.append((key,trip,d,b))
    if not candidates:
        raise RuntimeError(f'No feasible dispatch for {target}, pending {remaining[target]}')
    _,trip,d,b=min(candidates,key=lambda x:x[0])
    apply_trip(trip,d,b,boxes,remaining,trips)
    return True


def summarize(trips,boxes):
    deliveries={bid:dict(trip=trip['id'],service=boxes[bid]['service'],time=t,
                         expected=boxes[bid]['expected'],hard_deadline=boxes[bid]['hard_deadline'])
                for trip in trips for bid,t in trip['deliveries'].items()}
    assert len(deliveries)==len(boxes)==80
    hard_violations=[bid for bid,x in deliveries.items() if x['hard_deadline'] is not None and x['time']>x['hard_deadline']+EPS]
    tardy=[bid for bid,x in deliveries.items() if x['time']>x['expected']+EPS]
    weighted_tardiness=sum(boxes[bid]['priority']*max(0,x['time']-x['expected']) for bid,x in deliveries.items())
    return dict(sorties=len(trips),total_energy_kwh=sum(x['energy'] for x in trips),
                makespan_s=max(x['return_time'] for x in trips),hard_violations=hard_violations,
                soft_tardy_boxes=len(tardy),weighted_tardiness_priority_seconds=weighted_tardiness),deliveries


def merge_terminal_trips(trips,drones,batteries,boxes,by,aircraft,routes):
    """Merge two terminal trips when a two-stop sortie saves energy and meets all dates."""
    from itertools import permutations
    terminal=[t for t in trips if drones[t['drone']]['sorties'][-1]==t['id']
              and batteries[t['battery']]['sorties'][-1]==t['id']]
    baseline_makespan=max(x['return_time'] for x in trips)
    options=[]
    for a,b in combinations(terminal,2):
        if a['model']!=b['model'] or a['stops'][0]['service']==b['stops'][0]['service']:
            continue
        model=a['model'];ac=aircraft[model]
        if a['mass']+b['mass']>ac['maxload']+EPS or a['volume']+b['volume']>ac['maxvolume']+EPS:
            continue
        for keeper in (a,b):
            for stops in permutations((a['stops'][0],b['stops'][0])):
                candidate=evaluate_trip(model,list(stops),boxes,aircraft,routes,keeper['load_start'])
                if candidate is None or hard_misses(candidate,boxes):continue
                if candidate['return_time']>baseline_makespan+EPS:continue
                if any(t>boxes[bid]['expected']+EPS for bid,t in candidate['deliveries'].items()):continue
                saving=a['energy']+b['energy']-candidate['energy']
                if saving<=EPS:continue
                options.append((saving,a,b,keeper,candidate))
    if not options:return trips,drones,batteries,None
    saving,a,b,keeper,candidate=max(options,key=lambda x:x[0])
    candidate['drone']=keeper['drone'];candidate['battery']=keeper['battery']
    raw=[t for t in trips if t['id'] not in (a['id'],b['id'])]+[candidate]
    raw.sort(key=lambda t:(t['load_start'],t.get('id','ZZZ')))
    new_drones,new_batteries=read_resources()
    remaining={s:set(ids) for s,ids in by.items()}
    replay=[]
    for t in raw:
        apply_trip(t,new_drones[t['drone']],new_batteries[t['battery']],boxes,remaining,replay)
    assert all(not ids for ids in remaining.values())
    note=dict(merged_old_trips=[a['id'],b['id']],new_trip=next(
        t['id'] for t in replay if len(t['stops'])==2),energy_saved_kwh=saving,
        stops=[x['service'] for x in candidate['stops']])
    return replay,new_drones,new_batteries,note


def main(outdir):
    boxes,by=read_boxes();drones,batteries=read_resources()
    nodes=q1.read_nodes();aircraft=q1.read_aircraft();dem=q1.Dem(next(DATA.rglob('*.tif')))
    routes=pair_routes(nodes,dem)
    remaining={s:set(ids) for s,ids in by.items()}
    trips=[]
    initial=first_wave(boxes,remaining,aircraft,routes,drones,batteries,trips)
    while next_dispatch(boxes,remaining,aircraft,routes,drones,batteries,trips):
        if len(trips)>100:raise RuntimeError('Too many trips')
    baseline_summary,_=summarize(trips,boxes)
    trips,drones,batteries,merge_note=merge_terminal_trips(
        trips,drones,batteries,boxes,by,aircraft,routes)
    summary,deliveries=summarize(trips,boxes)
    output=dict(summary=summary,baseline_summary=baseline_summary,merge_note=merge_note,
                first_wave_assignment=initial,trips=trips,
                deliveries=deliveries,drones=drones,batteries=batteries,
                assumptions=dict(route='Straight horizontal segment; DEM maximum + 50m cruise altitude',
                  energy='Same payload-dependent range and gravitational climb model as Q1',
                  hard='All medical expected times and first-batch deadlines',
                  ready='Aircraft available on return; battery reusable once charged to 100%',
                  scope='Construct direct-trip feasibility baseline, then merge a safe terminal pair into a multi-stop trip'))
    outdir.mkdir(parents=True,exist_ok=True)
    (outdir/'d_q2_results.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FIRST WAVE',initial)
    print('BASELINE',baseline_summary)
    print('MERGE',merge_note)
    print('SUMMARY',summary)
    print('MODEL SORTIES',{m:sum(x['model']==m for x in trips) for m in 'ABC'})
    print('OUTPUT',outdir/'d_q2_results.json')

if __name__=='__main__':
    main(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).parent)
