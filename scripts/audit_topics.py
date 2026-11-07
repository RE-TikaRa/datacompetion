import argparse
import csv
import json
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.files import ROOT, read_json, read_jsonl

parser = argparse.ArgumentParser(description="检查候选或正式主题的成员和排序。")
parser.add_argument("--run", required=True, type=Path)
args = parser.parse_args()
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
run = args.run if args.run.is_absolute() else ROOT / args.run
run = run.resolve()
if not run.is_relative_to(ROOT / "results") or not run.is_dir():
    parser.error("分析运行目录必须位于项目 results 目录内。")
topics_data = read_json(run / "topics.json")
topics = topics_data["topics"]
quality = topics_data["quality"]
cleaning = ROOT / topics_data["cleaning_run"]
judgement_file = ROOT / topics_data.get(
    "judgement_file", f"{topics_data['judgement_run']}/judgements.jsonl"
)
judgements = read_jsonl(judgement_file)
judged_positive = {row["record_id"] for row in judgements if row["is_opportunity"]}
errors = []


def read_result(configured: str | None, default: str, legacy: str, label: str):
    names = list(dict.fromkeys(name for name in (configured, default, legacy) if name))
    for name in names:
        path = run / name
        if path.is_file():
            with path.open(encoding="utf-8-sig", newline="") as stream:
                return name, list(csv.DictReader(stream))
    errors.append(f"找不到{label}文件：{', '.join(names)}")
    return names[0], []


result3_name, result3 = read_result(
    topics_data.get("result3"), "candidate_result3.csv", "result3.csv", "result3"
)
result4_name, result4 = read_result(
    topics_data.get("result4"), "candidate_result4.csv", "result4.csv", "result4"
)
members = [record_id for topic in topics for record_id in topic["record_ids"]]
if len(members) != len(set(members)):
    errors.append("记录同时出现在多个主题中。")
if set(members) != judged_positive:
    errors.append("主题成员集合与机会记录集合不一致。")
if len(result3) != len(topics) or len(result4) != len(topics):
    errors.append("result3/result4 行数与主题数不一致。")
scores = [float(row["机会价值分"]) for row in result4]
if scores != sorted(scores, reverse=True):
    errors.append("result4 未按机会价值分降序排列。")
if [int(row["优先级"]) for row in result4] != list(range(1, len(result4) + 1)):
    errors.append("result4 优先级应从 1 开始连续编号。")
if result3 and list(result3[0]) != [
    "采集批次号",
    "主题簇编号",
    "主题簇名称",
    "功能类别",
    "所属行业",
    "簇内机会记录数",
    "来源覆盖",
    "簇内机会记录",
]:
    errors.append("result3 列名与官方模板不一致。")
if result4 and list(result4[0]) != [
    "采集批次号",
    "主题簇编号",
    "主题簇名称",
    "功能类别",
    "所属行业",
    "机会价值分",
    "优先级",
]:
    errors.append("result4 列名与官方模板不一致。")
records = {row["record_id"]: row for row in read_jsonl(cleaning / "records.jsonl")}
for topic in topics:
    if topic["record_count"] != len(topic["record_ids"]):
        errors.append(f"主题数量字段不一致：{topic['topic_id']}")
    if topic["source_names"] != sorted(
        {records[key]["source_name"] for key in topic["record_ids"]}
    ):
        errors.append(f"主题来源覆盖不一致：{topic['topic_id']}")
    dimensions = topic["dimension_scores"]
    if not all(value is None or 0 <= value <= 100 for value in dimensions.values()):
        errors.append(f"维度分超出 0 到 100：{topic['topic_id']}")
    topic_result = next(
        (row for row in result4 if row["主题簇编号"] == topic["topic_id"]), None
    )
    if (
        topic_result is None
        or float(topic_result["机会价值分"]) != topic["value_score"]
    ):
        errors.append(f"result4 分数与明细不一致：{topic['topic_id']}")

result = {
    "run": run.relative_to(ROOT).as_posix(),
    "status": topics_data["status"],
    "candidate_records": quality["candidate_records"],
    "topic_count": len(topics),
    "member_records": len(members),
    "noise_records": quality["noise_records"],
    "silhouette_score": quality["silhouette_score"],
    "result3": result3_name,
    "result4": result4_name,
    "single_record_topics": sum(topic["record_count"] == 1 for topic in topics),
    "errors": errors,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors:
    sys.exit(1)
