import argparse
import csv
import json
import sys
from collections import Counter
from io import TextIOWrapper
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import (
    ROOT,
    new_run,
    read_json,
    read_jsonl,
    write_csv,
    write_json,
)
from opportunity.topics import cluster_topics, score_sensitivity, score_topics

parser = argparse.ArgumentParser(
    description="聚合机会主题并生成候选或正式 result3/result4。"
)
parser.add_argument("--cleaning-run", required=True, type=Path)
parser.add_argument("--judgement-run", required=True, type=Path)
parser.add_argument("--min-cluster-size", type=int, default=5)
parser.add_argument("--judgement-file", type=Path)
parser.add_argument("--formal", action="store_true")
parser.add_argument(
    "--label-source",
    choices=("model", "assistant-proxy", "human"),
    default="model",
)
args = parser.parse_args()
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
cleaning_run = (
    args.cleaning_run if args.cleaning_run.is_absolute() else ROOT / args.cleaning_run
)
judgement_run = (
    args.judgement_run
    if args.judgement_run.is_absolute()
    else ROOT / args.judgement_run
)
cleaning_run = cleaning_run.resolve()
judgement_run = judgement_run.resolve()
if not cleaning_run.is_relative_to(
    ROOT / "results"
) or not judgement_run.is_relative_to(ROOT / "results"):
    parser.error("输入运行目录必须位于项目 results 目录内。")
if args.min_cluster_size < 2:
    parser.error("min-cluster-size 至少为 2。")
if args.formal and args.label_source == "assistant-proxy":
    parser.error("正式模式不能使用 AI 代理标签。")
if not args.formal and args.label_source == "human":
    parser.error("human 标签来源只能用于正式模式。")
label_source = "human" if args.formal else args.label_source

judgement_file = args.judgement_file
if judgement_file is None:
    judgement_file = judgement_run / "judgements.jsonl"
elif not judgement_file.is_absolute():
    judgement_file = judgement_run / judgement_file
judgement_file = judgement_file.resolve()
if not judgement_file.is_relative_to(ROOT / "results") or not judgement_file.exists():
    parser.error("judgement-file 必须位于项目 results 目录内。")
judgement_rows = read_jsonl(judgement_file)
if args.formal:
    final_review = judgement_file.parent / "final_review.json"
    if (
        not final_review.exists()
        or read_json(final_review).get("model_labels_not_reviewed", 1) != 0
    ):
        parser.error("正式模式要求全量人工复核完成。")
    final_rows = read_jsonl(judgement_file)
    if len(final_rows) != read_json(final_review)["records"]:
        parser.error("人工确认文件没有覆盖完整批次。")
    cleaning_records = read_jsonl(cleaning_run / "records.jsonl")
    final_ids = [row["record_id"] for row in final_rows]
    cleaning_ids = {row["record_id"] for row in cleaning_records}
    if len(final_ids) != len(set(final_ids)) or set(final_ids) != cleaning_ids:
        parser.error("人工复核结果与清洗批次的记录数不一致。")
topics, quality = cluster_topics(
    cleaning_run, judgement_run, ROOT, args.min_cluster_size, judgement_rows
)
cleaned = {row["record_id"]: row for row in read_jsonl(cleaning_run / "records.jsonl")}
judged = {row["record_id"]: row for row in judgement_rows}
topics, scoring = score_topics(topics, cleaned, judged)
output = new_run(cleaned[next(iter(cleaned))]["batch_id"])
status_by_source = {
    "model": "候选结果，基于待复核模型机会标签",
    "assistant-proxy": "AI代理复核候选结果，待真人确认",
    "human": "正式结果",
}
status = status_by_source[label_source]
quality["review_status"] = status
scoring["review_status"] = status

result3_rows = [
    [
        topic["batch_id"],
        topic["topic_id"],
        topic["topic_name"],
        topic["functional_category"],
        topic["industry"],
        topic["record_count"],
        "、".join(topic["source_names"]),
        "；".join(topic["record_ids"]),
    ]
    for topic in topics
]
result4_rows = [
    [
        topic["batch_id"],
        topic["topic_id"],
        topic["topic_name"],
        topic["functional_category"],
        topic["industry"],
        topic["value_score"],
        topic["priority"],
    ]
    for topic in topics
]
with (ROOT / "templates/results/result3.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    columns3 = next(csv.reader(stream))
with (ROOT / "templates/results/result4.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    columns4 = next(csv.reader(stream))
result3_name, result4_name = (
    ("result3.csv", "result4.csv")
    if args.formal
    else (
        ("proxy_result3.csv", "proxy_result4.csv")
        if label_source == "assistant-proxy"
        else ("candidate_result3.csv", "candidate_result4.csv")
    )
)
write_csv(output / result3_name, columns3, result3_rows)
write_csv(output / result4_name, columns4, result4_rows)
write_json(
    output / "topics.json",
    {
        "batch_id": topics[0]["batch_id"] if topics else None,
        "status": status,
        "label_source": label_source,
        "result3": result3_name,
        "result4": result4_name,
        "cleaning_run": cleaning_run.relative_to(ROOT).as_posix(),
        "judgement_run": judgement_run.relative_to(ROOT).as_posix(),
        "judgement_file": judgement_file.relative_to(ROOT).as_posix(),
        "quality": quality,
        "topics": topics,
    },
)
write_json(
    output / "scoring.json",
    {
        "batch_id": topics[0]["batch_id"] if topics else None,
        "status": status,
        "label_source": label_source,
        "scoring": scoring,
        "ranking": [
            {
                "topic_id": topic["topic_id"],
                "value_score": topic["value_score"],
                "priority": topic["priority"],
            }
            for topic in topics
        ],
        "sensitivity": score_sensitivity(topics),
    },
)
print(
    json.dumps(
        {
            "output": output.relative_to(ROOT).as_posix(),
            "candidate_records": quality["candidate_records"],
            "topic_count": len(topics),
            "noise_records": quality["noise_records"],
            "silhouette_score": quality["silhouette_score"],
            "result3": result3_name,
            "result4": result4_name,
            "industry_counts": dict(Counter(topic["industry"] for topic in topics)),
            "review_status": status,
        },
        ensure_ascii=False,
        indent=2,
    )
)
