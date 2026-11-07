import argparse
import csv
import json
import sys
from collections import Counter
from io import TextIOWrapper
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import ROOT, read_json, read_jsonl

parser = argparse.ArgumentParser(
    description="检查 result2 与清洗记录和证据的对应关系。"
)
parser.add_argument("--run", required=True, type=Path)
args = parser.parse_args()
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
run = args.run if args.run.is_absolute() else ROOT / args.run
run = run.resolve()
if not run.is_relative_to(ROOT) or not run.is_dir():
    parser.error("运行目录必须位于项目目录内。")

manifest = read_json(run / "judging.json")
cleaning_run = ROOT / manifest["cleaning_run"]
cleaned = read_jsonl(cleaning_run / "records.jsonl")
cleaned_by_id = {record["record_id"]: record for record in cleaned}
judgements_name = (
    "judgements.jsonl" if manifest["complete"] else "judgements.preview.jsonl"
)
csv_name = "result2.csv" if manifest["complete"] else "result2.preview.csv"
judgements = read_jsonl(run / judgements_name)
with (run / csv_name).open(encoding="utf-8-sig", newline="") as stream:
    rows = list(csv.DictReader(stream))
with (ROOT / "templates/results/result2.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    columns = next(csv.reader(stream))

errors = []
if len(rows) != len(judgements) or len(rows) != manifest["records"]:
    errors.append("CSV、判别记录和清单数量不一致。")
if rows and list(rows[0]) != columns:
    errors.append("CSV 列名与 result2 官方模板不一致。")
ids = [item["record_id"] for item in judgements]
if len(ids) != len(set(ids)):
    errors.append("判别记录编号重复。")
if any(record_id not in cleaned_by_id for record_id in ids):
    errors.append("判别记录中含有清洗记录之外的编号。")
if manifest["complete"] and set(ids) != set(cleaned_by_id):
    errors.append("完整判别运行没有覆盖全部清洗记录。")
functions = set(read_json(ROOT / "data/reference/labels.json")["functions"])
industries = set(read_json(ROOT / "data/reference/labels.json")["industries"])
for item, row in zip(judgements, rows, strict=True):
    record_id = item["record_id"]
    decision = (
        item["observable_demand"]
        and item["ai_core"]
        and item["technically_feasible"]
        and not item["excluded"]
    )
    if item["is_opportunity"] != decision or row["是否构成机会"] != str(int(decision)):
        errors.append(f"机会判定不符合四项规则：{record_id}")
    if not 0 <= item["confidence"] <= 1 or not isinstance(item["confidence"], float):
        errors.append(f"置信度格式错误：{record_id}")
    if decision:
        if item["functional_category"] not in functions:
            errors.append(f"功能类别不在官方标签中：{record_id}")
        if item["industry"] not in industries:
            errors.append(f"所属行业不在官方标签中：{record_id}")
        if not item["evidence"]:
            errors.append(f"机会记录缺少依据：{record_id}")
    elif item["functional_category"] or item["industry"]:
        errors.append(f"非机会记录带有机会分类：{record_id}")
    source_text = (cleaning_run / cleaned_by_id[record_id]["content_path"]).read_text(
        encoding="utf-8"
    )
    if any(quote not in source_text for quote in item["evidence"]):
        errors.append(f"证据摘录不在正文中：{record_id}")

result = {
    "run": run.relative_to(ROOT).as_posix(),
    "records": len(judgements),
    "complete": manifest["complete"],
    "review_status": manifest["review_status"],
    "opportunity_counts": dict(
        Counter(str(item["is_opportunity"]) for item in judgements)
    ),
    "errors": errors,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors:
    sys.exit(1)
