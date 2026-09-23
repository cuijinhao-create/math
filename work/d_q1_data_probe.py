from pathlib import Path
from openpyxl import load_workbook
from PIL import Image
import sys
sys.stdout.reconfigure(encoding='utf-8')
root=Path(r'E:\数学建模\第二十三届中国研究生数学建模竞赛 - 中文题目\中文题目\D题\数据\无人机应急物资运输基础数据')
for name in ['调度中心与服务区.xlsx','运输无人机数据.xlsx','物资需求与配送时限.xlsx']:
    print('\n',name)
    wb=load_workbook(root/name,read_only=True,data_only=True)
    for ws in wb.worksheets:
        print('SHEET',ws.title)
        for n,r in enumerate(ws.values):
            if any(x is not None for x in r): print(tuple(r))
            if ws.title=='逐箱货箱清单' and n>=5: break
p=next(Path(r'E:\数学建模\第二十三届中国研究生数学建模竞赛 - 中文题目\中文题目\D题\数据\镇龙乡地理空间数据').rglob('*.tif'))
im=Image.open(p)
print('\nTIF',im.size,im.mode)
print('TAGS', {k:im.tag_v2.get(k) for k in [33550,33922,42113,34735]})
print('PIXEL sample', im.getpixel((700,700)))
