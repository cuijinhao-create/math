from pathlib import Path
from collections import Counter
import json

source=Path(r'E:\codexh\2026-09-23\ai\work\d_q2_final\d_q2_results.json')
out=Path(r'E:\codexh\2026-09-23\ai\outputs')
out.mkdir(parents=True,exist_ok=True)
p=json.loads(source.read_text(encoding='utf-8'))
s=p['summary'];b=p['baseline_summary']
min_hard=min(x['hard_deadline']-x['time'] for x in p['deliveries'].values() if x['hard_deadline'] is not None)
min_expected=min(x['expected']-x['time'] for x in p['deliveries'].values())
model_counts=Counter(t['model'] for t in p['trips'])

lines=['# D题问题二运输与电池调度试算','',
       '## 结果','',
       f'采用启发式构造并校验得到 **{s["sorties"]} 架次**，交付全部 **80 箱**；',
       f'最晚返航时刻 **{s["makespan_s"]:.1f} s**（约2小时25分30秒），',
       f'运输总能耗 **{s["total_energy_kwh"]:.3f} kWh**。',
       '所有医疗物资、首批保障箱均满足硬时限，其他货箱也全部不晚于期望送达时间。',
       f'A、B、C机型分别执行{model_counts["A"]}、{model_counts["B"]}、{model_counts["C"]}架次。',
       f'最小硬时限余量为{min_hard:.1f} s；最小期望时间余量为{min_expected:.1f} s，出现在S003的三箱饮用水上。',
       '', '## 建模与求解工作','',
       '1. 从附件读取16个节点、80个逐箱需求、8架实体运输机和14组按机型专用的共享电池。将所有医疗物资的期望时间、所有首批保障箱的截止时间设为硬约束；其余期望时间用于衡量及时性。',
       '2. 对任意两个任务节点的直线航段逐格读取DEM，预计算巡航海拔、水平距离、爬升和下降高度。每一航段按照当时剩余载荷计算时间和能耗；到达一个服务区交付后，再以减轻后的载荷继续飞行。能耗口径延续问题一。',
       '3. 枚举单服务区的可行货箱组，先给3600 s内必须送达的8个服务区分配首轮任务。首轮4架A、2架B、2架C同时从O01开始准备；枚举机型分配，选取能多交付货箱且满足硬时限的方案。',
       '4. 后续按箱子的期望时间选择服务区，联合挑选可用实体机、已充满电的同型电池和可行货箱组。每架次结束后，按附件的两阶段充电函数计算该电池再次可用的时刻。',
       '5. 在单点排程上，将末轮的S013、S010两个货批合并成一个两点架次；逐箱时间、返航电量和资源占用仍满足全部约束。',
       '',
       '| 方案 | 架次 | 总能耗 kWh | 最晚返航 s | 晚于期望时间的货箱 |',
       '|---|---:|---:|---:|---:|',
       f'| 单点构造基线 | {b["sorties"]} | {b["total_energy_kwh"]:.3f} | {b["makespan_s"]:.1f} | {b["soft_tardy_boxes"]} |',
       f'| 合并多点后 | {s["sorties"]} | {s["total_energy_kwh"]:.3f} | {s["makespan_s"]:.1f} | {s["soft_tardy_boxes"]} |',
       '',
       '## 运输架次','',
       '| 架次 | 无人机 | 电池 | 机型 | 开始 s | 访问顺序 | 箱数 | 载重 kg | 返回 s | 能耗 kWh |',
       '|---|---|---|---|---:|---|---:|---:|---:|---:|']
for t in p['trips']:
    route=' → '.join(['O01']+[x['service'] for x in t['stops']]+['O01'])
    lines.append(f'| {t["id"]} | {t["drone"]} | {t["battery"]} | {t["model"]} | {t["load_start"]:.1f} | {route} | {len(t["boxes"])} | {t["mass"]:.1f} | {t["return_time"]:.1f} | {t["energy"]:.3f} |')
lines += ['', '## 资源使用与核验','',
          '| 无人机 | 机型 | 架次数 | 最后返回 s |',
          '|---|---|---:|---:|']
for d in sorted(p['drones'].values(),key=lambda x:x['id']):
    lines.append(f'| {d["id"]} | {d["model"]} | {len(d["sorties"])} | {d["available"]:.1f} |')
lines += ['',
          f'8架实体无人机均投入使用；14组电池均投入使用。各架次开始时刻不早于对应无人机返回和所选电池充至100%的时刻。',
          '独立核验重新计算了每一航段的时间、能耗、逐箱交付时刻及返航SOC，并检查80个箱号各出现一次、同型电池使用、无人机不重叠和电池充电不重叠。',
          '',
          '## 结果边界','',
          '这是满足题目问题二约束的一份启发式方案，不是22架次或65.533 kWh的全局最优证明。',
          '仅合并了一个多点架次，仍可能通过更深入的路线搜索和联合排程改进。',
          '问题二不包含通信保障；问题三需要重新检查运输全程通信并安排中继。',
          'S003的三箱饮用水距离期望时间只有约61秒，若调整飞行速度、地形或准备时间口径，应优先重新核验这三箱。',
          '']
(out/'d_q2_report.md').write_text('\n'.join(lines),encoding='utf-8')

deliveries=['# D题问题二逐箱交付明细','',
            '| 货箱编号 | 服务区 | 架次 | 交付完成 s | 期望送达 s | 硬截止 s | 时间余量 s |',
            '|---|---|---|---:|---:|---:|---:|']
for bid,v in sorted(p['deliveries'].items()):
    hard='—' if v['hard_deadline'] is None else f'{v["hard_deadline"]:.0f}'
    deliveries.append(f'| {bid} | {v["service"]} | {v["trip"]} | {v["time"]:.1f} | {v["expected"]:.0f} | {hard} | {v["expected"]-v["time"]:.1f} |')
(out/'d_q2_deliveries.md').write_text('\n'.join(deliveries)+'\n',encoding='utf-8')

(out/'d_q2_results.json').write_text(source.read_text(encoding='utf-8'),encoding='utf-8')
(out/'d_q2.py').write_text(Path(r'E:\codexh\2026-09-23\ai\work\d_q2.py').read_text(encoding='utf-8'),encoding='utf-8')
print('created D Q2 report, deliveries, results, code')
