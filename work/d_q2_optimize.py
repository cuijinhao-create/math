"""D Q2 route and resource local search using the official-data evaluator.

Run with bundled Python. Uses only the Python standard library, openpyxl and Pillow.
Every reported route is independently re-evaluated from the contest data.
"""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from itertools import combinations, permutations
from pathlib import Path
import json
import random
import sys
import time

ROOT = Path(r'E:\codexh\2026-09-23\ai')
sys.path.insert(0, str(ROOT / 'outputs'))
_ARGV = sys.argv[:]
sys.argv = sys.argv[:1]
import d_q2 as q2
sys.argv = _ARGV

DATA = ROOT / 'outputs'
BASE = json.loads((DATA / 'd_q2_results.json').read_text(encoding='utf-8'))
BOXES, BY = q2.read_boxes()
AIR = q2.q1.read_aircraft()
NODES = q2.q1.read_nodes()
DEM = q2.q1.Dem(next(q2.DATA.rglob('*.tif')))
ROUTES = q2.pair_routes(NODES, DEM)
DRONES, BATS = q2.read_resources()
DRONE_IDS = {m: tuple(sorted(d for d in DRONES if DRONES[d]['model'] == m)) for m in 'ABC'}
BAT_IDS = {m: tuple(sorted(b for b in BATS if BATS[b]['model'] == m)) for m in 'ABC'}
CHARGE_FULL = {m: BATS[BAT_IDS[m][0]]['charge_full_s'] for m in 'ABC'}
MARGIN = 0.0  # Optional minimum buffer against every expected/hard arrival limit.


def key_for(model, stops):
    return model, tuple((s['service'], tuple(sorted(s['boxes']))) for s in stops)


@lru_cache(maxsize=100000)
def compile_trip(key):
    model, stop_tuple = key
    stops = [dict(service=s, boxes=list(ids)) for s, ids in stop_tuple]
    trip = q2.evaluate_trip(model, stops, BOXES, AIR, ROUTES, 0.0)
    if trip is None:
        return None
    offsets = trip['deliveries']
    return dict(key=key, model=model, stops=stops, boxes=tuple(trip['boxes']),
                duration=trip['return_time'], energy=trip['energy'],
                mass=trip['mass'], volume=trip['volume'], offsets=offsets,
                charge=q2.charge_to_full(trip['return_soc'], CHARGE_FULL[model]),
                latest_hard=min((BOXES[b]['hard_deadline'] - t for b, t in offsets.items()
                                 if BOXES[b]['hard_deadline'] is not None), default=float('inf')),
                latest_expected=min(BOXES[b]['expected'] - t for b, t in offsets.items()))


@lru_cache(maxsize=200000)
def solve_type(type_keys):
    if not type_keys:
        return (0.0, 0.0), ()
    tasks = [compile_trip(k) for k in type_keys]
    if any(t is None for t in tasks):
        return None
    model = tasks[0]['model']
    nd = len(DRONE_IDS[model])
    nb = len(BAT_IDS[model])
    d_av = [0.0] * nd
    b_av = [0.0] * nb
    best = None
    records = []
    priority = sorted(range(len(tasks)), key=lambda i:
                      (tasks[i]['latest_hard'], tasks[i]['latest_expected'], -len(tasks[i]['boxes'])))

    def rec(rem):
        nonlocal best
        if not rem:
            makespan = max((r[4] for r in records), default=0.0)
            arrival = sum(BOXES[b]['priority'] * (r[3] + tasks[r[0]]['offsets'][b])
                          for r in records for b in tasks[r[0]]['boxes'])
            score = (makespan, arrival)
            if best is None or score < best[0]:
                best = (score, tuple(records))
            return
        di = min(range(nd), key=lambda k: (d_av[k], k))
        bi = min(range(nb), key=lambda k: (b_av[k], k))
        start = max(d_av[di], b_av[bi])
        for idx in priority:
            if idx not in rem:
                continue
            t = tasks[idx]
            if start > min(t['latest_hard'], t['latest_expected']) - MARGIN + 1e-8:
                continue
            end = start + t['duration']
            if best is not None and end > best[0][0] + 1e-8:
                continue
            oldd, oldb = d_av[di], b_av[bi]
            d_av[di], b_av[bi] = end, end + t['charge']
            records.append((idx, di, bi, start, end))
            rec(rem - {idx})
            records.pop()
            d_av[di], b_av[bi] = oldd, oldb

    rec(set(range(len(tasks))))
    return best


@lru_cache(maxsize=200000)
def evaluate_plan(plan):
    if len(plan) != len(set(plan)):
        # Duplicate route keys can still cover different boxes only if box IDs differ,
        # so exact duplicates are always invalid.
        return None
    all_boxes = [b for k in plan for b in compile_trip(k)['boxes']]
    if len(all_boxes) != len(BOXES) or len(set(all_boxes)) != len(BOXES):
        return None
    per = {}
    for model in 'ABC':
        keys = tuple(sorted(k for k in plan if k[0] == model))
        sched = solve_type(keys)
        if sched is None:
            return None
        per[model] = (keys, sched)
    makespan = max(per[m][1][0][0] for m in 'ABC')
    arrival = sum(per[m][1][0][1] for m in 'ABC')
    energy = sum(compile_trip(k)['energy'] for k in plan)
    return dict(score=(makespan, energy, len(plan), arrival), schedules=per)


def replace(plan, old, new):
    old = set(old)
    return tuple(sorted([k for k in plan if k not in old] + list(new)))


def merge_candidates(a, b):
    contents = defaultdict(list)
    for key in (a, b):
        for site, ids in key[1]:
            contents[site].extend(ids)
    sites = tuple(contents)
    if len(sites) > 3:
        return
    total_mass = sum(BOXES[bid]['mass'] for ids in contents.values() for bid in ids)
    total_vol = sum(BOXES[bid]['volume'] for ids in contents.values() for bid in ids)
    for model in 'ABC':
        if total_mass > AIR[model]['maxload'] + 1e-8 or total_vol > AIR[model]['maxvolume'] + 1e-8:
            continue
        for order in permutations(sites):
            key = (model, tuple((s, tuple(sorted(contents[s]))) for s in order))
            if compile_trip(key) is not None:
                yield key


def move_candidates(a, b):
    """Move one box from route a to route b, preserving an ordered stop sequence."""
    for bid in (x for _, ids in a[1] for x in ids):
        new_a = []
        for site, ids in a[1]:
            after = tuple(x for x in ids if x != bid)
            if after:
                new_a.append((site, after))
        if not new_a:
            continue
        ka = (a[0], tuple(new_a))
        if compile_trip(ka) is None:
            continue
        site = BOXES[bid]['service']
        if any(s == site for s, _ in b[1]):
            new_b = tuple((s, tuple(sorted(ids + (bid,))) if s == site else ids) for s, ids in b[1])
            kb = (b[0], new_b)
            if compile_trip(kb) is not None:
                yield ka, kb
        elif len(b[1]) < 3:
            for pos in range(len(b[1]) + 1):
                new_b = list(b[1]); new_b.insert(pos, (site, (bid,)))
                kb = (b[0], tuple(new_b))
                if compile_trip(kb) is not None:
                    yield ka, kb


def neighbors(plan, mode):
    if mode == 'model':
        for a in plan:
            for model in 'ABC':
                if model == a[0]:
                    continue
                key = (model, a[1])
                if compile_trip(key) is not None:
                    yield replace(plan, [a], [key]), f'model {a[0]}->{model}'
    elif mode == 'merge':
        for a, b in combinations(plan, 2):
            for key in merge_candidates(a, b):
                yield replace(plan, [a, b], [key]), 'merge'
    elif mode == 'move':
        for a in plan:
            for b in plan:
                if a == b:
                    continue
                for ka, kb in move_candidates(a, b):
                    yield replace(plan, [a, b], [ka, kb]), 'move'
    elif mode == 'order':
        for a in plan:
            if len(a[1]) < 2:
                continue
            for order in permutations(a[1]):
                if order == a[1]:
                    continue
                key = (a[0], order)
                if compile_trip(key) is not None:
                    yield replace(plan, [a], [key]), 'order'


def greedy_descent(plan, modes=('model', 'merge', 'move', 'order'), time_limit=60):
    begin = time.monotonic()
    best = evaluate_plan(plan)
    assert best is not None
    print('START', best['score'], flush=True)
    history = [(0, 'baseline routes rescheduled', best['score'])]
    round_no = 0
    while time.monotonic() - begin < time_limit:
        round_no += 1
        candidate = None
        counts = defaultdict(int)
        for mode in modes:
            for newplan, op in neighbors(plan, mode):
                if time.monotonic() - begin >= time_limit:
                    break
                counts[mode] += 1
                value = evaluate_plan(newplan)
                if value is not None and value['score'] < best['score']:
                    if candidate is None or value['score'] < candidate[1]['score']:
                        candidate = (newplan, value, op)
            if time.monotonic() - begin >= time_limit:
                break
        if candidate is None:
            print('LOCAL OPT', round_no, dict(counts), 'elapsed', round(time.monotonic()-begin,1), flush=True)
            break
        plan, best, op = candidate
        history.append((round_no, op, best['score']))
        print('IMPROVE', round_no, op, best['score'], dict(counts),
              'elapsed', round(time.monotonic()-begin,1), flush=True)
    return plan, best, history


def materialize(plan, value):
    results = []
    for m in 'ABC':
        keys, (_, records) = value['schedules'][m]
        for idx, di, bi, start, end in records:
            key = keys[idx]
            static = compile_trip(key)
            t = q2.evaluate_trip(m, static['stops'], BOXES, AIR, ROUTES, start)
            assert t is not None and abs(t['return_time']-end) < 1e-6
            t['drone'] = DRONE_IDS[m][di]
            t['battery'] = BAT_IDS[m][bi]
            t['battery_ready_after_charge'] = end + static['charge']
            results.append(t)
    results.sort(key=lambda t: (t['load_start'], t['model'], t['drone'], t['return_time']))
    for j, t in enumerate(results, 1):
        t['id'] = f'OPT-{j:02d}'
    return results


def independent_audit(trips):
    seen = set()
    d_intervals = defaultdict(list)
    b_intervals = defaultdict(list)
    for t in trips:
        rebuilt = q2.evaluate_trip(t['model'], t['stops'], BOXES, AIR, ROUTES, t['load_start'])
        assert rebuilt is not None
        assert abs(rebuilt['energy'] - t['energy']) < 1e-6
        assert abs(rebuilt['return_time'] - t['return_time']) < 1e-6
        for bid, arrival in t['deliveries'].items():
            assert bid not in seen
            seen.add(bid)
            assert arrival <= BOXES[bid]['expected'] + 1e-7
            if BOXES[bid]['hard_deadline'] is not None:
                assert arrival <= BOXES[bid]['hard_deadline'] + 1e-7
        assert DRONES[t['drone']]['model'] == t['model']
        assert BATS[t['battery']]['model'] == t['model']
        d_intervals[t['drone']].append((t['load_start'], t['return_time']))
        b_intervals[t['battery']].append((t['load_start'], t['battery_ready_after_charge']))
    assert seen == set(BOXES)
    for intervals in list(d_intervals.values()) + list(b_intervals.values()):
        intervals.sort()
        assert all(intervals[i][1] <= intervals[i+1][0] + 1e-7 for i in range(len(intervals)-1))


def save(plan, value, history, filename='d_q2_optimized_results.json'):
    trips = materialize(plan, value)
    independent_audit(trips)
    summary, deliveries = q2.summarize(trips, BOXES)
    assert summary['hard_violations'] == [] and summary['soft_tardy_boxes'] == 0
    assert abs(summary['makespan_s']-value['score'][0]) < 1e-6
    payload = dict(summary=summary, baseline=BASE['summary'],
                   optimization_history=history, trips=trips, deliveries=deliveries,
                   drone_ids=DRONE_IDS, battery_ids=BAT_IDS,
                   method='Multi-stop local search with enumerated same-model trip orders and earliest available drone/battery assignment; hard and expected deadlines required',
                   audit='Recomputed each route, each box deadline, and all drone/battery occupancy intervals')
    path=DATA/filename
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FINAL',summary, 'FILE',path, flush=True)
    return payload


if __name__ == '__main__':
    plan = tuple(sorted(key_for(t['model'], t['stops']) for t in BASE['trips']))
    budget = float(sys.argv[1]) if len(sys.argv)>1 else 90.0
    best_plan, best_value, hist = greedy_descent(plan, time_limit=budget)
    save(best_plan, best_value, hist)
