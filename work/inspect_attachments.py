from pathlib import Path
from zipfile import ZipFile
from collections import Counter

root = Path(r"E:\数学建模\第二十三届中国研究生数学建模竞赛 - 中文题目\中文题目")
for label in "ABEF":
    d = root / f"{label}题"
    print("\n", label)
    for p in d.iterdir():
        if p.is_file() and p.suffix.lower() == ".zip":
            with ZipFile(p) as z:
                files = [x for x in z.infolist() if not x.is_dir()]
                print(" ZIP", p.name, "count", len(files), "compressed_MB", round(p.stat().st_size/1e6, 1), "uncompressed_MB", round(sum(x.file_size for x in files)/1e6, 1))
                by_ext = Counter(Path(x.filename).suffix.lower() for x in files)
                print(" TYPES", by_ext.most_common(10))
                if label in "ABE":
                    top = sorted(files, key=lambda x:x.file_size, reverse=True)[:12]
                    for x in top: print(" LARGE",x.filename,round(x.file_size/1e6,1))
        elif p.is_dir() and label == "F" and p.name == "real_attachments":
            dirs = {}
            for x in p.rglob("*"):
                if x.is_file():
                    k = x.relative_to(p).parts[0]
                    count,size=dirs.get(k,(0,0))
                    dirs[k]=(count+1,size+x.stat().st_size)
            print(" F DIRS",[(k,v[0],round(v[1]/1e6,1)) for k,v in dirs.items()])
