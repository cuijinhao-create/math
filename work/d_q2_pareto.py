"""Search energy and trip-count alternatives while preserving on-time delivery."""
from __future__ import annotations
import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import d_q2_optimize as o

BASE_PLAN = tuple(sorted(o.key_for(t['model'], t['stops']) for t in o.BASE['trips']))
FAST = o.json.loads((o.DATA/'d_q2_optimized_results.json').read_text(encoding='utf-8'))
FAST_PLAN = tuple(sorted(o.key_for(t['model'],t['stops']) for t in FAST['trips']))
ENERGY = o.json.loads((o.DATA/'d_q2_energy_results.json').read_text(encoding='utf-8')) if (o.DATA/'d_q2_energy_results.json').exists() else FAST
ENERGY_PLAN = tuple(sorted(o.key_for(t['model'],t['stops']) for t in ENERGY['trips']))
CAP = o.BASE['summary']['makespan_s'] + 1e-7

def rank(value, mode):
    span, energy, sorties, arrival = value['score']
    if span > CAP:return None
    if mode=='energy':return (energy,sorties,span,arrival)
    if mode=='sorties':return (sorties,energy,span,arrival)
    raise ValueError(mode)

def search(plan,mode,budget):
    start=time.monotonic()
    val=o.evaluate_plan(plan)
    best=rank(val,mode)
    history=[(0,'start',val['score'])]
    print('START',mode,best,val['score'],flush=True)
    iteration=0
    while time.monotonic()-start<budget:
        iteration+=1
        candidate=None
        counts={}
        for move in ('merge','move','model','order'):
            counts[move]=0
            for newplan,op in o.neighbors(plan,move):
                if time.monotonic()-start>budget:break
                counts[move]+=1
                v=o.evaluate_plan(newplan)
                if v is None:continue
                score=rank(v,mode)
                if score is None or score>=best:continue
                if candidate is None or score<candidate[2]:candidate=(newplan,v,score,op)
        if candidate is None:
            print('LOCAL OPT',mode,iteration,counts,'elapsed',round(time.monotonic()-start,1),flush=True)
            break
        plan,val,best,op=candidate
        history.append((iteration,op,val['score']))
        print('IMPROVE',mode,iteration,op,best,'elapsed',round(time.monotonic()-start,1),flush=True)
    return plan,val,history

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'energy'
    budget=float(sys.argv[2]) if len(sys.argv)>2 else 60.
    start_plan=BASE_PLAN if mode=='energy' else ENERGY_PLAN
    p,v,h=search(start_plan,mode,budget)
    o.save(p,v,h,f'd_q2_{mode}_results.json')
