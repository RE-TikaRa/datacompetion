import argparse
import base64
import csv
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta, timezone
from datetime import time as day_time
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCAL = timezone(timedelta(hours=8))


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.ignored += 1
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "pre"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.ignored -= 1
        if tag in {"p", "div", "li", "pre"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            self.parts.append(data)


def plain_text(value: str) -> str:
    parser = TextParser()
    parser.feed(value)
    text = html.unescape("".join(parser.parts))
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[邮箱已隐去]", text)
    text = re.sub(r"(?<!\d)(?:\+?86[ -]?)?1[3-9]\d{9}(?!\d)", "[电话已隐去]", text)
    text = re.sub(r"(?<!\w)\+\d[\d ()-]{7,}\d(?!\w)", "[电话已隐去]", text)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP已隐去]", text)
    text = re.sub(r"(?<!\w)@[A-Za-z0-9_-]+", "[用户提及已隐去]", text)
    text = re.sub(r"(?im)^(?:作者|编辑|Author|Editor)\s*[:：].*$", "", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def clean_text(value: str) -> str:
    text = re.sub(r"https?://[^\s<>\[\]()]+", "", value)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def dump_json(path: Path, data: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


class Collector:
    def __init__(self, source: dict, folder: Path, start: datetime, end: datetime):
        self.source = source
        self.folder = folder / source["id"]
        self.folder.mkdir()
        self.start = start
        self.end = end
        self.last_request = 0.0
        self.requests: list[dict] = []
        self.items: list[dict] = []
        self.queries: list[dict] = []

    def fetch(self, url: str, headers: dict | None = None) -> tuple[bytes, dict, str]:
        delay = self.source["interval_seconds"] - (time.monotonic() - self.last_request)
        if delay > 0:
            time.sleep(delay)
        request_id = f"{self.source['id']}-{len(self.requests) + 1:04d}"
        request = {
            "id": request_id,
            "url": url,
            "fetched_at": datetime.now(UTC).isoformat(),
        }
        self.requests.append(request)
        self.last_request = time.monotonic()
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers or {}), timeout=40
            ) as response:
                body = response.read()
                metadata = {
                    key.lower(): value
                    for key, value in response.headers.items()
                    if key.lower()
                    in {
                        "content-type",
                        "date",
                        "etag",
                        "last-modified",
                        "link",
                        "x-ratelimit-limit",
                        "x-ratelimit-remaining",
                        "x-ratelimit-reset",
                        "x-wp-total",
                        "x-wp-totalpages",
                        "retry-after",
                    }
                }
                request.update(
                    status=response.status, bytes=len(body), headers=metadata
                )
                return body, metadata, request_id
        except urllib.error.HTTPError as error:
            request.update(status=error.code, error=str(error))
            raise
        except (urllib.error.URLError, TimeoutError) as error:
            request.update(status=None, error=str(error))
            raise

    def save_page(self, request_id: str, items: list[dict], metadata: dict) -> None:
        for item in items:
            item["title"] = plain_text(item["title"])
            item["body"] = plain_text(item["body"])
            item["request_id"] = request_id
            item["collected_at"] = self.requests[-1]["fetched_at"]
        dump_json(
            self.folder / f"{request_id}.json", {"metadata": metadata, "items": items}
        )
        self.items.extend(items)

    def github(self) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        }
        for query in self.source["queries"]:
            stat = {"id": query["id"], "pages_fetched": 0, "items_received": 0}
            self.queries.append(stat)
            for page in range(1, query["max_pages"] + 1):
                params = {
                    "q": f"{query['q']} created:{self.start.date()}..{self.end.date()}",
                    "sort": "stars"
                    if query["endpoint"] == "repositories"
                    else "comments",
                    "order": "desc",
                    "per_page": 100,
                    "page": page,
                }
                url = f"https://api.github.com/search/{query['endpoint']}?{urllib.parse.urlencode(params)}"
                raw, _, request_id = self.fetch(url, headers)
                response = json.loads(raw)
                rows = []
                for item in response["items"]:
                    repository = query["endpoint"] == "repositories"
                    rows.append(
                        {
                            "native_id": str(item["id"]),
                            "title": item["full_name"] if repository else item["title"],
                            "body": item.get("description", "") or ""
                            if repository
                            else item.get("body", "") or "",
                            "source_url": item["html_url"],
                            "published_at": item["created_at"],
                            "updated_at": item["updated_at"],
                            "record_kind": "repository" if repository else "issue",
                            "content_kind": "description" if repository else "body",
                            "metrics": {
                                "stars": item["stargazers_count"],
                                "forks": item["forks_count"],
                                "open_issues": item["open_issues_count"],
                            }
                            if repository
                            else {
                                "comments": item["comments"],
                                "reactions": item.get("reactions", {}).get(
                                    "total_count"
                                ),
                            },
                            "license": (item.get("license") or {}).get("spdx_id")
                            if repository
                            else None,
                            "query_id": query["id"],
                            "repository_api_url": item["url"] if repository else None,
                        }
                    )
                stat.update(
                    total_available=response["total_count"],
                    incomplete_results=response["incomplete_results"],
                )
                stat["pages_fetched"] += 1
                stat["items_received"] += len(rows)
                self.save_page(
                    request_id,
                    rows,
                    {
                        "query": params,
                        "total": response["total_count"],
                        "incomplete_results": response["incomplete_results"],
                    },
                )
                if not rows or page * 100 >= response["total_count"]:
                    break
            stat["truncated"] = (
                stat["items_received"] < min(stat["total_available"], 1000)
                or stat["incomplete_results"]
            )
            print(f"GitHub {query['id']}: {stat['items_received']} 条", flush=True)
        repositories = {
            item["native_id"]: item
            for item in self.items
            if item["record_kind"] == "repository"
        }
        selected = sorted(
            repositories.values(), key=lambda row: row["metrics"]["stars"], reverse=True
        )[: self.source["readme_limit"]]
        for item in selected:
            url = item["repository_api_url"] + "/readme"
            raw, _, request_id = self.fetch(url, headers)
            response = json.loads(raw)
            body = base64.b64decode(response["content"]).decode(
                "utf-8", errors="replace"
            )
            enriched = {
                **item,
                "body": body,
                "content_kind": "readme",
                "query_id": "readme-detail",
                "readme_url": response["html_url"],
            }
            self.save_page(
                request_id,
                [enriched],
                {"path": response["path"], "sha": response["sha"]},
            )
        print(f"GitHub README: {len(selected)} 份", flush=True)

    def hackernews(self) -> None:
        for query in self.source["queries"]:
            stat = {"id": query["id"], "pages_fetched": 0, "items_received": 0}
            self.queries.append(stat)
            for page in range(query["max_pages"]):
                params = {
                    "query": query["q"],
                    "tags": query["tags"],
                    "numericFilters": (
                        f"created_at_i>={int(self.start.timestamp())},"
                        f"created_at_i<={int(self.end.timestamp())}"
                    ),
                    "hitsPerPage": 100,
                    "page": page,
                }
                raw, _, request_id = self.fetch(
                    "https://hn.algolia.com/api/v1/search?"
                    + urllib.parse.urlencode(params)
                )
                response = json.loads(raw)
                rows = []
                for item in response["hits"]:
                    comment = query["tags"] == "comment"
                    body = (
                        item.get("comment_text") if comment else item.get("story_text")
                    )
                    rows.append(
                        {
                            "native_id": item["objectID"],
                            "title": item.get("story_title") or item.get("title") or "",
                            "body": body or "",
                            "source_url": f"https://news.ycombinator.com/item?id={item['objectID']}",
                            "published_at": item["created_at"],
                            "updated_at": None,
                            "record_kind": "comment" if comment else query["tags"],
                            "content_kind": "body" if body else "title_only",
                            "metrics": {
                                "points": item.get("points"),
                                "comments": item.get("num_comments"),
                            },
                            "license": None,
                            "query_id": query["id"],
                            "external_url": item.get("url"),
                            "parent_story_id": item.get("story_id"),
                        }
                    )
                stat.update(
                    total_available=response["nbHits"],
                    available_pages=response["nbPages"],
                )
                stat["pages_fetched"] += 1
                stat["items_received"] += len(rows)
                self.save_page(
                    request_id,
                    rows,
                    {
                        "query": params,
                        "total": response["nbHits"],
                        "pages": response["nbPages"],
                    },
                )
                if page + 1 >= response["nbPages"]:
                    break
            stat["truncated"] = stat["items_received"] < stat["total_available"]
            print(f"Hacker News {query['id']}: {stat['items_received']} 条", flush=True)

    def wordpress(self) -> None:
        stat = {"id": "posts", "pages_fetched": 0, "items_received": 0}
        self.queries.append(stat)
        for page in range(1, self.source["max_pages"] + 1):
            params = {
                "after": self.start.astimezone(UTC).isoformat(),
                "before": self.end.astimezone(UTC).isoformat(),
                "per_page": 100,
                "page": page,
                "_fields": (
                    "id,date_gmt,modified_gmt,link,title,content,"
                    "excerpt,categories,tags"
                ),
            }
            raw, metadata, request_id = self.fetch(
                self.source["endpoint"] + "?" + urllib.parse.urlencode(params)
            )
            response = json.loads(raw)
            rows = [
                {
                    "native_id": str(item["id"]),
                    "title": item["title"]["rendered"],
                    "body": item["content"]["rendered"],
                    "source_url": item["link"],
                    "published_at": item["date_gmt"] + "+00:00",
                    "updated_at": item["modified_gmt"] + "+00:00",
                    "record_kind": "article",
                    "content_kind": "body",
                    "metrics": {},
                    "license": None,
                    "query_id": "posts",
                    "categories": item["categories"],
                    "tags": item["tags"],
                }
                for item in response
            ]
            stat.update(
                total_available=int(metadata["x-wp-total"]),
                available_pages=int(metadata["x-wp-totalpages"]),
            )
            stat["pages_fetched"] += 1
            stat["items_received"] += len(rows)
            self.save_page(
                request_id,
                rows,
                {
                    "query": params,
                    "total": stat["total_available"],
                    "pages": stat["available_pages"],
                },
            )
            print(
                f"量子位 {page}/{stat['available_pages']}: {len(rows)} 条", flush=True
            )
            if page >= stat["available_pages"]:
                break
        stat["truncated"] = stat["items_received"] < stat["total_available"]

    def feed(self) -> None:
        atom = "{http://www.w3.org/2005/Atom}"
        for index, url in enumerate(self.source["feeds"], 1):
            raw, _, request_id = self.fetch(url)
            tree = ET.fromstring(raw)
            is_atom = tree.tag == atom + "feed"
            entries = (
                tree.findall(atom + "entry")
                if is_atom
                else tree.findall("./channel/item")
            )
            rows = []
            for item in entries:
                if is_atom:
                    links = item.findall(atom + "link")
                    link = next(
                        link.get("href")
                        for link in links
                        if link.get("rel", "alternate") == "alternate"
                    )
                    published = item.findtext(atom + "published") or item.findtext(
                        atom + "updated"
                    )
                    body = (
                        item.findtext(atom + "content")
                        or item.findtext(atom + "summary")
                        or ""
                    )
                    title = item.findtext(atom + "title") or ""
                    native_id = item.findtext(atom + "id") or link
                else:
                    link = item.findtext("link")
                    published = parsedate_to_datetime(
                        item.findtext("pubDate")
                    ).isoformat()
                    body = item.findtext("description") or ""
                    title = item.findtext("title") or ""
                    native_id = item.findtext("guid") or link
                rows.append(
                    {
                        "native_id": native_id,
                        "title": title,
                        "body": body,
                        "source_url": link,
                        "published_at": published,
                        "updated_at": None,
                        "record_kind": "topic" if is_atom else "article",
                        "content_kind": "feed_body" if body else "title_only",
                        "metrics": {},
                        "license": None,
                        "query_id": f"feed-{index}",
                    }
                )
            self.save_page(request_id, rows, {"feed_url": url})
            self.queries.append(
                {
                    "id": f"feed-{index}",
                    "pages_fetched": 1,
                    "items_received": len(rows),
                    "truncated": True,
                    "limitation": "仅订阅源当前提供的记录，不能覆盖完整历史时间窗。",
                }
            )
            print(f"{self.source['name']} RSS: {len(rows)} 条", flush=True)

    def run(self) -> dict:
        error = None
        try:
            getattr(self, self.source["kind"])()
        except (
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            KeyError,
            ET.ParseError,
        ) as problem:
            error = f"{type(problem).__name__}: {problem}"
            print(f"{self.source['name']}: {error}", flush=True)
        result = {
            "source_id": self.source["id"],
            "name": self.source["name"],
            "requests": self.requests,
            "queries": self.queries,
            "error": error,
        }
        dump_json(self.folder / "requests.json", result)
        return {**result, "items": self.items}


parser = argparse.ArgumentParser(description="采集一个独立批次的公开 AI 应用相关内容。")
parser.add_argument("--batch", required=True, help="批次号，例如 B01、B02。")
parser.add_argument("--reference-date", type=date.fromisoformat)
args = parser.parse_args()
if not re.fullmatch(r"B\d{2,}", args.batch):
    parser.error("批次号应为 B 加至少两位数字。")

sys.stdout.reconfigure(encoding="utf-8")
config = json.loads((ROOT / "configs/collection.json").read_text(encoding="utf-8"))
reference_date = args.reference_date or date.fromisoformat(config["reference_date"])
started = datetime.now(UTC)
start = datetime.combine(
    reference_date - timedelta(days=config["lookback_days"] - 1), day_time(), LOCAL
)
end = min(
    started, datetime.combine(reference_date + timedelta(days=1), day_time(), LOCAL)
)
raw_folder = ROOT / "data/raw" / args.batch
processed_folder = ROOT / "data/processed" / args.batch
if raw_folder.exists() or processed_folder.exists():
    parser.error("批次目录已存在，请使用新的批次号。")
raw_folder.mkdir(parents=True)
processed_folder.mkdir(parents=True)
(processed_folder / "text").mkdir()
dump_json(
    raw_folder / "collection_config.json",
    {
        **config,
        "reference_date": reference_date.isoformat(),
        "batch_id": args.batch,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "started_at": started.isoformat(),
    },
)

collectors = [Collector(source, raw_folder, start, end) for source in config["sources"]]
with ThreadPoolExecutor(max_workers=len(collectors)) as executor:
    results = list(executor.map(lambda collector: collector.run(), collectors))

records: dict[tuple[str, str], dict] = {}
excluded = Counter()
relevance = re.compile(config["relevance_pattern"])
for result in results:
    for item in result["items"]:
        published = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
        if not start <= published <= end:
            excluded["outside_time_window"] += 1
            continue
        if not relevance.search(item["title"] + "\n" + item["body"]):
            excluded["outside_direction"] += 1
            continue
        key = (result["source_id"], item["source_url"])
        if key in records:
            excluded["duplicate_source_url"] += 1
            record = records[key]
            record["query_ids"] = sorted(set(record["query_ids"] + [item["query_id"]]))
            record["request_ids"] = sorted(
                set(record["request_ids"] + [item["request_id"]])
            )
            if item["content_kind"] == "readme":
                record["title"] = item["title"]
                record["body"] = item["body"]
                record["content_kind"] = "readme"
                record["readme_url"] = item["readme_url"]
                record["collected_at"] = item["collected_at"]
            continue
        records[key] = {
            **item,
            "batch_id": args.batch,
            "source_id": result["source_id"],
            "source_name": result["name"],
            "published_at": published.astimezone(UTC).isoformat(),
            "query_ids": [item["query_id"]],
            "request_ids": [item["request_id"]],
        }

counts = Counter()
content_counts = Counter()
with (
    (processed_folder / "records.jsonl").open("x", encoding="utf-8") as records_stream,
    (processed_folder / "records.csv").open(
        "x", encoding="utf-8-sig", newline=""
    ) as csv_stream,
):
    columns = [
        "采集批次号",
        "记录编号",
        "来源网站名称",
        "来源链接",
        "标题",
        "内容",
        "发布时间",
        "热度指标",
        "内容类型",
        "原始记录位置",
    ]
    writer = csv.DictWriter(csv_stream, fieldnames=columns)
    writer.writeheader()
    for index, record in enumerate(
        sorted(
            records.values(),
            key=lambda row: (row["source_id"], row["published_at"], row["native_id"]),
        ),
        1,
    ):
        record["record_id"] = f"S{index:05d}"
        raw_text = record.pop("body")
        content = clean_text(record["title"] + "\n\n" + raw_text)
        content_path = (
            processed_folder / "text" / f"{args.batch}_{record['record_id']}.md"
        )
        with content_path.open("x", encoding="utf-8") as stream:
            stream.write(content + "\n")
        record["content_path"] = content_path.relative_to(ROOT).as_posix()
        record["content_characters"] = len(content)
        record["raw_response_paths"] = [
            f"data/raw/{args.batch}/{record['source_id']}/{request_id}.json"
            for request_id in record["request_ids"]
        ]
        record.pop("query_id")
        record.pop("request_id")
        record.pop("repository_api_url", None)
        records_stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        writer.writerow(
            dict(
                zip(
                    columns,
                    [
                        args.batch,
                        record["record_id"],
                        record["source_name"],
                        record["source_url"],
                        record["title"],
                        record["content_path"],
                        record["published_at"],
                        json.dumps(record["metrics"], ensure_ascii=False),
                        record["content_kind"],
                        "；".join(record["raw_response_paths"]),
                    ],
                    strict=True,
                )
            )
        )
        counts[record["source_name"]] += 1
        content_counts[record["content_kind"]] += 1

manifest = {
    "batch_id": args.batch,
    "direction": config["direction"],
    "reference_date": reference_date.isoformat(),
    "window_start": start.isoformat(),
    "window_end": end.isoformat(),
    "started_at": started.isoformat(),
    "finished_at": datetime.now(UTC).isoformat(),
    "python_version": sys.version,
    "records": len(records),
    "source_counts": dict(counts),
    "content_counts": dict(content_counts),
    "excluded_response_items": dict(excluded),
    "source_status": [
        {key: value for key, value in result.items() if key != "items"}
        for result in results
    ],
    "cleaning": [
        "HTML转正文",
        "邮箱、电话、IP及用户提及脱敏",
        "移除正文URL和图片链接",
        "统一空白",
        "同一来源链接合并",
    ],
    "limitations": [
        "公开检索接口中的热门样本，不代表平台全量。",
        "RSS仅包含当前订阅内容。",
        "跨来源近重复、机会标签和行业标签尚未判定。",
        "未公开的互动指标保留缺失，不填零。",
        "保留教程与宣传等相关内容供机会判别使用。",
    ],
}
dump_json(raw_folder / "manifest.json", manifest)
print(
    json.dumps(
        {
            key: manifest[key]
            for key in [
                "batch_id",
                "records",
                "source_counts",
                "content_counts",
                "excluded_response_items",
            ]
        },
        ensure_ascii=False,
        indent=2,
    ),
    flush=True,
)
if any(result["error"] for result in results):
    sys.exit(1)
