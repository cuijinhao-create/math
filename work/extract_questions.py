from pathlib import Path
from zipfile import ZipFile
from lxml import etree

root = Path(r"E:\数学建模\第二十三届中国研究生数学建模竞赛 - 中文题目\中文题目")
out = Path(r"E:\codexh\2026-09-23\ai\work\questions")
out.mkdir(parents=True, exist_ok=True)
ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
      "m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}

for label in "ABCDEF":
    path = next(p for p in (root / f"{label}题").glob("*.docx") if not p.name.startswith("~$"))
    print("reading", path)
    with ZipFile(path) as z:
        doc = etree.fromstring(z.read("word/document.xml"))
        images = sum(n.startswith("word/media/") for n in z.namelist())
    body = doc.find("w:body", ns)
    lines = []
    for el in body:
        tag = etree.QName(el).localname
        if tag == "p":
            chunks = el.xpath(".//w:t/text() | .//m:t/text()", namespaces=ns)
            line = "".join(chunks).strip()
            if line:
                lines.append(line)
        elif tag == "tbl":
            lines.append("[TABLE]")
            for row in el.findall("w:tr", ns):
                cells = []
                for cell in row.findall("w:tc", ns):
                    cells.append("".join(cell.xpath(".//w:t/text() | .//m:t/text()", namespaces=ns)).strip())
                lines.append(" | ".join(cells))
            lines.append("[/TABLE]")
    target = out / f"{label}.txt"
    target.write_text("\n".join(lines), encoding="utf-8")
    print(label, "paragraphs_or_rows", len(lines), "chars", sum(map(len,lines)), "images", images, "text", target)
