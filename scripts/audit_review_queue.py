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

parser = argparse.ArgumentParser(description="检查人工复核清单与来源正文。")
parser.add_argument("--review", required=True, type=Path)
args = parser.parse_args()
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
review = args.review if args.review.is_absolute() else ROOT / args.review
review = review.resolve()
if not review.is_relative_to(ROOT / "results") or not review.is_dir():
    parser.error("复核目录必须位于项目 results 目录内。")
summary = read_json(review / "review_summary.json")
items = read_jsonl(review / "review_queue.jsonl")
with (review / "review_queue.csv").open(encoding="utf-8-sig", newline="") as stream:
    rows = list(csv.DictReader(stream))
errors = []
if len(rows) != len(items) or len(items) != summary["review_records"]:
    errors.append("CSV、JSONL 和复核清单数量不一致。")
judgement_run = ROOT / summary["judgement_run"]
judging = read_json(judgement_run / "judging.json")
cleaning_run = ROOT / judging["cleaning_run"]
records = {row["record_id"]: row for row in read_jsonl(cleaning_run / "records.jsonl")}
labels = read_json(ROOT / "data/reference/labels.json")
functions = set(labels["functions"])
industries = set(labels["industries"])
by_id = {row["record_id"]: row for row in items}
for item in items:
    if item["record_id"] not in records:
        errors.append(f"找不到清洗记录：{item['record_id']}")
        continue
    path = (cleaning_run / records[item["record_id"]]["content_path"]).resolve()
    if not path.is_relative_to(cleaning_run.resolve()) or not path.exists():
        errors.append(f"找不到正文快照：{item['record_id']}")
        continue
    text = path.read_text(encoding="utf-8")
    if any(quote not in text for quote in item["model_evidence"]):
        errors.append(f"模型证据不在正文中：{item['record_id']}")
    reviewed = item["human_is_opportunity"] is not None
    if reviewed != (item["review_status"] == "已复核"):
        errors.append(f"人工标签和复核状态不一致：{item['record_id']}")
    if item["human_is_opportunity"] is True:
        if item["human_functional_category"] not in functions:
            errors.append(f"人工功能类别不在官方标签中：{item['record_id']}")
        if item["human_industry"] not in industries:
            errors.append(f"人工所属行业不在官方标签中：{item['record_id']}")
    elif item["human_functional_category"] or item["human_industry"]:
        errors.append(f"人工非机会标签未清空分类：{item['record_id']}")
    csv_row = next((row for row in rows if row["记录编号"] == item["record_id"]), None)
    if csv_row is None:
        errors.append(f"CSV 中缺少记录：{item['record_id']}")
    else:
        human_value = (
            ""
            if item["human_is_opportunity"] is None
            else str(int(item["human_is_opportunity"]))
        )
        if csv_row["人工是否构成机会"] != human_value:
            errors.append(f"CSV 人工结果未同步：{item['record_id']}")
reviewed_count = sum(item["review_status"] == "已复核" for item in items)
if summary.get("reviewed_records", 0) != reviewed_count:
    errors.append("复核摘要中的已完成数量与记录不一致。")
result = {
    "review_records": len(items),
    "model_positive_records": summary["review_positive_records"],
    "model_negative_sample": summary["review_negative_records"],
    "source_counts": dict(Counter(item["source_name"] for item in items)),
    "content_counts": dict(Counter(item["content_kind"] for item in items)),
    "reviewed_records": reviewed_count,
    "pending_records": len(items) - reviewed_count,
    "errors": errors,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors:
    sys.exit(1)
