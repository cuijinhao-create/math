from pathlib import Path
from zipfile import ZipFile
import json

root = Path(r"E:\数学建模\第二十三届中国研究生数学建模竞赛 - 中文题目\中文题目")
za = next((root / "A题").glob("*.zip"))
with ZipFile(za) as z:
    cases = [n for n in z.namelist() if n.startswith("data/case_") and n.endswith(".json")]
    stats=[]
    for name in cases:
        d=json.loads(z.read(name))
        stats.append((name,len(d.get("ops",[])),len(d.get("tensors",[])),len(d.get("edges",[]))))
    print("A CASES",len(cases),"max",max(stats,key=lambda x:x[1]),"min",min(stats,key=lambda x:x[1]))
ze = next((root / "E题").glob("*.zip"))
with ZipFile(ze) as z:
    for x in z.infolist():
        if x.filename.lower().endswith(".pkl") and x.file_size > 1e7:
            print("E FEATURE",x.filename,round(x.file_size/1e6,1),"MB")
