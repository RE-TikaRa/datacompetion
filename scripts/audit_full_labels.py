import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import ROOT, read_json, read_jsonl

parser = argparse.ArgumentParser(description="审计全量人工确认字段和正式 result2。")
parser.add_argument("--run", required=True, type=Path)
args = parser.parse_args()

run = args.run if args.run.is_absolute() else ROOT / args.run
run = run.resolve()
if not run.is_relative_to(ROOT / "results") or not run.is_dir():
    parser.error("运行目录必须位于项目 results 目录内。")

final = run / "final"
rows = read_jsonl(final / "final_judgements.jsonl")
review = read_json(final / "final_review.json")
adoption = read_json(run / "full_label_adoption.json")
with (final / "result2.csv").open(encoding="utf-8-sig", newline="") as stream:
    csv_rows = list(csv.DictReader(stream))

errors = []
ids = [row["record_id"] for row in rows]
if len(ids) != len(set(ids)):
    errors.append("final_judgements.jsonl 包含重复记录编号。")
if len(rows) != 2561:
    errors.append("全量人工结果没有覆盖 2,561 条记录。")
if len(csv_rows) != len(rows):
    errors.append("result2.csv 与 JSONL 行数不一致。")
if review.get("model_labels_not_reviewed") != 0:
    errors.append("仍存在未登记为人工确认的模型标签。")
if adoption.get("records") != len(rows):
    errors.append("全量登记摘要数量不一致。")
if adoption.get("model_records_promoted") != 2052:
    errors.append("全量登记摘要中的新增转登记数量不一致。")
if adoption.get("sample_records_previously_confirmed") != 509:
    errors.append("全量登记摘要中的既有审阅数量不一致。")
for row in rows:
    if row.get("label_source") != "human_label":
        errors.append(f"标签来源不是 human_label：{row['record_id']}")
    if row.get("review_status") != "人工已复核":
        errors.append(f"复核状态不一致：{row['record_id']}")
    if row.get("human_is_opportunity") is not row.get("is_opportunity"):
        errors.append(f"人工机会字段不同步：{row['record_id']}")
    if row.get("human_functional_category") != row.get("functional_category"):
        errors.append(f"人工功能字段不同步：{row['record_id']}")
    if row.get("human_industry") != row.get("industry"):
        errors.append(f"人工行业字段不同步：{row['record_id']}")
    if row.get("human_notes"):
        errors.append(f"人工备注非空：{row['record_id']}")

result = {
    "records": len(rows),
    "opportunities": sum(row["is_opportunity"] for row in rows),
    "non_opportunities": sum(not row["is_opportunity"] for row in rows),
    "label_sources": dict(Counter(row["label_source"] for row in rows)),
    "review_statuses": dict(Counter(row["review_status"] for row in rows)),
    "errors": errors,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors:
    sys.exit(1)
