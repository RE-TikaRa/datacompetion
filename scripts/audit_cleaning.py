import argparse
import csv
import json
import sys
from collections import Counter
from io import TextIOWrapper
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
parser = argparse.ArgumentParser(
    description="检查任务一清洗运行的 CSV、快照和记录关系。"
)
parser.add_argument("--run", required=True, type=Path)
args = parser.parse_args()
run = args.run if args.run.is_absolute() else ROOT / args.run
run = run.resolve()
if not run.is_relative_to(ROOT) or not run.is_dir():
    parser.error("运行目录必须位于项目目录内。")

report = json.loads((run / "cleaning.json").read_text(encoding="utf-8"))
records = [
    json.loads(line)
    for line in (run / "records.jsonl").read_text(encoding="utf-8").splitlines()
]
with (run / "result1.csv").open(encoding="utf-8-sig", newline="") as stream:
    rows = list(csv.DictReader(stream))
errors = []
if len(records) != len(rows) or len(records) != report["retained_records"]:
    errors.append("CSV、JSONL 与清洗报告的记录数不一致。")
with (ROOT / "templates/results/result1.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    columns = next(csv.reader(stream))
if rows and list(rows[0]) != columns:
    errors.append("CSV 列名与 result1 官方模板不一致。")
seen_ids = set()
seen_urls = set()
raw_pages = {}
for index, (record, row) in enumerate(zip(records, rows, strict=True), 1):
    expected_id = f"S{index:05d}"
    if record["record_id"] != expected_id or row["记录编号"] != expected_id:
        errors.append(f"记录编号错误：{expected_id}")
    if row["采集批次号"] != report["batch_id"]:
        errors.append(f"批次号错误：{expected_id}")
    source_names = sorted(record["sources"])
    if row["来源网站名称"] != "、".join(source_names):
        errors.append(f"来源列表不一致：{expected_id}")
    if row["内容"] != "./" + record["content_path"]:
        errors.append(f"正文引用不一致：{expected_id}")
    source_key = (record["source_url"], tuple(source_names))
    if source_key in seen_urls:
        errors.append(f"来源链接重复：{expected_id}")
    seen_urls.add(source_key)
    expected_metrics = {
        item["source_id"]: item["metrics"] for item in record["provenance"]
    }
    if json.loads(row["热度指标（如浏览数、点赞数、讨论数等）"]) != expected_metrics:
        errors.append(f"热度指标与来源记录不一致：{expected_id}")
    if record["record_id"] in seen_ids:
        errors.append(f"记录编号重复：{expected_id}")
    seen_ids.add(record["record_id"])
    content = (run / record["content_path"]).resolve()
    if not content.is_relative_to(run) or not content.exists():
        errors.append(f"正文路径无效：{expected_id}")
        continue
    if (
        len(content.read_text(encoding="utf-8").rstrip("\n"))
        != record["content_characters"]
    ):
        errors.append(f"正文长度不一致：{expected_id}")
    for item in record["provenance"]:
        raw = (ROOT / item["raw_path"]).resolve()
        if not raw.is_relative_to(ROOT / "data/raw"):
            errors.append(f"原始记录路径越界：{expected_id}")
            continue
        if item["raw_path"] not in raw_pages:
            raw_pages[item["raw_path"]] = json.loads(raw.read_text(encoding="utf-8"))
        if not any(
            raw_item["native_id"] == item["native_id"]
            and raw_item["source_url"] == item["source_url"]
            for raw_item in raw_pages[item["raw_path"]]["items"]
        ):
            errors.append(f"原始来源证据不存在：{expected_id}")

result = {
    "run": run.relative_to(ROOT).as_posix(),
    "records": len(records),
    "text_files": len(list((run / "text").glob("*.md"))),
    "source_counts": dict(Counter(row["来源网站名称"] for row in rows)),
    "quality_flags": report["quality_flags"],
    "duplicate_groups": len(report["duplicates"]),
    "raw_response_pages": len(raw_pages),
    "errors": errors,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors:
    sys.exit(1)
