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
from opportunity.judging import exact_source_quote

parser = argparse.ArgumentParser(description="检查 AI 辅助复核结果和原人工队列。")
parser.add_argument("--run", required=True, type=Path)
parser.add_argument("--blind", action="store_true")
args = parser.parse_args()
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
run = args.run if args.run.is_absolute() else ROOT / args.run
run = run.resolve()
if not run.is_relative_to(ROOT / "results") or not run.is_dir():
    parser.error("判别运行目录必须位于项目 results 目录内。")
review = run / "review"
output = review / ("assistant_review_blind" if args.blind else "assistant_review")
job = read_json(output / "job.json")
queue = read_jsonl(review / "review_queue.jsonl")
items = read_jsonl(output / "assistant_review.jsonl")
summary = read_json(output / "assistant_review_summary.json")
attention = read_json(output / "human_attention_summary.json")
with (output / "assistant_review.csv").open(encoding="utf-8-sig", newline="") as stream:
    csv_rows = list(csv.DictReader(stream))
with (output / "human_attention.csv").open(encoding="utf-8-sig", newline="") as stream:
    attention_rows = list(csv.DictReader(stream))
labels = read_json(ROOT / "data/reference/labels.json")
functions = set(labels["functions"])
industries = set(labels["industries"])
queue_by_id = {row["record_id"]: row for row in queue}
item_by_id = {row["record_id"]: row for row in items}
errors = []
if len(queue) != len(items) or set(queue_by_id) != set(item_by_id):
    errors.append("AI 辅助复核没有覆盖复核队列的全部记录。")
expected_mode = "blind_to_automatic_judgement" if args.blind else "model_visible"
allowed_job_modes: set[str | None] = {expected_mode}
if not args.blind:
    allowed_job_modes.add(None)
if job.get("review_mode") not in allowed_job_modes:
    errors.append("复核运行模式与审计参数不一致。")
if args.blind and job.get("record_fields") != [
    "record_id",
    "source",
    "content_kind",
    "title",
    "content",
]:
    errors.append("盲复核输入字段包含了不允许的内容。")
if summary.get("review_mode") not in allowed_job_modes:
    errors.append("复核摘要中的运行模式不一致。")
for row in queue:
    if (
        row["human_is_opportunity"] is not None
        or row["human_functional_category"]
        or row["human_industry"]
        or row["human_notes"]
        or row["review_status"] != "待人工复核"
    ):
        errors.append(f"原人工队列已被 AI 辅助复核改写：{row['record_id']}")
for item in items:
    record_id = item["record_id"]
    queue_row = queue_by_id.get(record_id)
    if queue_row is None:
        continue
    if item["is_opportunity"]:
        if item["functional_category"] not in functions:
            errors.append(f"AI 辅助功能类别非法：{record_id}")
        if item["industry"] not in industries:
            errors.append(f"AI 辅助行业非法：{record_id}")
    elif item["functional_category"] or item["industry"]:
        errors.append(f"AI 辅助非机会记录带有分类：{record_id}")
    text = (ROOT / queue_row["content_path"]).read_text(encoding="utf-8")
    if any(exact_source_quote(quote, text) is None for quote in item["evidence"]):
        errors.append(f"AI 辅助证据不在正文中：{record_id}")
    if not item["rationale"].strip():
        errors.append(f"AI 辅助理由为空：{record_id}")
if summary["review_records"] != len(items):
    errors.append("AI 辅助复核摘要数量不一致。")
if len(csv_rows) != len(items) or {row["记录编号"] for row in csv_rows} != set(
    item_by_id
):
    errors.append("AI 辅助复核 CSV 与 JSONL 覆盖范围不一致。")
for row in csv_rows:
    item = item_by_id.get(row["记录编号"])
    if item is not None and row["AI辅助复核是否构成机会"] != str(
        int(item["is_opportunity"])
    ):
        errors.append(f"AI 辅助复核 CSV 判断不一致：{row['记录编号']}")
if summary["assistant_opportunities"] != sum(item["is_opportunity"] for item in items):
    errors.append("AI 辅助机会数量不一致。")
if len(attention_rows) != attention["records_requiring_human_attention"]:
    errors.append("真人优先查看清单数量不一致。")
expected_attention_ids = {
    item["record_id"]
    for item in items
    if item["boundary_case"]
    or bool(queue_by_id[item["record_id"]]["model_is_opportunity"])
    != item["is_opportunity"]
}
if {row["记录编号"] for row in attention_rows} != expected_attention_ids:
    errors.append("真人优先查看清单与分歧或边界记录不一致。")
result = {
    "run": run.relative_to(ROOT).as_posix(),
    "review_records": len(items),
    "assistant_opportunities": sum(item["is_opportunity"] for item in items),
    "boundary_records": sum(item["boundary_case"] for item in items),
    "human_attention_records": len(attention_rows),
    "source_counts": dict(Counter(row["source_name"] for row in queue)),
    "human_queue_untouched": not any(
        row["human_is_opportunity"] is not None
        or row["human_functional_category"]
        or row["human_industry"]
        or row["human_notes"]
        or row["review_status"] != "待人工复核"
        for row in queue
    ),
    "errors": errors,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors:
    sys.exit(1)
