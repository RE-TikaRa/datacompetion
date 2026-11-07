import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser(
    description="检查采集批次的日期、编号、快照与来源关系。"
)
parser.add_argument("--batch", required=True)
args = parser.parse_args()
sys.stdout.reconfigure(encoding="utf-8")

raw_folder = ROOT / "data/raw" / args.batch
processed_folder = ROOT / "data/processed" / args.batch
manifest = json.loads((raw_folder / "manifest.json").read_text(encoding="utf-8"))
records = [
    json.loads(line)
    for line in (processed_folder / "records.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
]
with (processed_folder / "records.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    csv_rows = list(csv.DictReader(stream))

errors = []
if len(records) != manifest["records"] or len(csv_rows) != len(records):
    errors.append("JSONL、CSV 与清单中的记录数不一致。")
counts = Counter(row["source_name"] for row in records)
if dict(counts) != manifest["source_counts"]:
    errors.append("按来源统计的记录数与清单不一致。")
start = datetime.fromisoformat(manifest["window_start"])
end = datetime.fromisoformat(manifest["window_end"])
seen_urls = set()
texts = []
raw_pages = {}
for index, (record, csv_row) in enumerate(zip(records, csv_rows, strict=True), 1):
    record_id = record["record_id"]
    if record["batch_id"] != args.batch or record_id != f"S{index:05d}":
        errors.append(f"{record_id}: 批次号或顺序编号有误。")
    if csv_row["记录编号"] != record_id or csv_row["内容"] != record["content_path"]:
        errors.append(f"{record_id}: CSV 与 JSONL 的记录关系有误。")
    if not start <= datetime.fromisoformat(record["published_at"]) <= end:
        errors.append(f"{record_id}: 发布时间超出批次时间窗。")
    key = (record["source_id"], record["source_url"])
    if key in seen_urls:
        errors.append(f"{record_id}: 来源链接重复。")
    seen_urls.add(key)
    text_path = (ROOT / record["content_path"]).resolve()
    if not text_path.is_relative_to(ROOT):
        errors.append(f"{record_id}: 正文路径超出项目范围。")
        continue
    text = text_path.read_text(encoding="utf-8").rstrip("\n")
    texts.append(text)
    if not text or len(text) != record["content_characters"]:
        errors.append(f"{record_id}: 正文为空或长度不一致。")
    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text):
        errors.append(f"{record_id}: 正文存在未处理的邮箱。")
    for raw_path in record["raw_response_paths"]:
        path = (ROOT / raw_path).resolve()
        if not path.is_relative_to(raw_folder):
            errors.append(f"{record_id}: 响应路径超出当前批次。")
            continue
        if raw_path not in raw_pages:
            raw_pages[raw_path] = json.loads(path.read_text(encoding="utf-8"))
        if not any(
            item["source_url"] == record["source_url"]
            for item in raw_pages[raw_path]["items"]
        ):
            errors.append(f"{record_id}: 在原始响应中找不到对应记录。")

result = {
    "batch_id": args.batch,
    "records": len(records),
    "csv_rows": len(csv_rows),
    "source_counts": dict(counts),
    "content_counts": dict(Counter(row["content_kind"] for row in records)),
    "published_min": min(row["published_at"] for row in records),
    "published_max": max(row["published_at"] for row in records),
    "raw_pages_referenced": len(raw_pages),
    "shorter_than_100_characters": sum(len(text) < 100 for text in texts),
    "exact_duplicate_texts": len(texts) - len(set(texts)),
    "records_without_heat": sum(
        not any(value is not None for value in row["metrics"].values())
        for row in records
    ),
    "source_errors": [
        {"source": source["name"], "error": source["error"]}
        for source in manifest["source_status"]
        if source["error"]
    ],
    "errors": errors,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors:
    sys.exit(1)
