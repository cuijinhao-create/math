from pathlib import Path
from collections import defaultdict
from openpyxl import load_workbook
import sys
sys.stdout.reconfigure(encoding='utf-8')
root=Path(r'E:\数学建模\第二十三届中国研究生数学建模竞赛 - 中文题目\中文题目\D题\数据\无人机应急物资运输基础数据')
ws=load_workbook(root/'物资需求与配送时限.xlsx',read_only=True,data_only=True)['逐箱货箱清单']
by=defaultdict(list)
for r in list(ws.values)[1:]:
    if r[0]:by[r[1]].append(r)
for s,rows in by.items():
    urgent=[x for x in rows if x[2]=='医疗物资' or x[5]=='是']
    print(s,'total',len(rows),'mass',sum(x[3] for x in rows),'urgent',len(urgent),'urgent_mass',sum(x[3] for x in urgent),'urgent_deadlines',[x[6] if x[5]=='是' else x[7] for x in urgent])
