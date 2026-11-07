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
    read_jsonl,
    write_csv,
    write_json,
)
from opportunity.topics import cluster_topics, score_topics

parser = argparse.ArgumentParser(description="聚合候选机会并生成候选 result3/result4。")
parser.add_argument("--cleaning-run", required=True, type=Path)
parser.add_argument("--judgement-run", required=True, type=Path)
parser.add_argument("--min-cluster-size", type=int, default=5)
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

topics, quality = cluster_topics(
    cleaning_run, judgement_run, ROOT, args.min_cluster_size
)
cleaned = {row["record_id"]: row for row in read_jsonl(cleaning_run / "records.jsonl")}
judged = {
    row["record_id"]: row for row in read_jsonl(judgement_run / "judgements.jsonl")
}
topics, scoring = score_topics(topics, cleaned, judged)
output = new_run(cleaned[next(iter(cleaned))]["batch_id"])

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
write_csv(output / "result3.csv", columns3, result3_rows)
write_csv(output / "result4.csv", columns4, result4_rows)
write_json(
    output / "topics.json",
    {
        "batch_id": topics[0]["batch_id"] if topics else None,
        "status": "候选结果，基于待复核模型机会标签",
        "cleaning_run": cleaning_run.relative_to(ROOT).as_posix(),
        "judgement_run": judgement_run.relative_to(ROOT).as_posix(),
        "quality": quality,
        "topics": topics,
    },
)
write_json(
    output / "scoring.json",
    {
        "batch_id": topics[0]["batch_id"] if topics else None,
        "status": "候选结果，待人工复核",
        "scoring": scoring,
        "ranking": [
            {
                "topic_id": topic["topic_id"],
                "value_score": topic["value_score"],
                "priority": topic["priority"],
            }
            for topic in topics
        ],
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
            "industry_counts": dict(Counter(topic["industry"] for topic in topics)),
            "review_status": "候选结果，待人工复核",
        },
        ensure_ascii=False,
        indent=2,
    )
)
