import argparse
import csv
import json
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import ROOT, read_json, read_jsonl
from opportunity.review_adoption import adoption_errors

parser = argparse.ArgumentParser(description="检查人工确认样本与标签来源记录。")
parser.add_argument("--run", required=True, type=Path)
args = parser.parse_args()
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
run = args.run if args.run.is_absolute() else ROOT / args.run
run = run.resolve()
if not run.is_relative_to(ROOT / "results") or not run.is_dir():
    parser.error("判别运行目录必须位于项目 results 目录内。")

review = run / "review"
adoption = read_json(review / "human_adoption.json")
queue = read_jsonl(review / "review_queue.jsonl")
proxy = read_jsonl(review / "assistant_adjudication" / "assistant_review_proxy.jsonl")
summary = read_json(review / "review_summary.json")
with (review / "review_queue.csv").open(encoding="utf-8-sig", newline="") as stream:
    csv_rows = list(csv.DictReader(stream))

errors = adoption_errors(queue, proxy, adoption)
queue_by_id = {row["record_id"]: row for row in queue}
csv_by_id = {row["记录编号"]: row for row in csv_rows}
if len(csv_rows) != len(queue) or set(csv_by_id) != set(queue_by_id):
    errors.append("人工复核 CSV 与 JSONL 范围不一致。")
for record_id, item in queue_by_id.items():
    csv_row = csv_by_id.get(record_id)
    if csv_row is None:
        continue
    expected = str(int(item["human_is_opportunity"]))
    if csv_row["人工是否构成机会"] != expected:
        errors.append(f"CSV 人工机会标签不同步：{record_id}")
    if csv_row["人工功能类别"] != item["human_functional_category"]:
        errors.append(f"CSV 人工功能类别不同步：{record_id}")
    if csv_row["人工所属行业"] != item["human_industry"]:
        errors.append(f"CSV 人工行业不同步：{record_id}")
    if csv_row["人工备注"]:
        errors.append(f"CSV 人工备注包含模型说明：{record_id}")
if summary.get("reviewed_records") != len(queue):
    errors.append("复核摘要已复核数量不一致。")
if summary.get("pending_records") != 0:
    errors.append("已确认队列仍列有待复核记录。")

result = {
    "reviewed_records": len(queue),
    "human_opportunities": adoption["opportunities"],
    "human_non_opportunities": adoption["non_opportunities"],
    "labels_changed_by_reviewer": adoption["labels_changed_by_reviewer"],
    "independent_human_annotation": adoption["independent_human_annotation"],
    "ai_suggestion_text_copied_to_human_notes": adoption[
        "ai_suggestion_text_copied_to_human_notes"
    ],
    "errors": errors,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors:
    sys.exit(1)
