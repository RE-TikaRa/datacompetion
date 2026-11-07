import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.cluster import HDBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score

from opportunity.embedding import TextEmbedder
from opportunity.files import ROOT, read_json, read_jsonl


def short_title(title: str, limit: int = 48) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    return title if len(title) <= limit else title[: limit - 1] + "…"


def topic_name(cluster: list[dict], keywords: list[str]) -> str:
    titles = Counter(record["title"] for record in cluster)
    representative = titles.most_common(1)[0][0]
    if len(cluster) == 1:
        return short_title(representative)
    keyword_text = "、".join(keywords[:3])
    return f"{keyword_text}相关应用需求：{short_title(representative, 34)}"


def top_keywords(texts: list[str], count: int = 6) -> list[str]:
    vectorizer = TfidfVectorizer(
        analyzer="char", ngram_range=(2, 4), min_df=1, max_features=20000
    )
    matrix = vectorizer.fit_transform(texts)
    scores = np.asarray(matrix.mean(axis=0)).ravel()
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(zip(scores, terms, strict=True), reverse=True)
    stopwords = {
        "the",
        "and",
        "you",
        "age",
        "gen",
        "ent",
        "ing",
        "ion",
        "with",
        "for",
        "from",
        "this",
        "that",
        "are",
        "what",
        "how",
        "can",
    }
    selected = []
    for _, term in ranked:
        if term.isascii() and len(term.strip()) < 3:
            continue
        if term.strip().casefold() in stopwords:
            continue
        if any(term in existing or existing in term for existing in selected):
            continue
        if not re.search(r"[A-Za-z\u4e00-\u9fff]", term):
            continue
        selected.append(term)
        if len(selected) == count:
            break
    return selected


def cluster_topics(
    cleaning_run: Path,
    judgement_run: Path,
    root: Path = ROOT,
    min_cluster_size: int = 5,
) -> tuple[list[dict], dict]:
    records = {
        row["record_id"]: row for row in read_jsonl(cleaning_run / "records.jsonl")
    }
    judgements = read_jsonl(judgement_run / "judgements.jsonl")
    candidates = [item for item in judgements if item["is_opportunity"]]
    if not candidates:
        raise ValueError("没有模型候选机会，无法生成候选主题。")
    texts = []
    for item in candidates:
        record = records[item["record_id"]]
        text = (
            record["title"]
            + "\n"
            + (cleaning_run / record["content_path"]).read_text(encoding="utf-8")
        )[:12000]
        texts.append(text)
    embedder = TextEmbedder(root)
    embeddings = embedder.encode(texts)
    min_cluster_size = min(min_cluster_size, max(2, len(candidates) // 3))
    model = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=2,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    labels = model.fit_predict(embeddings)
    groups: dict[int, list[int]] = defaultdict(list)
    for index, label in enumerate(labels):
        groups[int(label)].append(index)
    noise = groups.pop(-1, [])
    for index in noise:
        groups[max(groups, default=-1) + 1] = [index]
    topics = []
    item_to_topic = {}
    for cluster_index, members in enumerate(
        sorted(groups.values(), key=lambda row: (-len(row), row[0])), 1
    ):
        rows = [candidates[index] for index in members]
        source_names = sorted(
            {records[row["record_id"]]["source_name"] for row in rows}
        )
        keywords = top_keywords([texts[index] for index in members])
        topic_id = f"C{cluster_index}"
        for row in rows:
            item_to_topic[row["record_id"]] = topic_id
        topics.append(
            {
                "batch_id": read_json(cleaning_run / "cleaning.json")["batch_id"],
                "topic_id": topic_id,
                "topic_name": topic_name(
                    [records[row["record_id"]] for row in rows], keywords
                ),
                "functional_category": Counter(
                    row["functional_category"] for row in rows
                ).most_common(1)[0][0],
                "industry": Counter(row["industry"] for row in rows).most_common(1)[0][
                    0
                ],
                "record_ids": sorted(row["record_id"] for row in rows),
                "record_count": len(rows),
                "source_names": source_names,
                "source_count": len(source_names),
                "keywords": keywords,
            }
        )
    cluster_records = [index for index, label in enumerate(labels) if label >= 0]
    clustered_labels = labels[cluster_records]
    quality = {
        "embedding": embedder.metadata(),
        "algorithm": "HDBSCAN",
        "min_cluster_size": min_cluster_size,
        "min_samples": 2,
        "candidate_records": len(candidates),
        "topic_count": len(topics),
        "noise_records": len(noise),
        "silhouette_score": float(
            silhouette_score(embeddings[cluster_records], clustered_labels)
        )
        if len(set(clustered_labels)) > 1
        and len(clustered_labels) > len(set(clustered_labels))
        else None,
        "topic_assignments": item_to_topic,
        "review_status": "候选结果，待人工复核",
    }
    return topics, quality


def score_topics(
    topics: list[dict],
    records: dict[str, dict],
    judgements: dict[str, dict],
) -> tuple[list[dict], dict]:
    max_sources = max((topic["source_count"] for topic in topics), default=1)
    max_records = max((topic["record_count"] for topic in topics), default=1)
    source_max: dict[str, dict[str, float]] = defaultdict(dict)
    for record in records.values():
        for key, value in record["metrics"].items():
            if key in {"stars", "points", "comments", "reactions"} and isinstance(
                value, (int, float)
            ):
                source_max[record["source_id"]][key] = max(
                    source_max[record["source_id"]].get(key, 0), math.log1p(value)
                )
    for topic in topics:
        heat_values = []
        for record_id in topic["record_ids"]:
            record = records[record_id]
            heat = [
                math.log1p(value) / source_max[record["source_id"]][key]
                for key, value in record["metrics"].items()
                if key in {"stars", "points", "comments", "reactions"}
                and isinstance(value, (int, float))
                and source_max.get(record["source_id"], {}).get(key, 0) > 0
            ]
            if heat:
                heat_values.append(sum(heat) / len(heat))
        dimensions = {
            "multi_source_direction": 100 * topic["source_count"] / max_sources,
            "record_scale": 100
            * math.log1p(topic["record_count"])
            / math.log1p(max_records),
            "interaction_signal": 100 * (sum(heat_values) / len(heat_values))
            if heat_values
            else None,
        }
        topic["dimension_scores"] = dimensions
        weights = {
            "multi_source_direction": 0.45,
            "record_scale": 0.35,
            "interaction_signal": 0.20,
        }
        available = {
            name: (weight, dimensions[name])
            for name, weight in weights.items()
            if dimensions[name] is not None
        }
        weight_total = sum(weight for weight, _ in available.values())
        topic["scoring_weights"] = {
            name: weight / weight_total for name, (weight, _) in available.items()
        }
        topic["value_score"] = round(
            sum(weight * float(score) for weight, score in available.values())
            / weight_total,
            2,
        )
    topics.sort(key=lambda topic: (-topic["value_score"], topic["topic_id"]))
    for priority, topic in enumerate(topics, 1):
        topic["priority"] = priority
    return topics, {
        "weights": {
            "multi_source_direction": 0.45,
            "record_scale": 0.35,
            "interaction_signal": 0.20,
        },
        "review_status": "候选结果，待人工复核",
        "heat_policy": (
            "按来源和指标分别取对数归一，簇内计算非缺失值均值。"
            "整个主题没有热度值时，按可用维度重新归一权重。"
        ),
    }
