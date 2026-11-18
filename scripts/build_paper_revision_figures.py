import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from sklearn.decomposition import PCA
from sklearn.metrics import average_precision_score, precision_recall_curve

ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


parser = argparse.ArgumentParser(description="根据首批公开数据结果生成论文新增图件。")
parser.add_argument(
    "--cleaning-run",
    type=Path,
    default=Path("results/B01/20261107T164112993137Z"),
)
parser.add_argument(
    "--review-run",
    type=Path,
    default=Path("results/B01/20261107T173708748922Z/review/assistant_adjudication"),
)
parser.add_argument(
    "--topic-run", type=Path, default=Path("results/B01/20261118T192102321700Z")
)
parser.add_argument(
    "--experiment-run",
    type=Path,
    default=Path("results/B01/20261118_proxy_ml_family_v2"),
)
parser.add_argument("--overwrite", action="store_true")
args = parser.parse_args()


def project_path(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


cleaning_run = project_path(args.cleaning_run)
review_run = project_path(args.review_run)
topic_run = project_path(args.topic_run)
experiment_run = project_path(args.experiment_run)
figure_dir = ROOT / "paper" / "figures"
stems = [
    "fig07_weekly_source_heatmap",
    "fig08_source_quality_heatmap",
    "fig09_review_sample_composition",
    "fig10_proxy_classifier_comparison",
    "fig11_proxy_classifier_oof",
    "fig12_embedding_pca",
    "fig13_topic_dimension_heatmap",
    "fig14_topic_rank_sensitivity",
    "fig15_opportunity_method",
    "fig16_classifier_family",
    "fig17_source_holdout",
]
PRIMARY_MODELS = ["char_tfidf_lr", "e5_lr", "e5_mlp_nested"]
existing = [
    figure_dir / f"{stem}.{extension}"
    for stem in stems
    for extension in ("png", "pdf", "svg")
    if (figure_dir / f"{stem}.{extension}").exists()
]
if existing and not args.overwrite:
    raise FileExistsError("图件输出已存在：" + ", ".join(map(str, existing)))

records = read_jsonl(cleaning_run / "records.jsonl")
proxy = read_jsonl(review_run / "assistant_review_proxy.jsonl")
records_by_id = {record["record_id"]: record for record in records}
proxy_labels = np.asarray([int(row["is_opportunity"]) for row in proxy])
experiment = json.loads(
    (experiment_run / "experiment.json").read_text(encoding="utf-8")
)
topics = json.loads((topic_run / "topics.json").read_text(encoding="utf-8"))["topics"]
nested = experiment["nested_experiment"]
with (experiment_run / "nested_fold_metrics.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    fold_metrics = list(csv.DictReader(stream))
with (experiment_run / "nested_oof_predictions.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    prediction_rows = list(csv.DictReader(stream))
with (experiment_run / "source_holdout_metrics.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    source_holdout_rows = list(csv.DictReader(stream))
embeddings = np.load(experiment_run / "e5_embeddings.npy")

BLUE = "#0F4D92"
BLUE_LIGHT = "#3775BA"
GREEN = "#42949E"
RED = "#B64342"
GRAY = "#767676"
LIGHT_GRAY = "#CFCECE"
PALE_BLUE = "#DCE8F2"
SOURCE_ORDER = ["Hacker News", "GitHub", "量子位", "V2EX", "IT之家"]
SOURCE_COLORS = {
    "Hacker News": BLUE,
    "GitHub": GREEN,
    "量子位": "#9A4D8E",
    "V2EX": "#D08A34",
    "IT之家": RED,
}


def setup_plot() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    font = next(
        (name for name in ["Microsoft YaHei", "SimHei", "Arial"] if name in available),
        "DejaVu Sans",
    )
    plt.rcParams.update(
        {
            "font.family": font,
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.unicode_minus": False,
            "legend.frameon": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "figure.dpi": 160,
            "savefig.dpi": 300,
        }
    )


def save_figure(fig, stem: str) -> None:
    if fig.get_layout_engine() is None:
        fig.tight_layout(pad=1.4)
    for extension in ("pdf", "png", "svg"):
        fig.savefig(
            figure_dir / f"{stem}.{extension}",
            dpi=300,
            bbox_inches="tight",
        )
    plt.close(fig)


def build_weekly_source_heatmap() -> None:
    counts: Counter[tuple[str, str]] = Counter()
    weeks = set()
    zone = ZoneInfo("Asia/Shanghai")
    for record in records:
        published = datetime.fromisoformat(
            record["published_at"].replace("Z", "+00:00")
        ).astimezone(zone)
        monday = published.date() - timedelta(days=published.weekday())
        week = monday.isoformat()
        weeks.add(week)
        counts[(record["source_name"], week)] += 1
    week_order = sorted(weeks)
    source_order = [
        source
        for source in SOURCE_ORDER
        if any(r["source_name"] == source for r in records)
    ]
    matrix = np.asarray(
        [[counts[(source, week)] for week in week_order] for source in source_order]
    )
    fig, ax = plt.subplots(figsize=(9.4, 3.6))
    image = ax.imshow(matrix, aspect="auto", cmap="YlGnBu")
    ax.set_yticks(range(len(source_order)), source_order)
    ax.set_xticks(
        range(len(week_order)),
        [week[5:] for week in week_order],
        rotation=45,
        ha="right",
    )
    ax.set_xlabel("发布周（周一）")
    ax.set_title("清洗记录的来源与时间覆盖")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = int(matrix[row, column])
            if value:
                color = "white" if value > matrix.max() * 0.58 else "#222222"
                ax.text(
                    column,
                    row,
                    str(value),
                    ha="center",
                    va="center",
                    color=color,
                    fontsize=7,
                )
    fig.colorbar(image, ax=ax, label="记录数", shrink=0.82)
    save_figure(fig, stems[0])


def build_source_quality_heatmap() -> None:
    flags = ["incomplete_content", "short_text", "missing_heat"]
    labels = ["正文不完整", "短文本", "缺少热度"]
    source_order = [
        source
        for source in SOURCE_ORDER
        if any(r["source_name"] == source for r in records)
    ]
    matrix = np.zeros((len(source_order), len(flags)), dtype=np.float64)
    annotations = []
    totals = []
    for row_index, source in enumerate(source_order):
        source_records = [
            record for record in records if record["source_name"] == source
        ]
        totals.append(len(source_records))
        row_annotations = []
        for column_index, flag in enumerate(flags):
            count = sum(flag in record["quality_flags"] for record in source_records)
            matrix[row_index, column_index] = 100 * count / len(source_records)
            row_annotations.append(f"{matrix[row_index, column_index]:.0f}%\n({count})")
        annotations.append(row_annotations)
    fig, ax = plt.subplots(figsize=(7.3, 3.6))
    image = ax.imshow(matrix, aspect="auto", cmap="YlOrRd", vmin=0, vmax=100)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_yticks(
        range(len(source_order)),
        [
            f"{source} (n={count})"
            for source, count in zip(source_order, totals, strict=True)
        ],
    )
    ax.set_title("来源内部的内容质量标记比例")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            ax.text(
                column,
                row,
                annotations[row][column],
                ha="center",
                va="center",
                fontsize=8,
            )
    fig.colorbar(image, ax=ax, label="占该来源记录比例（%）", shrink=0.84)
    save_figure(fig, stems[1])


def add_stacked_panel(ax, rows, labels, title: str) -> None:
    negative = np.asarray(
        [
            sum(not row["is_opportunity"] for row in rows if row["group"] == label)
            for label in labels
        ]
    )
    positive = np.asarray(
        [
            sum(row["is_opportunity"] for row in rows if row["group"] == label)
            for label in labels
        ]
    )
    y = np.arange(len(labels))
    ax.barh(y, negative, color=LIGHT_GRAY, label="人工确认非机会")
    ax.barh(y, positive, left=negative, color=BLUE, label="人工确认机会")
    for index, (no_count, yes_count) in enumerate(zip(negative, positive, strict=True)):
        if no_count >= 12:
            ax.text(
                no_count / 2, index, str(no_count), ha="center", va="center", fontsize=8
            )
        if yes_count >= 4:
            ax.text(
                no_count + yes_count / 2,
                index,
                str(yes_count),
                ha="center",
                va="center",
                color="white",
                fontsize=8,
            )
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("复核记录数")
    ax.set_title(title)


def build_review_sample_composition() -> None:
    source_rows = [
        {
            "group": records_by_id[row["record_id"]]["source_name"],
            "is_opportunity": row["is_opportunity"],
        }
        for row in proxy
    ]
    source_labels = [
        source
        for source in SOURCE_ORDER
        if any(row["group"] == source for row in source_rows)
    ]
    kind_order = ["body", "feed_body", "description", "readme", "title_only"]
    kind_rows = [
        {
            "group": records_by_id[row["record_id"]]["content_kind"],
            "is_opportunity": row["is_opportunity"],
        }
        for row in proxy
    ]
    kind_labels = [
        kind for kind in kind_order if any(row["group"] == kind for row in kind_rows)
    ]
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.3))
    add_stacked_panel(axes[0], source_rows, source_labels, "按来源网站")
    add_stacked_panel(axes[1], kind_rows, kind_labels, "按正文类型")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.04))
    fig.suptitle("509 条人工复核样本的组成", y=1.12)
    save_figure(fig, stems[2])


def build_classifier_comparison() -> None:
    metrics = [
        ("average_precision", "平均精确率 AP"),
        ("macro_f1", "Macro-F1"),
        ("balanced_accuracy", "平衡准确率"),
    ]
    model_keys = PRIMARY_MODELS
    colors = [GRAY, "#9FB1CF", BLUE]
    fig, axes = plt.subplots(1, 3, figsize=(11.2, 3.7), sharex=True)
    for axis, (metric, title) in zip(axes, metrics, strict=True):
        for index, model_key in enumerate(model_keys):
            mean = float(
                nested["metrics"][model_key]["repeated_fold_metrics"][metric]["mean"]
            )
            sd = float(
                nested["metrics"][model_key]["repeated_fold_metrics"][metric]["sd"]
            )
            axis.errorbar(
                mean,
                index,
                xerr=sd,
                fmt="o",
                color=colors[index],
                ecolor=colors[index],
                capsize=3,
                markersize=6,
                label=nested["models"][model_key],
            )
            axis.text(
                min(mean + sd + 0.025, 0.96),
                index,
                f"{mean:.2f} ± {sd:.2f}",
                va="center",
                fontsize=7,
            )
        axis.set_xlim(0, 1)
        axis.set_ylim(-0.6, len(model_keys) - 0.4)
        axis.set_yticks(
            range(len(model_keys)), [nested["models"][key] for key in model_keys]
        )
        axis.invert_yaxis()
        axis.set_title(title)
        axis.grid(axis="x", color="#DDDDDD", linewidth=0.6)
    prevalence = float(proxy_labels.mean())
    axes[0].axvline(
        prevalence, color=RED, linestyle="--", linewidth=1, label="正例比例"
    )
    handles = [
        Line2D(
            [0], [0], marker="o", linestyle="", color=color, label=nested["models"][key]
        )
        for key, color in zip(model_keys, colors, strict=True)
    ]
    handles.append(Line2D([0], [0], linestyle="--", color=RED, label="正例比例"))
    fig.legend(
        handles=handles,
        loc="upper center",
        ncol=4,
        bbox_to_anchor=(0.5, 1.05),
        fontsize=8,
    )
    fig.suptitle("人工复核标签复现：五折嵌套验证重复两次（均值 ± 折间标准差）", y=1.16)
    save_figure(fig, stems[3])


def build_classifier_oof() -> None:
    y_true = np.asarray([int(row["proxy_is_opportunity"]) for row in prediction_rows])
    model_keys = PRIMARY_MODELS
    colors = [GRAY, "#9FB1CF", BLUE]
    fig = plt.figure(figsize=(10.4, 7.1), layout="constrained")
    grid = fig.add_gridspec(2, 3, height_ratios=[1.15, 1.0], hspace=0.42)
    pr_axis = fig.add_subplot(grid[0, :])
    prevalence = float(y_true.mean())
    for model_key, color in zip(model_keys, colors, strict=True):
        probabilities = np.asarray(
            [float(row[f"{model_key}_probability"]) for row in prediction_rows]
        )
        precision, recall, _ = precision_recall_curve(y_true, probabilities)
        ap = average_precision_score(y_true, probabilities)
        pr_axis.plot(
            recall,
            precision,
            color=color,
            linewidth=2,
            label=f"{nested['models'][model_key]} (AP={ap:.2f})",
        )
    pr_axis.axhline(
        prevalence,
        color=RED,
        linestyle="--",
        linewidth=1,
        label=f"正例比例={prevalence:.2f}",
    )
    pr_axis.set_xlim(0, 1)
    pr_axis.set_ylim(0, 1)
    pr_axis.set_xlabel("召回率")
    pr_axis.set_ylabel("精确率")
    pr_axis.set_title("折外平均预测的精确率—召回率曲线")
    pr_axis.legend(loc="upper right", fontsize=8)

    maximum = 0
    matrices = []
    for model_key in model_keys:
        probabilities = np.asarray(
            [float(row[f"{model_key}_probability"]) for row in prediction_rows]
        )
        prediction = probabilities >= 0.5
        matrix = np.asarray(
            [
                [
                    np.count_nonzero((y_true == 0) & ~prediction),
                    np.count_nonzero((y_true == 0) & prediction),
                ],
                [
                    np.count_nonzero((y_true == 1) & ~prediction),
                    np.count_nonzero((y_true == 1) & prediction),
                ],
            ]
        )
        matrices.append(matrix)
        maximum = max(maximum, int(matrix.max()))
    for index, (model_key, matrix) in enumerate(zip(model_keys, matrices, strict=True)):
        axis = fig.add_subplot(grid[1, index])
        axis.imshow(matrix, cmap="Blues", norm=Normalize(vmin=0, vmax=maximum))
        axis.set_xticks([0, 1], ["非机会", "机会"])
        axis.set_yticks([0, 1], ["非机会", "机会"])
        axis.set_xlabel("预测人工标签")
        if index == 0:
            axis.set_ylabel("人工复核标签")
        axis.set_title(nested["models"][model_key], fontsize=9)
        for row in range(2):
            for column in range(2):
                color = "white" if matrix[row, column] > maximum * 0.55 else "#222222"
                axis.text(
                    column,
                    row,
                    str(matrix[row, column]),
                    ha="center",
                    va="center",
                    color=color,
                    fontsize=10,
                )
    save_figure(fig, stems[4])


def build_embedding_pca() -> None:
    pca = PCA(n_components=2, svd_solver="full")
    projection = pca.fit_transform(embeddings)
    labels = proxy_labels
    boundaries = np.asarray([bool(row["boundary_case"]) for row in proxy])
    fig, ax = plt.subplots(figsize=(6.5, 5.1))
    for label, color, label_text in [
        (0, LIGHT_GRAY, "人工确认非机会"),
        (1, BLUE, "人工确认机会"),
    ]:
        for boundary, marker, marker_text in [
            (False, "o", "普通"),
            (True, "^", "边界"),
        ]:
            mask = (labels == label) & (boundaries == boundary)
            if mask.any():
                ax.scatter(
                    projection[mask, 0],
                    projection[mask, 1],
                    s=34 if not boundary else 58,
                    marker=marker,
                    color=color,
                    alpha=0.76,
                    linewidths=0,
                    label=f"{label_text} · {marker_text}",
                )
    variance = pca.explained_variance_ratio_
    ax.set_xlabel(f"PC1 ({variance[0] * 100:.1f}%)")
    ax.set_ylabel(f"PC2 ({variance[1] * 100:.1f}%)")
    ax.set_title("人工复核标签在冻结 E5 向量空间中的 PCA 投影")
    ax.legend(loc="best", fontsize=8)
    save_figure(fig, stems[5])


def build_topic_dimension_heatmap() -> None:
    dimension_keys = [
        "multi_source_direction",
        "record_scale",
        "interaction_signal",
        "recency_signal",
    ]
    dimension_labels = ["多源指向", "记录规模", "互动信号", "时间新近性"]
    values = np.asarray(
        [
            [
                np.nan
                if topic["dimension_scores"][key] is None
                else topic["dimension_scores"][key]
                for key in dimension_keys
            ]
            for topic in topics
        ],
        dtype=np.float64,
    )
    counts = [int(topic["record_count"]) for topic in topics]
    names = [
        f"{topic['topic_id']} · {count} 条"
        for topic, count in zip(topics, counts, strict=True)
    ]
    cmap = plt.get_cmap("YlGnBu").copy()
    cmap.set_bad("#E8E8E8")
    fig, ax = plt.subplots(figsize=(8.0, 5.3))
    image = ax.imshow(
        np.ma.masked_invalid(values), aspect="auto", cmap=cmap, vmin=0, vmax=100
    )
    ax.set_xticks(range(len(dimension_labels)), dimension_labels)
    ax.set_yticks(range(len(names)), names)
    ax.set_title("人工确认主题的评分维度构成")
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            value = values[row, column]
            ax.text(
                column,
                row,
                "缺失" if np.isnan(value) else f"{value:.0f}",
                ha="center",
                va="center",
                fontsize=7,
            )
    fig.colorbar(image, ax=ax, label="维度分（0–100）", shrink=0.82)
    save_figure(fig, stems[6])


def build_topic_rank_sensitivity() -> None:
    keys = [
        "multi_source_direction",
        "record_scale",
        "interaction_signal",
        "recency_signal",
    ]
    rng = np.random.default_rng(20261118)
    weights = rng.dirichlet(np.ones(len(keys)), size=20000)
    scores = np.zeros((len(weights), len(topics)), dtype=np.float64)
    for topic_index, topic in enumerate(topics):
        available = np.asarray(
            [topic["dimension_scores"][key] is not None for key in keys]
        ).astype(bool)
        values = np.asarray(
            [
                0.0
                if topic["dimension_scores"][key] is None
                else topic["dimension_scores"][key]
                for key in keys
            ],
            dtype=np.float64,
        )
        topic_weights = weights[:, available]
        topic_weights /= topic_weights.sum(axis=1, keepdims=True)
        scores[:, topic_index] = topic_weights @ values[available]
    ranks = np.argsort(np.argsort(-scores, axis=1), axis=1) + 1
    lower, median, upper = np.quantile(ranks, [0.1, 0.5, 0.9], axis=0)
    top_three = np.mean(ranks <= 3, axis=0)
    order = np.argsort([int(topic["priority"]) for topic in topics])
    y = np.arange(len(topics))
    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    ax.errorbar(
        median[order],
        y,
        xerr=np.vstack([median[order] - lower[order], upper[order] - median[order]]),
        fmt="o",
        color=BLUE,
        ecolor=BLUE_LIGHT,
        capsize=2,
        markersize=5,
    )
    ax.set_yticks(
        y,
        [
            f"{topics[index]['topic_id']} · {topics[index]['record_count']} 条 · "
            f"前三 {top_three[index]:.0%}"
            for index in order
        ],
    )
    ax.invert_yaxis()
    ax.set_xlim(14.5, 0.5)
    ax.set_xticks(range(1, len(topics) + 1))
    ax.set_xlabel("排名（1 为最高）")
    ax.set_title("均匀权重扰动下的主题排名区间")
    ax.text(
        0.99,
        -0.09,
        "误差线：第 10–90 百分位；Top 3 为 20,000 次均匀 Dirichlet 权重抽样中的比例",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
    )
    save_figure(fig, stems[7])


def build_method_diagram() -> None:
    fig, ax = plt.subplots(figsize=(8.4, 6.0))
    ax.set_xlim(0, 8.4)
    ax.set_ylim(0, 6.0)
    ax.axis("off")
    nodes = [
        (0.35, 4.65, "多源公开文本\n检索与批次", BLUE),
        (3.05, 4.65, "清洗与审计\n来源、重复、质量", GREEN),
        (5.75, 4.65, "机会条件判别\n需求 × AI × 可行性", "#6A7A89"),
        (5.75, 2.95, "分层复核\n辅助裁定与人工确认", "#9A4D8E"),
        (3.05, 2.95, "语义主题\n聚类与命名", "#D08A34"),
        (0.35, 2.95, "价值排序\n证据与维度分", "#3A8F70"),
    ]
    width = 2.3
    height = 0.92
    for x, y, label, color in nodes:
        box = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.08,rounding_size=0.08",
            facecolor="white",
            edgecolor=color,
            linewidth=1.7,
        )
        ax.add_patch(box)
        ax.text(
            x + width / 2, y + height / 2, label, ha="center", va="center", fontsize=10
        )
    for start_x, end_x, row_y in [(2.65, 3.05, 5.11), (5.35, 5.75, 5.11)]:
        ax.add_patch(
            FancyArrowPatch(
                (start_x, row_y),
                (end_x, row_y),
                arrowstyle="-|>",
                mutation_scale=13,
                linewidth=1.2,
                color=GRAY,
            )
        )
    for start_x, end_x in [(5.72, 5.38), (3.02, 2.68)]:
        ax.add_patch(
            FancyArrowPatch(
                (start_x, 3.41),
                (end_x, 3.41),
                arrowstyle="-|>",
                mutation_scale=13,
                linewidth=1.2,
                color=GRAY,
            )
        )
    ax.add_patch(
        FancyArrowPatch(
            (6.9, 4.62),
            (6.9, 3.93),
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.2,
            color=GRAY,
        )
    )
    proxy_box = FancyBboxPatch(
        (0.65, 0.55),
        7.1,
        1.55,
        boxstyle="round,pad=0.08,rounding_size=0.08",
        facecolor="#F8FAFC",
        edgecolor=BLUE,
        linestyle="--",
        linewidth=1.5,
    )
    ax.add_patch(proxy_box)
    ax.text(
        4.2,
        1.34,
        "研究性分类器对照\n509 条用户审阅采纳的标签 · 冻结 E5 与字符 TF-IDF\n"
        "重复嵌套验证 · 评估对采纳标签的复现，不是独立人工真值",
        ha="center",
        va="center",
        fontsize=9.5,
    )
    ax.add_patch(
        FancyArrowPatch(
            (6.9, 2.9),
            (6.9, 2.17),
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.2,
            color=BLUE,
            linestyle="--",
        )
    )
    ax.text(
        0.35,
        5.84,
        "公开文本机会发现与人工标签实验",
        fontsize=13,
        weight="bold",
        color=BLUE,
    )
    save_figure(fig, stems[8])


def build_classifier_family() -> None:
    model_keys = list(nested["models"])
    colors = [GRAY, "#A7A7A7", "#9FB1CF", "#6482B5", BLUE]
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.0), sharex=True)
    for axis, metric, title in zip(
        axes,
        ["average_precision", "roc_auc"],
        ["平均精确率 AP", "ROC-AUC"],
        strict=True,
    ):
        for index, (model_key, color) in enumerate(
            zip(model_keys, colors, strict=True)
        ):
            values = nested["metrics"][model_key]["repeated_fold_metrics"][metric]
            axis.errorbar(
                values["mean"],
                index,
                xerr=values["sd"],
                fmt="o",
                color=color,
                ecolor=color,
                capsize=3,
                markersize=6,
            )
            axis.text(
                min(values["mean"] + values["sd"] + 0.025, 0.96),
                index,
                f"{values['mean']:.2f} ± {values['sd']:.2f}",
                va="center",
                fontsize=7,
            )
        axis.set_xlim(0, 1)
        axis.set_ylim(-0.6, len(model_keys) - 0.4)
        axis.set_yticks(
            range(len(model_keys)),
            [nested["models"][key] for key in model_keys],
        )
        axis.invert_yaxis()
        axis.set_title(title)
        axis.grid(axis="x", color="#DDDDDD", linewidth=0.6)
    fig.suptitle("五类文本分类方法：重复五折嵌套验证", y=1.04)
    save_figure(fig, stems[9])


def build_source_holdout() -> None:
    source_order = [
        source
        for source in SOURCE_ORDER
        if any(row["held_out_source"] == source for row in source_holdout_rows)
    ]
    model_keys = PRIMARY_MODELS
    counts = {
        source: next(
            int(row["test_records"])
            for row in source_holdout_rows
            if row["held_out_source"] == source
        )
        for source in source_order
    }
    positives = {
        source: next(
            int(row["proxy_opportunities"])
            for row in source_holdout_rows
            if row["held_out_source"] == source
        )
        for source in source_order
    }
    matrix = np.full((len(model_keys), len(source_order)), np.nan)
    for row in source_holdout_rows:
        if row["model"] in model_keys and row["average_precision"] not in {"", None}:
            matrix[
                model_keys.index(row["model"]),
                source_order.index(row["held_out_source"]),
            ] = float(row["average_precision"])
    cmap = plt.get_cmap("YlGnBu").copy()
    cmap.set_bad("#E8E8E8")
    fig, ax = plt.subplots(figsize=(9.1, 3.8))
    image = ax.imshow(
        np.ma.masked_invalid(matrix), aspect="auto", cmap=cmap, vmin=0, vmax=0.65
    )
    ax.set_xticks(
        range(len(source_order)),
        [
            f"{source}\n(n={counts[source]}, 机会={positives[source]})"
            for source in source_order
        ],
    )
    ax.set_yticks(range(len(model_keys)), [nested["models"][key] for key in model_keys])
    ax.set_title("整站留出验证：训练数据不含测试来源")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = matrix[row, column]
            ax.text(
                column,
                row,
                "不可估" if np.isnan(value) else f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=8,
            )
    fig.colorbar(image, ax=ax, label="人工复核标签平均精确率 AP", shrink=0.86)
    save_figure(fig, stems[10])


setup_plot()
build_weekly_source_heatmap()
build_source_quality_heatmap()
build_review_sample_composition()
build_classifier_comparison()
build_classifier_oof()
build_embedding_pca()
build_topic_dimension_heatmap()
build_topic_rank_sensitivity()
build_method_diagram()
build_classifier_family()
build_source_holdout()
print(
    json.dumps(
        {"figures": stems, "formats": ["pdf", "png", "svg"]},
        ensure_ascii=False,
        indent=2,
    )
)
