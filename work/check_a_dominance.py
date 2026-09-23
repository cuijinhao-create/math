from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).parent))
import d_q1 as q

p=json.loads(Path(r'E:\codexh\2026-09-23\ai\outputs\d_q1_results.json').read_text(encoding='utf-8'))
boxes=q.read_boxes(); ac=q.read_aircraft()
A,B=ac['A'],ac['B']
count=0; b_infeasible=[]; b_worse_energy=[]; b_worse_time=[]
min_energy_gain=float('inf'); max_energy_gain=0
for site,items in boxes.items():
    route=p['routes'][site]
    n=len(items)
    masses=[0.0]*(1<<n);volumes=[0.0]*(1<<n);counts=[0]*(1<<n)
    for mask in range(1,1<<n):
        bit=mask&-mask; k=bit.bit_length()-1;prev=mask^bit
        masses[mask]=masses[prev]+items[k]['mass']
        volumes[mask]=volumes[prev]+items[k]['volume']
        counts[mask]=counts[prev]+1
        if masses[mask]>A['maxload']+1e-9 or volumes[mask]>A['maxvolume']+1e-9:continue
        ea,ta=q.trip(A,route,masses[mask],counts[mask])
        if ea>(1-A['reserve'])*A['battery']+1e-9:continue
        count+=1
        eb,tb=q.trip(B,route,masses[mask],counts[mask])
        if eb>(1-B['reserve'])*B['battery']+1e-9:b_infeasible.append((site,mask,ea,eb))
        if eb>=ea-1e-9:b_worse_energy.append((site,mask,ea,eb))
        if tb>=ta-1e-9:b_worse_time.append((site,mask,ta,tb))
        min_energy_gain=min(min_energy_gain,ea-eb)
        max_energy_gain=max(max_energy_gain,ea-eb)
print('A-feasible groups',count)
print('B infeasible',len(b_infeasible),'B non-improving energy',len(b_worse_energy),'B non-improving time',len(b_worse_time))
print('B saving per identical trip kWh range',round(min_energy_gain,4),round(max_energy_gain,4))
print('example B infeasible',b_infeasible[:3])
