from pathlib import Path
from collections import Counter
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,str(Path(__file__).parent))
import d_q1 as q1

p=Path(r'E:\codexh\2026-09-23\ai\work\d_q1_run\d_q1_results.json')
data=json.loads(p.read_text(encoding='utf-8'))
nodes=q1.read_nodes(); ac=q1.read_aircraft(); boxes=q1.read_boxes()
raw={b['id']:(s,b) for s,arr in boxes.items() for b in arr}
assert len(raw)==80
for name,strategy in list(data['strategies'].items())+[(f'all_{k}',v) for k,v in data['fixed_model_results'].items()]:
    seen=[]
    for row in strategy['trips']:
        entries=[raw[x] for x in row['boxes']]
        assert all(s==row['service'] for s,_ in entries)
        assert abs(sum(b['mass'] for _,b in entries)-row['mass'])<1e-8
        assert abs(sum(b['volume'] for _,b in entries)-row['volume'])<1e-8
        model=ac[row['model']]
        if name.startswith('all_'):
            assert row['model']==name[-1]
        assert row['mass']<=model['maxload']+1e-8
        assert row['volume']<=model['maxvolume']+1e-8
        assert row['energy']<=(1-model['reserve'])*model['battery']+1e-8
        assert abs(100*(1-row['energy']/model['battery'])-row['return_soc'])<1e-8
        seen.extend(row['boxes'])
    assert len(seen)==80 and Counter(seen)==Counter(raw.keys())
    assert strategy['summary']['sorties']==len(strategy['trips'])
    print(name,'PASS',len(strategy['trips']),'trips')

# A simple per-service lower bound proves the 18-sortie plan reaches the
# minimum possible sortie count under the no-cross-service Q1 rule.
lower=0
for s,arr in boxes.items():
    total_mass=sum(x['mass'] for x in arr)
    max_mass=max(x['max_safe_payload_kg'] for x in data['safety'] if x['service']==s and x['max_safe_payload_kg'] is not None)
    import math
    lower+=math.ceil((total_mass-1e-9)/max_mass)
print('MASS LOWER BOUND',lower)
assert lower==18

# Compare the exact grid-traversal terrain maxima with independent dense
# 0.1-pixel stepping along every direct route.
dem=q1.Dem(next(q1.DATA.rglob('*.tif')))
for s in boxes:
    x0,y0=dem.xy(nodes['O01']); x1,y1=dem.xy(nodes[s])
    steps=math.ceil(max(abs(x1-x0),abs(y1-y0))*10)
    sampled=max(float(dem.pixels[math.floor(x0+(x1-x0)*k/steps),
                                  math.floor(y0+(y1-y0)*k/steps)])
                for k in range(steps+1))
    assert sampled<=data['routes'][s]['terrain_max']+1e-6
print('DEM MAXIMA PASS 15 routes')
