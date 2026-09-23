"""Energy search with a 180-second arrival buffer for all boxes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import d_q2_pareto as p

p.o.MARGIN=180.0
p.o.solve_type.cache_clear()
p.o.evaluate_plan.cache_clear()
plan,value,hist=p.search(p.FAST_PLAN,'energy',float(sys.argv[1]) if len(sys.argv)>1 else 65.0)
p.o.save(plan,value,hist,'d_q2_robust_results.json')
