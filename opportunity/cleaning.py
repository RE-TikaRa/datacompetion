import csv
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

from opportunity.collection import clean_text, matches_keywords, plain_text
from opportunity.files import ROOT, read_json, write_csv, write_json, write_jsonl


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.startswith("utm_") and key not in {"spm", "fbclid", "gclid"}
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            urlencode(query),
            "",
        )
    )


def normalize_content(text: str) -> str:
    text = unicodedata.normalize("NFKC", clean_text(plain_text(text)))
    lines = []
    noise = re.compile(
        r"^(?:量子位\s*\|\s*公众号\s*QbitAI|.{1,20}发自\s*凹非寺|"
        r"扫码关注.*|点击(?:阅读原文|关注).*|未经授权.*|版权所有.*)$"
    )
    for line in text.splitlines():
        line = line.strip()
        if line and not noise.fullmatch(line):
            lines.append(line)
    return "\n\n".join(lines)


def quality_flags(record: dict) -> list[str]:
    flags = []
    if record["content_kind"] in {"description", "title_only"}:
        flags.append("incomplete_content")
    if len(record["text"]) < 100:
        flags.append("short_text")
    if not any(value is not None for value in record["metrics"].values()):
        flags.append("missing_heat")
    return flags


def duplicate_key(text: str) -> str:
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", text).casefold())


def shingles(text: str) -> set[str]:
    return {text[index : index + 4] for index in range(len(text) - 3)}


def deduplicate(records: list[dict]) -> tuple[list[dict], list[dict]]:
    retained: list[dict] = []
    by_text: dict[str, int] = {}
    duplicates = []
    for record in records:
        key = duplicate_key(record["text"])
        exact_duplicate = (
            len(key) >= 120
            and record["content_kind"] != "title_only"
            and key in by_text
        )
        if exact_duplicate:
            kept = retained[by_text[key]]
            kept["provenance"].extend(record["provenance"])
            duplicates.append(
                {
                    "kept_url": kept["source_url"],
                    "merged_url": record["source_url"],
                    "reason": "exact_content",
                    "similarity": 1.0,
                }
            )
        else:
            by_text[key] = len(retained)
            retained.append(record)
    long_indices = [
        index for index, row in enumerate(retained) if len(row["text"]) >= 400
    ]
    merged: set[int] = set()
    if len(long_indices) > 1:
        texts = [duplicate_key(retained[index]["text"]) for index in long_indices]
        vectors = TfidfVectorizer(
            analyzer="char", ngram_range=(4, 4), max_features=60000
        ).fit_transform(texts)
        neighbors = NearestNeighbors(metric="cosine", algorithm="brute").fit(vectors)
        candidates = neighbors.radius_neighbors(
            vectors, radius=0.025, return_distance=False
        )
        for position, matches in enumerate(candidates):
            kept_index = long_indices[position]
            if kept_index in merged:
                continue
            left = shingles(texts[position])
            for other in sorted(matches):
                merged_index = long_indices[other]
                if other <= position or merged_index in merged:
                    continue
                right = shingles(texts[other])
                score = len(left & right) / len(left | right)
                if score >= 0.95:
                    retained[kept_index]["provenance"].extend(
                        retained[merged_index]["provenance"]
                    )
                    duplicates.append(
                        {
                            "kept_url": retained[kept_index]["source_url"],
                            "merged_url": retained[merged_index]["source_url"],
                            "reason": "near_content",
                            "similarity": score,
                        }
                    )
                    merged.add(merged_index)
    return [
        row for index, row in enumerate(retained) if index not in merged
    ], duplicates


def clean_batch(batch: str, output: Path, root: Path = ROOT) -> dict:
    raw_folder = root / "data/raw" / batch
    config = read_json(raw_folder / "collection_config.json")
    start = datetime.fromisoformat(config["window_start"])
    end = datetime.fromisoformat(config["window_end"])
    relevance = re.compile(config["relevance_pattern"])
    keywords = config.get("keywords", [])
    by_url: dict[tuple[str, str], dict] = {}
    exclusions = Counter()
    received = 0
    for source in config["sources"]:
        for path in sorted((raw_folder / source["id"]).glob(f"{source['id']}-*.json")):
            for item in read_json(path)["items"]:
                received += 1
                published = datetime.fromisoformat(
                    item["published_at"].replace("Z", "+00:00")
                )
                if not start <= published <= end:
                    exclusions["outside_window"] += 1
                    continue
                text = normalize_content(item["title"] + "\n\n" + item["body"])
                if not text or not relevance.search(text):
                    exclusions["outside_ai_direction"] += 1
                    continue
                if not matches_keywords(text, keywords):
                    exclusions["outside_user_direction"] += 1
                    continue
                url = canonical_url(item["source_url"])
                provenance = {
                    "source_id": source["id"],
                    "source_name": source["name"],
                    "source_url": item["source_url"],
                    "native_id": item["native_id"],
                    "request_id": item["request_id"],
                    "raw_path": path.relative_to(root).as_posix(),
                    "published_at": published.isoformat(),
                    "content_kind": item["content_kind"],
                    "metrics": item["metrics"],
                }
                key = (source["id"], url)
                if key in by_url:
                    exclusions["duplicate_url"] += 1
                    record = by_url[key]
                    record["provenance"].append(provenance)
                    if item["content_kind"] == "readme":
                        record["text"] = text
                        record["content_kind"] = "readme"
                    continue
                by_url[key] = {
                    "batch_id": batch,
                    "source_id": source["id"],
                    "source_name": source["name"],
                    "source_url": url,
                    "title": item["title"],
                    "published_at": published.isoformat(),
                    "collected_at": item["collected_at"],
                    "record_kind": item["record_kind"],
                    "content_kind": item["content_kind"],
                    "metrics": item["metrics"],
                    "license": item.get("license"),
                    "text": text,
                    "provenance": [provenance],
                }
    ordered = sorted(
        by_url.values(),
        key=lambda row: (row["source_id"], row["published_at"], row["source_url"]),
    )
    records, duplicates = deduplicate(ordered)
    text_folder = output / "text"
    text_folder.mkdir()
    for index, record in enumerate(records, 1):
        record["record_id"] = f"S{index:05d}"
        record["content_path"] = f"text/{batch}_{record['record_id']}.md"
        record["content_characters"] = len(record["text"])
        record["sources"] = sorted(
            {entry["source_name"] for entry in record["provenance"]}
        )
        record["quality_flags"] = quality_flags(record)
        with (output / record["content_path"]).open("x", encoding="utf-8") as stream:
            stream.write(record["text"] + "\n")
    with (root / "templates/results/result1.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        columns = next(csv.reader(stream))
    rows = [
        [
            batch,
            row["record_id"],
            "、".join(row["sources"]),
            row["source_url"],
            "./" + row["content_path"],
            row["published_at"],
            json.dumps(
                {entry["source_id"]: entry["metrics"] for entry in row["provenance"]},
                ensure_ascii=False,
            ),
        ]
        for row in records
    ]
    write_csv(output / "result1.csv", columns, rows)
    write_jsonl(
        output / "records.jsonl",
        [
            {key: value for key, value in row.items() if key != "text"}
            for row in records
        ],
    )
    report = {
        "batch_id": batch,
        "direction": config["direction"],
        "window_start": config["window_start"],
        "window_end": config["window_end"],
        "raw_record_appearances": received,
        "url_unique_records": len(by_url),
        "retained_records": len(records),
        "exclusions": dict(exclusions),
        "duplicates": duplicates,
        "source_counts": dict(Counter(row["source_name"] for row in records)),
        "content_counts": dict(Counter(row["content_kind"] for row in records)),
        "quality_flags": dict(
            Counter(flag for row in records for flag in row["quality_flags"])
        ),
        "near_duplicate_method": "char4_tfidf_cosine<=0.025_and_jaccard>=0.95",
    }
    write_json(output / "cleaning.json", report)
    return report
