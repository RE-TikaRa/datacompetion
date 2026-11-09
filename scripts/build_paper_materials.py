import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
CLEANING = ROOT / "results/B01/20261107T164112993137Z"
JUDGING = ROOT / "results/B01/20261107T173708748922Z"
PROXY = JUDGING / "review/assistant_adjudication"
PROXY_FULL = PROXY / "full_batch_proxy"
TOPICS = ROOT / "results/B01/20261108T043220466135Z"
PAPER = ROOT / "paper"
FIGURES = PAPER / "figures"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def choose_font() -> str:
    candidates = ["Microsoft YaHei", "SimHei", "Arial"]
    available = {font.name for font in font_manager.fontManager.ttflist}
    return next((name for name in candidates if name in available), "DejaVu Sans")


def setup_plot() -> None:
    plt.rcParams.update(
        {
            "font.family": choose_font(),
            "axes.unicode_minus": False,
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.dpi": 160,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def save_figure(fig, stem: str) -> None:
    fig.savefig(FIGURES / f"{stem}.png", bbox_inches="tight")
    fig.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)


def build_figures(records: list[dict], proxy: list[dict], topics: list[dict]) -> None:
    setup_plot()
    source_counts = Counter(row["source_name"] for row in records)
    source_order = source_counts.most_common()
    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    names = [item[0] for item in source_order][::-1]
    values = [item[1] for item in source_order][::-1]
    bars = ax.barh(names, values, color="#3568a8")
    ax.set_xlabel("清洗后记录数")
    ax.set_title("B01 各公开来源的清洗记录规模")
    ax.bar_label(bars, padding=3, fmt="%d")
    ax.set_xlim(0, max(values) * 1.16)
    save_figure(fig, "fig01_source_counts")

    cleaning = read_json(CLEANING / "cleaning.json")
    stages = [
        ("原始字段出现", cleaning["raw_record_appearances"]),
        ("来源 URL 唯一", cleaning["url_unique_records"]),
        ("最终清洗记录", cleaning["retained_records"]),
        (
            "模型候选机会",
            len(
                [
                    row
                    for row in read_jsonl(JUDGING / "judgements.jsonl")
                    if row["is_opportunity"]
                ]
            ),
        ),
        ("AI 代理机会", len([row for row in proxy if row["is_opportunity"]])),
    ]
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    x = list(range(len(stages)))
    y = [value for _, value in stages]
    bars = ax.bar(x, y, color=["#596f9e", "#728bb5", "#4e9b8f", "#c57a36", "#bf5348"])
    ax.bar_label(bars, labels=[f"{value:,}" for _, value in stages], padding=3)
    ax.set_xticks(x, [label for label, _ in stages], rotation=18, ha="right")
    ax.set_ylabel("记录数")
    ax.set_title("从采集到 AI 代理候选的记录规模变化")
    ax.grid(axis="y", alpha=0.22)
    save_figure(fig, "fig02_pipeline_counts")

    quality_flags = {
        "内容不完整": cleaning["quality_flags"]["incomplete_content"],
        "短文本": cleaning["quality_flags"]["short_text"],
        "缺失热度": cleaning["quality_flags"]["missing_heat"],
    }
    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    names = list(quality_flags)
    values = list(quality_flags.values())
    bars = ax.bar(names, values, color=["#8b6bb8", "#e39a42", "#6b9b78"])
    ax.set_ylabel("记录数")
    ax.set_title("清洗结果中的主要质量标记")
    ax.bar_label(bars, padding=3, fmt="%d")
    ax.set_ylim(0, max(values) * 1.18)
    save_figure(fig, "fig03_quality_flags")

    original = read_jsonl(JUDGING / "judgements.jsonl")
    model_positive = len([row for row in original if row["is_opportunity"]])
    proxy_positive = len([row for row in proxy if row["is_opportunity"]])
    model_negative = len(original) - model_positive
    triage_states = {
        "原模型机会": model_positive,
        "原模型非机会": model_negative,
        "AI 代理机会": proxy_positive,
        "AI 代理非机会": len(proxy) - proxy_positive,
    }
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    labels = list(triage_states)
    values = list(triage_states.values())
    colors = ["#b95b57", "#d9d9d9", "#3d7ea6", "#a9c7d8"]
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("记录数")
    ax.set_title("原模型与 AI 代理复核的机会判断规模")
    ax.bar_label(bars, padding=3, fmt="%d")
    ax.set_ylim(0, max(values) * 1.18)
    ax.tick_params(axis="x", rotation=15)
    save_figure(fig, "fig04_label_shift")

    topic_rows = sorted(topics, key=lambda row: (-row["record_count"], row["topic_id"]))
    fig, (size_ax, score_ax) = plt.subplots(
        1, 2, figsize=(8.2, 5.2), gridspec_kw={"width_ratios": [1.0, 1.0]}
    )
    names = [row["topic_id"] for row in topic_rows][::-1]
    counts = [row["record_count"] for row in topic_rows][::-1]
    scores = [row["value_score"] for row in topic_rows][::-1]
    size_bars = size_ax.barh(names, counts, color="#397f78")
    size_ax.bar_label(size_bars, padding=2, fmt="%d", fontsize=7)
    size_ax.set_xlabel("主题成员数")
    size_ax.set_title("主题规模")
    size_ax.set_xlim(0, max(counts) * 1.18)
    score_bars = score_ax.barh(names, scores, color="#c87932")
    score_ax.bar_label(score_bars, padding=2, fmt="%.1f", fontsize=7)
    score_ax.set_xlabel("机会价值分")
    score_ax.set_title("主题价值分")
    score_ax.set_xlim(0, max(scores) * 1.22)
    score_ax.tick_params(axis="y", labelleft=False)
    fig.suptitle("AI 代理候选主题的规模与价值分", y=1.01)
    fig.tight_layout()
    save_figure(fig, "fig05_topic_size_score")

    queue = read_jsonl(JUDGING / "judgements.jsonl")
    model_labels = {row["record_id"]: bool(row["is_opportunity"]) for row in queue}
    counts = Counter(
        (model_labels[row["record_id"]], bool(row["is_opportunity"])) for row in proxy
    )
    labels = [
        "模型机会→代理机会",
        "模型机会→代理非机会",
        "模型非机会→代理机会",
        "模型非机会→代理非机会",
    ]
    keys = [(True, True), (True, False), (False, True), (False, False)]
    values = [counts[key] for key in keys]
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    bars = ax.bar(labels, values, color=["#3d7ea6", "#c4513d", "#e39a42", "#9eabb5"])
    ax.set_ylabel("记录数")
    ax.set_title("AI 代理复核相对原模型的标签变化")
    ax.bar_label(bars, padding=3, fmt="%d")
    ax.tick_params(axis="x", rotation=16)
    ax.set_ylim(0, max(values) * 1.2)
    save_figure(fig, "fig06_proxy_confusion")


def build_reports(records: list[dict], proxy: list[dict], topics: list[dict]) -> None:
    cleaning = read_json(CLEANING / "cleaning.json")
    judging = read_json(JUDGING / "judging.json")
    proxy_summary = read_json(PROXY / "assistant_adjudication_summary.json")
    topic_data = read_json(TOPICS / "topics.json")
    scoring = read_json(TOPICS / "scoring.json")
    model_candidate_count = sum(
        row["is_opportunity"] for row in read_jsonl(JUDGING / "judgements.jsonl")
    )
    source_counts = Counter(row["source_name"] for row in records)
    content_counts = Counter(row["content_kind"] for row in records)
    evidence_lines = [
        "# 论文证据账本",
        "",
        "## 研究对象",
        "",
        "- 研究批次：B01。需求方向为综合 AI 应用机会，覆盖多个行业。",
        "- 时间窗：2026-08-10 至 2026-11-07（北京时间口径）。",
        "- 来源：GitHub、Hacker News、量子位、IT之家、V2EX，共 5 个公开来源。",
        (
            f"- 原始字段出现：{cleaning['raw_record_appearances']:,}；"
            f"来源 URL 唯一记录：{cleaning['url_unique_records']:,}；"
            f"最终清洗记录：{cleaning['retained_records']:,}。"
        ),
        "",
        "## 可写入正文的事实",
        "",
        "| 论文主张 | 证据文件 | 强度 | 限制 |",
        "| --- | --- | --- | --- |",
        (
            "| B01 完成多源公开数据采集与可追溯清洗 | "
            "采集与清洗报告 | 结构审计通过 | 来源样本量和历史覆盖不一致 |"
        ),
        (
            f"| 清洗结果包含 {cleaning['retained_records']:,} 条记录 | "
            "cleaning.json、records.jsonl、result1.csv | 数量可复现 | "
            f"{cleaning['quality_flags']['incomplete_content']} 条内容不完整，"
            f"{cleaning['quality_flags']['missing_heat']} 条缺少热度 |"
        ),
        (
            "| 原模型覆盖全部清洗记录 | judging.json、JUDGING_B01.md | "
            "结构审计通过 | 置信度是模型自评，尚未校准 |"
        ),
        (
            "| AI 代理复核覆盖 509 条复核队列 | "
            "assistant_adjudication_summary.json | 编号和证据审计通过 | 不是人工真值 |"
        ),
        (
            f"| AI 代理结果包含 "
            f"{proxy_summary['assistant_proxy_opportunities']} 条机会候选 | "
            "assistant_proxy_summary.json | 代理结果可复现 | "
            "2,052 条未抽样记录仍为原模型标签 |"
        ),
        (
            f"| 代理候选形成 {topic_data['quality']['topic_count']} 个主题 | "
            "topics.json | 成员审计通过 | "
            f"{sum(topic['record_count'] == 1 for topic in topics)} 个主题为单记录，"
            f"轮廓系数 {topic_data['quality']['silhouette_score']:.3f} |"
        ),
        "",
        "## 不可写成强结论的内容",
        "",
        "- 不报告 Precision、Recall、F1 或概率校准结果，因为没有真人真值。",
        ("- 不把 AI 代理复核称为人工复核，也不把代理 result2 称为正式比赛 result2。"),
        "- 不把代理主题称为已经识别出的可靠热点。",
        "- 不把来源记录数量解释为各行业真实需求占比。",
        "- 不把缺失热度解释为低热度。",
        "",
        "## 代理主题摘要",
        "",
        "| 主题 | 成员数 | 价值分 | 来源覆盖 |",
        "| --- | ---: | ---: | --- |",
    ]
    evidence = "\n".join(evidence_lines) + "\n"
    for topic in sorted(topics, key=lambda row: row["priority"]):
        evidence += (
            f"| {topic['topic_id']} {topic['topic_name']} | "
            f"{topic['record_count']} | {topic['value_score']:.2f} | "
            f"{'、'.join(topic['source_names'])} |\n"
        )
    evidence += (
        "\n代理评分权重为多源指向度 0.45、记录规模 0.35、互动信号 0.20。"
        "缺失互动指标不填零，主题没有可用指标时按可用维度重新归一。\n"
    )
    (PAPER / "EVIDENCE_LEDGER.md").write_text(evidence, encoding="utf-8")

    result_lines = [
        "# B01 论文结果总表",
        "",
        "## 数据规模",
        "",
        "| 指标 | 数值 |",
        "| --- | ---: |",
        f"| 原始字段出现 | {cleaning['raw_record_appearances']:,} |",
        f"| 来源 URL 唯一记录 | {cleaning['url_unique_records']:,} |",
        f"| 最终清洗记录 | {cleaning['retained_records']:,} |",
        f"| 模型判别覆盖 | {judging['records']:,} |",
        f"| 原模型机会候选 | {model_candidate_count:,} |",
        f"| AI 代理复核记录 | {proxy_summary['review_records']:,} |",
        f"| AI 代理机会候选 | {proxy_summary['assistant_proxy_opportunities']:,} |",
        "",
        "## 来源与内容",
        "",
        "| 来源 | 记录数 |",
        "| --- | ---: |",
    ]
    results = "\n".join(result_lines) + "\n"
    for source, count in source_counts.most_common():
        results += f"| {source} | {count} |\n"
    results += "\n| 内容类型 | 记录数 |\n| --- | ---: |\n"
    for kind, count in content_counts.most_common():
        results += f"| {kind} | {count} |\n"
    result_topic = (
        "\n## 代理主题\n\n"
        f"代理机会记录形成 {topic_data['quality']['topic_count']} 个主题，"
        f"噪声记录 {topic_data['quality']['noise_records']} 条按单记录主题保留；"
        f"轮廓系数为 {topic_data['quality']['silhouette_score']:.3f}。"
        f"其中 {sum(topic['record_count'] == 1 for topic in topics)} 个主题只有 "
        "一条记录，"
        "主题结果仅作为探索性候选。\n\n"
        f"代理评分排名第一主题为 {scoring['ranking'][0]['topic_id']}，"
        f"机会价值分 {scoring['ranking'][0]['value_score']:.2f}。"
        "该排名只适用于当前代理标签和当前 B01 样本。\n"
    )
    results += result_topic
    (PAPER / "RESULTS_REPORT.md").write_text(results, encoding="utf-8")

    storyboard = "\n".join(
        [
            "# 论文图表规划",
            "",
            "| 图表 | 论证问题 | 数据来源 | 计划位置 | 结论边界 |",
            "| --- | --- | --- | --- | --- |",
            (
                "| Figure 1 | B01 来源组成与样本规模 | records.jsonl | "
                "数据与采集 | 不代表平台总体 |"
            ),
            (
                "| Figure 2 | 各阶段记录规模变化 | cleaning.json、judging.json、"
                "代理摘要 | 方法与结果 | 不是召回率 |"
            ),
            (
                "| Figure 3 | 内容质量限制 | cleaning.json | 数据质量 | "
                "缺失与短文本需保留 |"
            ),
            (
                "| Figure 4 | 代理复核相对原模型的变化 | 代理 JSONL | "
                "复核与评价 | 不是真人准确率 |"
            ),
            (
                "| Figure 5 | 代理主题规模与价值分布 | topics.json、scoring.json | "
                "主题与价值评估 | 不能宣称热点稳定 |"
            ),
            (
                "| Figure 6 | 原模型与代理标签交叉变化 | 代理 JSONL | "
                "稳健性与限制 | 只能说明代理敏感性 |"
            ),
            "",
        ]
    )
    (PAPER / "FIGURE_STORYBOARD.md").write_text(storyboard, encoding="utf-8")


PAPER.mkdir(exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)
records = read_jsonl(CLEANING / "records.jsonl")
proxy = read_jsonl(PROXY_FULL / "assistant_proxy_judgements.jsonl")
topics = read_json(TOPICS / "topics.json")["topics"]
build_figures(records, proxy, topics)
build_reports(records, proxy, topics)
print(
    json.dumps(
        {
            "paper": PAPER.relative_to(ROOT).as_posix(),
            "figures": len(list(FIGURES.glob("*.pdf"))),
            "proxy_topics": len(topics),
        },
        ensure_ascii=False,
        indent=2,
    )
)
