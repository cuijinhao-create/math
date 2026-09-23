from pathlib import Path
from itertools import combinations, permutations
import json,sys
sys.path.insert(0,str(Path(__file__).parent))
import d_q2 as q

p=json.loads(Path(r'E:\codexh\2026-09-23\ai\work\d_q2_run2\d_q2_baseline.json').read_text(encoding='utf-8'))
boxes,_=q.read_boxes();nodes=q.q1.read_nodes();ac=q.q1.read_aircraft();dem=q.q1.Dem(next(q.DATA.rglob('*.tif')))
routes=q.pair_routes(nodes,dem)
terminal={t['id'] for t in p['trips'] if p['drones'][t['drone']]['sorties'][-1]==t['id'] and p['batteries'][t['battery']]['sorties'][-1]==t['id']}
print('terminal',terminal)
for a,b in combinations([t for t in p['trips'] if t['id'] in terminal],2):
    if a['model']!=b['model']:continue
    model=a['model'];res=ac[model]
    if a['mass']+b['mass']>res['maxload'] or a['volume']+b['volume']>res['maxvolume']:continue
    for keeper in (a,b):
        for stops in permutations([a['stops'][0],b['stops'][0]]):
            t=q.evaluate_trip(model,list(stops),boxes,ac,routes,keeper['load_start'])
            if t is None:continue
            late=sum(x>boxes[k]['expected']+1e-8 for k,x in t['deliveries'].items())
            if q.hard_misses(t,boxes):continue
            print(a['id'],b['id'],'keeper',keeper['id'],'order',[x['service'] for x in stops],
                  'newenergy',round(t['energy'],3),'saved',round(a['energy']+b['energy']-t['energy'],3),
                  'return',round(t['return_time']),'late',late)
