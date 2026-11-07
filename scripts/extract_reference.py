import json
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_sheets(path: Path) -> list[list[list[str]]]:
    with ZipFile(path) as workbook:
        strings = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            tree = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            strings = ["".join(node.itertext()) for node in tree.findall("s:si", NS)]
        sheets = []
        for name in sorted(workbook.namelist()):
            if not name.startswith("xl/worksheets/sheet") or not name.endswith(".xml"):
                continue
            sheet = ET.fromstring(workbook.read(name))
            rows = []
            for row in sheet.findall("s:sheetData/s:row", NS):
                values = []
                for cell in row.findall("s:c", NS):
                    value = cell.findtext("s:v", default="", namespaces=NS)
                    if cell.get("t") == "s":
                        value = strings[int(value)]
                    elif cell.get("t") == "inlineStr":
                        value = "".join(cell.find("s:is", NS).itertext())
                    values.append(value)
                rows.append(values)
            sheets.append(rows)
        return sheets


reference = ROOT / "data/reference"
functions, industries = read_sheets(reference / "附件1.xlsx")
sources = read_sheets(reference / "附件2.xlsx")[0]
outputs = {
    "labels.json": {
        "functions": [row[1] for row in functions[1:]],
        "industries": [row[1] for row in industries[1:]],
    },
    "reference_sources.json": [
        {"category": row[0], "name": row[1], "url": row[2]} for row in sources[1:]
    ],
}
for name, content in outputs.items():
    with (reference / name).open("x", encoding="utf-8") as stream:
        json.dump(content, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
print("已导出 16 个功能标签、30 个行业标签和 20 个参考数据源。")
