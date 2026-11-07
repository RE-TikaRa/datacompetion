import argparse
import json
import sys
from collections import Counter, defaultdict
from io import TextIOWrapper
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import (
    ROOT,
    read_json,
    read_jsonl,
    write_csv,
    write_json,
    write_jsonl,
)

parser = argparse.ArgumentParser(description="生成任务二人工复核队列。")
parser.add_argument("--run", required=True, type=Path)
parser.add_argument("--negative-sample", type=int, default=240)
args = parser.parse_args()
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")

run = args.run if args.run.is_absolute() else ROOT / args.run
run = run.resolve()
if not run.is_relative_to(ROOT / "results") or not run.is_dir():
    parser.error("判别运行目录必须位于项目 results 目录内。")
manifest = read_json(run / "judging.json")
if not manifest["complete"]:
    parser.error("只有完整判别运行才能生成复核队列。")
cleaning_run = ROOT / manifest["cleaning_run"]
records = {row["record_id"]: row for row in read_jsonl(cleaning_run / "records.jsonl")}
judgements = read_jsonl(run / "judgements.jsonl")
positives = [row for row in judgements if row["is_opportunity"]]
negatives = [row for row in judgements if not row["is_opportunity"]]
if args.negative_sample < 0:
    parser.error("negative-sample 不能为负数。")

buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
for judgement in negatives:
    record = records[judgement["record_id"]]
    buckets[(record["source_name"], record["content_kind"])].append(judgement)
for bucket in buckets.values():
    bucket.sort(key=lambda row: (row["confidence"], row["record_id"]))

selected_negatives = []
bucket_names = sorted(buckets)
while len(selected_negatives) < min(args.negative_sample, len(negatives)):
    progressed = False
    for bucket_name in bucket_names:
        bucket = buckets[bucket_name]
        if bucket:
            selected_negatives.append(bucket.pop(0))
            progressed = True
            if len(selected_negatives) >= args.negative_sample:
                break
    if not progressed:
        break

selected = sorted([*positives, *selected_negatives], key=lambda row: row["record_id"])
columns = [
    "采集批次号",
    "记录编号",
    "来源网站名称",
    "内容类型",
    "标题",
    "正文路径",
    "模型是否构成机会",
    "模型置信度",
    "需求信号",
    "AI核心性",
    "技术可实现性",
    "排除项",
    "模型功能类别",
    "模型所属行业",
    "模型证据",
    "模型排除理由",
    "人工是否构成机会",
    "人工功能类别",
    "人工所属行业",
    "人工备注",
]
rows = []
queue = []
for index, judgement in enumerate(selected, 1):
    record = records[judgement["record_id"]]
    row = {
        "queue_id": f"R{index:04d}",
        "batch_id": manifest["batch_id"],
        "record_id": judgement["record_id"],
        "source_name": record["source_name"],
        "content_kind": record["content_kind"],
        "title": record["title"],
        "content_path": (cleaning_run / record["content_path"])
        .relative_to(ROOT)
        .as_posix(),
        "model_is_opportunity": int(judgement["is_opportunity"]),
        "model_confidence": judgement["confidence"],
        "observable_demand": judgement["observable_demand"],
        "ai_core": judgement["ai_core"],
        "technically_feasible": judgement["technically_feasible"],
        "excluded": judgement["excluded"],
        "model_functional_category": judgement["functional_category"],
        "model_industry": judgement["industry"],
        "model_evidence": judgement["evidence"],
        "model_exclusion_reason": judgement["exclusion_reason"],
        "human_is_opportunity": None,
        "human_functional_category": "",
        "human_industry": "",
        "human_notes": "",
        "review_status": "待人工复核",
    }
    queue.append(row)
    rows.append(
        [
            manifest["batch_id"],
            judgement["record_id"],
            record["source_name"],
            record["content_kind"],
            record["title"],
            row["content_path"],
            int(judgement["is_opportunity"]),
            judgement["confidence"],
            judgement["observable_demand"],
            judgement["ai_core"],
            judgement["technically_feasible"],
            judgement["excluded"],
            judgement["functional_category"],
            judgement["industry"],
            "；".join(judgement["evidence"]),
            judgement["exclusion_reason"],
            "",
            "",
            "",
            "",
        ]
    )

output = run / "review"
output.mkdir(exist_ok=True)
write_csv(output / "review_queue.csv", columns, rows)
write_jsonl(output / "review_queue.jsonl", queue)
write_json(
    output / "review_summary.json",
    {
        "batch_id": manifest["batch_id"],
        "judgement_run": run.relative_to(ROOT).as_posix(),
        "total_records": len(judgements),
        "model_positive_records": len(positives),
        "model_negative_records": len(negatives),
        "review_records": len(queue),
        "review_positive_records": len(positives),
        "review_negative_records": len(selected_negatives),
        "negative_sampling": (
            "round_robin_by_source_and_content_kind_sorted_by_"
            "model_confidence_then_record_id"
        ),
        "source_counts": dict(Counter(row["source_name"] for row in queue)),
        "content_counts": dict(Counter(row["content_kind"] for row in queue)),
        "review_status": "待人工复核",
    },
)
print(
    json.dumps(
        {
            "output": output.relative_to(ROOT).as_posix(),
            "review_records": len(queue),
            "positives": len(positives),
            "sampled_negatives": len(selected_negatives),
        },
        ensure_ascii=False,
        indent=2,
    )
)
