from pathlib import Path
import json

source=Path(r'E:\codexh\2026-09-23\ai\work\d_q1_run\d_q1_results.json')
out=Path(r'E:\codexh\2026-09-23\ai\outputs')
out.mkdir(parents=True,exist_ok=True)
p=json.loads(source.read_text(encoding='utf-8'))
chosen=p['strategies']['sorties_then_energy_then_time']
lines=[
    '# D题问题一初步计算结果',
    '',
    '## 结论',
    '',
    '按“先最少架次、再最低总能耗、最后最短累计作业时间”排序，80个不可拆货箱使用18个单服务区往返架次，',
    f'总运输能耗 {chosen["summary"]["energy_kwh"]:.3f} kWh，累计作业时间 {chosen["summary"]["work_time_s"]:.1f} s。',
    '累计作业时间是各架次时间之和，不是问题二中的多机并行完工时间。',
    '各服务区总质量除以该服务区最高安全载荷后向上取整，所得最少架次数下界合计为18，因此该方案的架次数达到下界。',
    '',
    '## 为什么没有A机型',
    '',
    '问题一明确不考虑实体无人机和共享电池调度。在本题这80箱数据里，逐一枚举了236种满足A机型载重、体积和返航电量的非空同区货箱组合。',
    '这236种组合换用B机型均仍满足约束，且每次运输的能耗和作业时间都更低；相同组合使用B机型可节约约0.166至0.605 kWh。',
    '因此A机型在问题一的既定目标下被B机型支配，不出现在推荐组批中是计算结果，不是漏掉了机型。',
    '问题二加入实体数量和时间安排后，A机型可能用于并行完成有时限的任务，需要重新优化。',
    '',
    '## 口径与假设',
    '',
    '- 每个架次只往返一个服务区；不考虑实体无人机、电池周转和通信调度。',
    '- 航段为两端点的水平直线；巡航海拔为所经DEM像元最大高程加50 m。',
    '- 水平距离用WGS84球面距离计算。',
    '- 依据题目给出的载荷相关等效航程，将水平能耗计算为 `电池可用能量 × 水平距离 / 等效航程`。',
    '- 爬升附加能耗按 `(含电池空载质量+当前载荷)×g×爬升高度/爬升效率` 换算为kWh；下降不另计附加能耗。',
    '- 题面未单列水平能耗与爬升能耗的展开式，上述两项是根据等效航程和给定效率采用的显式计算口径，正式论文应说明。',
    '',
    '## 各服务区最大安全载荷',
    '',
    '| 服务区 | 单程水平距离 km | A kg | B kg | C kg |',
    '|---|---:|---:|---:|---:|',
]
for s,r in p['routes'].items():
    values=[]
    for a in 'ABC':
        v=next(x['max_safe_payload_kg'] for x in p['safety'] if x['service']==s and x['model']==a)
        values.append('不可达' if v is None else f'{v:.2f}')
    lines.append(f'| {s} | {r["distance"]/1000:.2f} | {values[0]} | {values[1]} | {values[2]} |')
lines += ['', '## 推荐组批方案', '',
          '| 架次 | 服务区 | 机型 | 箱数 | 载重 kg | 体积 m³ | 能耗 kWh | 作业时间 s | 返航SOC |',
          '|---|---|---|---:|---:|---:|---:|---:|---:|']
for i,t in enumerate(chosen['trips'],1):
    lines.append(f'| Q1-{i:02d} | {t["service"]} | {t["model"]} | {len(t["boxes"])} | {t["mass"]:.1f} | {t["volume"]:.3f} | {t["energy"]:.3f} | {t["work_time"]:.1f} | {t["return_soc"]:.1f}% |')
lines += ['', '逐箱对应关系：', '']
for i,t in enumerate(chosen['trips'],1):
    lines.append(f'- Q1-{i:02d}：'+'、'.join(t['boxes']))
lines += ['', '## 全A、全B、全C与混合方案', '',
          '四种方案均以先最少架次、再最低能耗、最后最短累计作业时间为目标顺序，且均交付全部80箱。',
          '“全A”表示全部架次都使用A机型，不表示同时使用52架实体无人机；问题一不考虑实体机与电池排程。',
          '',
          '| 方案 | 架次 | 能耗 kWh | 累计作业时间 s |',
          '|---|---:|---:|---:|']
for model in 'ABC':
    x=p['fixed_model_results'][model]['summary']
    lines.append(f'| 全{model} | {x["sorties"]} | {x["energy_kwh"]:.3f} | {x["work_time_s"]:.1f} |')
x=chosen['summary']
lines.append(f'| 混合 | {x["sorties"]} | {x["energy_kwh"]:.3f} | {x["work_time_s"]:.1f} |')
lines += ['', '| 服务区 | 全A架次 | 全B架次 | 全C架次 | 混合架次 |',
          '|---|---:|---:|---:|---:|']
for service in p['routes']:
    vals=[sum(t['service']==service for t in p['fixed_model_results'][m]['trips']) for m in 'ABC']
    mix=sum(t['service']==service for t in chosen['trips'])
    lines.append(f'| {service} | {vals[0]} | {vals[1]} | {vals[2]} | {mix} |')
lines += ['', '全C与混合方案同为18架次，但混合方案把部分较轻的货批交给B机型，能耗减少约14.818 kWh。',
          '全B比全C节约约5.583 kWh，但增加17个架次；全A的架次、能耗和累计作业时间均最高。',
          '各固定机型方案的逐箱分配见另附详细文件和JSON。',
          '', '## 目标权衡与返航余量', '',
          '| 策略 | 架次 | 能耗 kWh | 累计作业时间 s |',
          '|---|---:|---:|---:|']
for key,label in [('sorties_then_energy_then_time','先最少架次'),('energy_then_sorties_then_time','先最低能耗'),('time_then_sorties_then_energy','先最短累计时间')]:
    x=p['strategies'][key]['summary']
    lines.append(f'| {label} | {x["sorties"]} | {x["energy_kwh"]:.3f} | {x["work_time_s"]:.1f} |')
lines += ['', '最低能耗方案多一次架次，仅节约约0.100 kWh，且累计作业时间增加约1662 s，因此推荐18架次方案。', '',
          '| 返航安全余量 | 架次 | 能耗 kWh | 累计作业时间 s | 受能量限制的机型-服务区组合数 |',
          '|---:|---:|---:|---:|---:|']
for x in p['sensitivity']:
    lines.append(f'| {x["reserve_fraction"]:.0%} | {x["sorties"]} | {x["energy_kwh"]:.3f} | {x["work_time_s"]:.1f} | {x["affected_max_loads"]} |')
lines += ['', '## 核验', '',
          '- 80个货箱编号恰好各出现一次，且每架次只装该服务区的货箱。',
          '- 18个架次均通过载质量、载货体积和返航电量检查。',
          '- 15条航线的DEM最高像元计算经过独立密采样对照；密采样结果未超过逐格遍历结果。',
          '',
          '这份结果只完成问题一。问题二的实体无人机、共享电池、时限与并行调度，以及问题三的通信约束，尚未加入。',
          '']
(out/'d_q1_report.md').write_text('\n'.join(lines),encoding='utf-8')
fixed=['# D题问题一全A全B全C详细组批','',
       '全部方案按最少架次、最低能耗、最短累计作业时间依次优化；每架次仅服务一个服务区。','']
for model in 'ABC':
    result=p['fixed_model_results'][model]
    summ=result['summary']
    fixed += [f'## 全{model}方案','',
              f'{summ["sorties"]}架次；总能耗{summ["energy_kwh"]:.3f} kWh；累计作业时间{summ["work_time_s"]:.1f} s。','',
              '| 架次 | 服务区 | 货箱编号 | 质量 kg | 体积 m³ | 能耗 kWh | 时间 s | 返航SOC |',
              '|---|---|---|---:|---:|---:|---:|---:|']
    for i,t in enumerate(result['trips'],1):
        fixed.append(f'| {model}-{i:02d} | {t["service"]} | {", ".join(t["boxes"])} | {t["mass"]:.1f} | {t["volume"]:.3f} | {t["energy"]:.3f} | {t["work_time"]:.1f} | {t["return_soc"]:.1f}% |')
    fixed.append('')
(out/'d_q1_fixed_models.md').write_text('\n'.join(fixed),encoding='utf-8')
(out/'d_q1_results.json').write_text(source.read_text(encoding='utf-8'),encoding='utf-8')
(out/'d_q1.py').write_text(Path(r'E:\codexh\2026-09-23\ai\work\d_q1.py').read_text(encoding='utf-8'),encoding='utf-8')
print('created',out/'d_q1_report.md',out/'d_q1_fixed_models.md',out/'d_q1_results.json',out/'d_q1.py')
