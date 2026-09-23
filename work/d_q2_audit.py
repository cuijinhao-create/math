from pathlib import Path
from collections import Counter,defaultdict
import json,sys
sys.path.insert(0,str(Path(__file__).parent))
import d_q2 as q

p=json.loads(Path(r'E:\codexh\2026-09-23\ai\work\d_q2_final\d_q2_results.json').read_text(encoding='utf-8'))
boxes,_=q.read_boxes();nodes=q.q1.read_nodes();ac=q.q1.read_aircraft();dem=q.q1.Dem(next(q.DATA.rglob('*.tif')))
routes=q.pair_routes(nodes,dem)
drones,batteries=q.read_resources()
seen=[];by_drone=defaultdict(list);by_battery=defaultdict(list)
hard_slack=[];soft_slack=[]
for t in p['trips']:
    assert t['drone'] in drones and t['battery'] in batteries
    assert drones[t['drone']]['model']==batteries[t['battery']]['model']==t['model']
    fresh=q.evaluate_trip(t['model'],t['stops'],boxes,ac,routes,t['load_start'])
    assert fresh is not None
    for k in ('energy','return_time','mass','volume','return_soc'):
        assert abs(fresh[k]-t[k])<1e-7,(t['id'],k)
    assert fresh['deliveries'].keys()==t['deliveries'].keys()
    for bid,at in t['deliveries'].items():
        assert abs(fresh['deliveries'][bid]-at)<1e-7
        assert t['load_start']<=at<=t['return_time']
        b=boxes[bid]
        soft_slack.append(b['expected']-at)
        if b['hard_deadline'] is not None:hard_slack.append(b['hard_deadline']-at)
        assert at<=b['expected']+1e-7
        if b['hard_deadline'] is not None:assert at<=b['hard_deadline']+1e-7
        seen.append(bid)
    by_drone[t['drone']].append(t)
    by_battery[t['battery']].append(t)
assert len(seen)==80 and Counter(seen)==Counter(boxes.keys())
for drone,ts in by_drone.items():
    ts.sort(key=lambda t:t['load_start'])
    for a,b in zip(ts,ts[1:]):assert b['load_start']+1e-7>=a['return_time'],(drone,a['id'],b['id'])
for battery,ts in by_battery.items():
    ts.sort(key=lambda t:t['load_start'])
    for a,b in zip(ts,ts[1:]):
        ready=a['return_time']+q.charge_to_full(a['return_soc'],batteries[battery]['charge_full_s'])
        assert b['load_start']+1e-7>=ready,(battery,a['id'],b['id'],ready,b['load_start'])
assert len(p['trips'])==p['summary']['sorties']
assert abs(sum(t['energy'] for t in p['trips'])-p['summary']['total_energy_kwh'])<1e-7
assert abs(max(t['return_time'] for t in p['trips'])-p['summary']['makespan_s'])<1e-7
print('PASS: 80 unique boxes, 22 trips, exact route recomputation, deadlines, airframes, batteries, charging')
print('minimum hard slack s',min(hard_slack),'minimum expected slack s',min(soft_slack))
print('used drones',len(by_drone),'used batteries',len(by_battery))
print('multistop',[(t['id'],[x['service'] for x in t['stops']]) for t in p['trips'] if len(t['stops'])>1])
