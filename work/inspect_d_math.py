from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p=next(x for x in Path(r"E:\数学建模\第二十三届中国研究生数学建模竞赛 - 中文题目\中文题目\D题").glob("*.docx") if not x.name.startswith("~$"))
ns={"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main","m":"http://schemas.openxmlformats.org/officeDocument/2006/math"}
with ZipFile(p) as z: root=etree.fromstring(z.read("word/document.xml"))
body=root.find("w:body",ns)
for i,el in enumerate(body):
    if etree.QName(el).localname!="p": continue
    t="".join(el.xpath(".//w:t/text() | .//m:t/text()",namespaces=ns)).strip()
    if any(s in t for s in ["航段运输能耗","等效航程","爬升附加","水平巡航能耗"]):
        for q in list(body)[max(i-2,0):i+9]:
            if etree.QName(q).localname!="p":continue
            tt="".join(q.xpath(".//w:t/text() | .//m:t/text()",namespaces=ns)).strip()
            print("P",tt)
            for m in q.xpath(".//m:oMath",namespaces=ns):
                print("MATH",etree.tostring(m,encoding="unicode")[:6000])
