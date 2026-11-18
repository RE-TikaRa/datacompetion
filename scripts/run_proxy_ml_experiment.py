import argparse
import csv
import json
import warnings
from collections import Counter
from pathlib import Path
from typing import cast

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.naive_bayes import ComplementNB
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.utils.class_weight import compute_sample_weight

from opportunity.embedding import TextEmbedder
from opportunity.files import read_jsonl

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser(
    description="比较文本机会代理标签的线性模型与神经网络。"
)
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
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()


def project_path(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


cleaning_run = project_path(args.cleaning_run)
review_run = project_path(args.review_run)
output = project_path(args.output)
if not cleaning_run.is_relative_to(ROOT / "results"):
    parser.error("cleaning-run 必须位于项目 results 目录内。")
if not review_run.is_relative_to(ROOT / "results"):
    parser.error("review-run 必须位于项目 results 目录内。")
if not output.is_relative_to(ROOT / "results"):
    parser.error("output 必须位于项目 results 目录内。")
if output.exists():
    parser.error(f"输出目录已经存在：{output}")

records = read_jsonl(cleaning_run / "records.jsonl")
proxy = read_jsonl(review_run / "assistant_review_proxy.jsonl")
records_by_id = {record["record_id"]: record for record in records}
proxy_ids = [row["record_id"] for row in proxy]
if len(proxy_ids) != len(set(proxy_ids)):
    parser.error("代理复核文件包含重复 record_id。")
if not set(proxy_ids).issubset(records_by_id):
    parser.error("代理复核记录与清洗批次不匹配。")

labels = np.asarray([int(row["is_opportunity"]) for row in proxy], dtype=np.int64)
if set(labels) != {0, 1}:
    parser.error("代理标签必须同时包含机会与非机会记录。")

texts = []
for row in proxy:
    record = records_by_id[row["record_id"]]
    content = (cleaning_run / record["content_path"]).read_text(encoding="utf-8")
    texts.append((record["title"] + "\n" + content)[:12000])

embedder = TextEmbedder(ROOT)
batch_size = embedder.config["batch_size"]
embeddings = np.concatenate(
    [
        embedder.encode(texts[start : start + batch_size])
        for start in range(0, len(texts), batch_size)
    ],
    axis=0,
)

splitter = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=20261118)
model_names = {
    "char_tfidf_lr": "字符 TF-IDF + 逻辑回归",
    "e5_lr": "冻结 E5 + 逻辑回归",
    "e5_mlp": "冻结 E5 + MLP 神经网络",
}
probability_sums = {
    name: np.zeros(len(proxy), dtype=np.float64) for name in model_names
}
prediction_counts = np.zeros(len(proxy), dtype=np.int64)
fold_metrics = []
convergence = Counter()


def fold_scores(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    predictions = probabilities >= 0.5
    actual = y_true.astype(bool)
    true_positive = int(np.count_nonzero(actual & predictions))
    false_positive = int(np.count_nonzero(~actual & predictions))
    false_negative = int(np.count_nonzero(actual & ~predictions))
    true_negative = int(np.count_nonzero(~actual & ~predictions))
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0.0
    )
    recall = true_positive / (true_positive + false_negative)
    f1 = (
        2 * true_positive / (2 * true_positive + false_positive + false_negative)
        if 2 * true_positive + false_positive + false_negative
        else 0.0
    )
    negative_f1 = (
        2 * true_negative / (2 * true_negative + false_positive + false_negative)
        if 2 * true_negative + false_positive + false_negative
        else 0.0
    )
    return {
        "average_precision": float(average_precision_score(y_true, probabilities)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "macro_f1": (f1 + negative_f1) / 2,
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predictions)),
    }


for fold_number, (train_indices, test_indices) in enumerate(
    splitter.split(texts, labels), start=1
):
    repeat = (fold_number - 1) // 5 + 1
    fold = (fold_number - 1) % 5 + 1
    y_train = labels[train_indices]
    y_test = labels[test_indices]

    char_model = make_pipeline(
        TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 5),
            min_df=2,
            max_features=50000,
            sublinear_tf=True,
            max_df=0.98,
        ),
        LogisticRegression(
            C=1.0,
            class_weight="balanced",
            max_iter=3000,
            solver="liblinear",
            random_state=20261118 + fold_number,
        ),
    )
    char_model.fit([texts[index] for index in train_indices], y_train)
    char_probabilities = char_model.predict_proba(
        [texts[index] for index in test_indices]
    )[:, 1]

    scaler = StandardScaler()
    x_train = scaler.fit_transform(embeddings[train_indices])
    x_test = scaler.transform(embeddings[test_indices])
    linear_model = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=3000,
        solver="liblinear",
        random_state=20261118 + fold_number,
    )
    linear_model.fit(x_train, y_train)
    linear_probabilities = linear_model.predict_proba(x_test)[:, 1]

    neural_model = MLPClassifier(
        hidden_layer_sizes=(64, 32),
        alpha=0.1,
        learning_rate_init=0.001,
        max_iter=300,
        n_iter_no_change=20,
        random_state=20261118 + fold_number,
        tol=0.0001,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        neural_model.fit(
            x_train,
            y_train,
            sample_weight=compute_sample_weight("balanced", y_train),
        )
    convergence["mlp_non_converged_folds"] += sum(
        issubclass(warning.category, ConvergenceWarning) for warning in caught
    )
    neural_probabilities = cast(np.ndarray, neural_model.predict_proba(x_test))[:, 1]

    predictions_by_model = {
        "char_tfidf_lr": char_probabilities,
        "e5_lr": linear_probabilities,
        "e5_mlp": neural_probabilities,
    }
    for model_name, probabilities in predictions_by_model.items():
        probability_sums[model_name][test_indices] += probabilities
        fold_metrics.append(
            {
                "repeat": repeat,
                "fold": fold,
                "model": model_name,
                "test_records": len(test_indices),
                **fold_scores(y_test, probabilities),
            }
        )
    prediction_counts[test_indices] += 1

if not np.all(prediction_counts == 5):
    raise RuntimeError("每条记录应恰好获得五次折外预测。")

mean_probabilities = {
    name: values / prediction_counts for name, values in probability_sums.items()
}
summary = {}
for model_name in model_names:
    rows = [row for row in fold_metrics if row["model"] == model_name]
    summary[model_name] = {
        "display_name": model_names[model_name],
        "repeated_fold_metrics": {
            metric: {
                "mean": float(np.mean([row[metric] for row in rows])),
                "sd": float(np.std([row[metric] for row in rows], ddof=1)),
            }
            for metric in rows[0]
            if metric not in {"repeat", "fold", "model", "test_records"}
        },
        "pooled_mean_oof_metrics": fold_scores(labels, mean_probabilities[model_name]),
    }

nested_model_names = {
    "char_tfidf_lr": "字符 TF-IDF + 逻辑回归",
    "char_complement_nb": "字符 TF-IDF + ComplementNB",
    "e5_lr": "冻结 E5 + 逻辑回归",
    "e5_rbf_svc": "冻结 E5 + RBF-SVM",
    "e5_mlp_nested": "冻结 E5 + 内层选择 MLP",
}
mlp_configs: list[tuple[tuple[int, ...], float]] = [
    ((8,), 0.1),
    ((8,), 1.0),
    ((16,), 0.1),
    ((16,), 1.0),
]
nested_splitter = RepeatedStratifiedKFold(
    n_splits=5, n_repeats=2, random_state=20261119
)
nested_probability_sums = {
    name: np.zeros(len(proxy), dtype=np.float64) for name in nested_model_names
}
nested_prediction_counts = np.zeros(len(proxy), dtype=np.int64)
nested_fold_metrics = []
nested_selections = []
nested_convergence = Counter()

for outer_number, (train_indices, test_indices) in enumerate(
    nested_splitter.split(texts, labels), start=1
):
    outer_repeat = (outer_number - 1) // 5 + 1
    outer_fold = (outer_number - 1) % 5 + 1
    y_train = labels[train_indices]
    y_test = labels[test_indices]
    train_texts = [texts[index] for index in train_indices]

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 5),
        min_df=2,
        max_features=50000,
        sublinear_tf=True,
        max_df=0.98,
    )
    x_char_train = vectorizer.fit_transform(train_texts)
    x_char_test = vectorizer.transform([texts[index] for index in test_indices])
    char_model = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=3000,
        solver="liblinear",
        random_state=20261119 + outer_number,
    )
    char_model.fit(x_char_train, y_train)
    char_probabilities = cast(
        np.ndarray,
        char_model.predict_proba(x_char_test),
    )[:, 1]
    complement_model = ComplementNB(alpha=1.0, norm=True)
    complement_model.fit(
        x_char_train,
        y_train,
        sample_weight=compute_sample_weight("balanced", y_train),
    )
    complement_probabilities = cast(
        np.ndarray, complement_model.predict_proba(x_char_test)
    )[:, 1]

    scaler = StandardScaler()
    x_train = scaler.fit_transform(embeddings[train_indices])
    x_test = scaler.transform(embeddings[test_indices])
    linear_model = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=3000,
        solver="liblinear",
        random_state=20261119 + outer_number,
    )
    linear_model.fit(x_train, y_train)
    linear_probabilities = cast(np.ndarray, linear_model.predict_proba(x_test))[:, 1]

    rbf_model = CalibratedClassifierCV(
        estimator=SVC(
            C=1.0,
            class_weight="balanced",
            gamma="scale",
            kernel="rbf",
            random_state=20261119 + outer_number,
        ),
        cv=3,
        method="sigmoid",
    )
    rbf_model.fit(
        x_train,
        y_train,
        sample_weight=compute_sample_weight("balanced", y_train),
    )
    rbf_probabilities = cast(np.ndarray, rbf_model.predict_proba(x_test))[:, 1]

    inner_splitter = RepeatedStratifiedKFold(
        n_splits=3, n_repeats=1, random_state=20262119 + outer_number
    )
    config_results = []
    for hidden_layer_sizes, alpha in mlp_configs:
        inner_scores = []
        for inner_train, inner_valid in inner_splitter.split(train_texts, y_train):
            inner_scaler = StandardScaler()
            inner_x_train = inner_scaler.fit_transform(
                embeddings[train_indices][inner_train]
            )
            inner_x_valid = inner_scaler.transform(
                embeddings[train_indices][inner_valid]
            )
            inner_model = MLPClassifier(
                hidden_layer_sizes=hidden_layer_sizes,
                alpha=alpha,
                learning_rate_init=0.001,
                max_iter=1000,
                n_iter_no_change=25,
                random_state=20263119 + outer_number,
                tol=0.0001,
            )
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ConvergenceWarning)
                inner_model.fit(
                    inner_x_train,
                    y_train[inner_train],
                    sample_weight=compute_sample_weight(
                        "balanced", y_train[inner_train]
                    ),
                )
            nested_convergence["inner_non_converged_fits"] += sum(
                issubclass(warning.category, ConvergenceWarning) for warning in caught
            )
            inner_probabilities = cast(
                np.ndarray, inner_model.predict_proba(inner_x_valid)
            )[:, 1]
            inner_scores.append(
                float(
                    average_precision_score(y_train[inner_valid], inner_probabilities)
                )
            )
        config_results.append(
            {
                "hidden_layer_sizes": hidden_layer_sizes,
                "alpha": alpha,
                "mean_inner_average_precision": float(np.mean(inner_scores)),
            }
        )

    selected = max(
        config_results, key=lambda result: result["mean_inner_average_precision"]
    )
    outer_model = MLPClassifier(
        hidden_layer_sizes=selected["hidden_layer_sizes"],
        alpha=selected["alpha"],
        learning_rate_init=0.001,
        max_iter=1000,
        n_iter_no_change=25,
        random_state=20264119 + outer_number,
        tol=0.0001,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        outer_model.fit(
            x_train,
            y_train,
            sample_weight=compute_sample_weight("balanced", y_train),
        )
    nested_convergence["outer_non_converged_folds"] += sum(
        issubclass(warning.category, ConvergenceWarning) for warning in caught
    )
    neural_probabilities = cast(np.ndarray, outer_model.predict_proba(x_test))[:, 1]

    nested_predictions = {
        "char_tfidf_lr": char_probabilities,
        "char_complement_nb": complement_probabilities,
        "e5_lr": linear_probabilities,
        "e5_rbf_svc": rbf_probabilities,
        "e5_mlp_nested": neural_probabilities,
    }
    for model_name, probabilities in nested_predictions.items():
        nested_probability_sums[model_name][test_indices] += probabilities
        nested_fold_metrics.append(
            {
                "repeat": outer_repeat,
                "fold": outer_fold,
                "model": model_name,
                "test_records": len(test_indices),
                **fold_scores(y_test, probabilities),
            }
        )
    nested_prediction_counts[test_indices] += 1
    nested_selections.append(
        {
            "repeat": outer_repeat,
            "fold": outer_fold,
            "selected_hidden_layer_sizes": selected["hidden_layer_sizes"],
            "selected_alpha": selected["alpha"],
            "mean_inner_average_precision": selected["mean_inner_average_precision"],
            "candidate_results": config_results,
        }
    )

if not np.all(nested_prediction_counts == 2):
    raise RuntimeError("嵌套交叉验证中每条记录应恰好获得两次折外预测。")

nested_mean_probabilities = {
    name: values / nested_prediction_counts
    for name, values in nested_probability_sums.items()
}

source_holdout_metrics = []
source_holdout_selections = []
source_holdout_convergence = Counter()
source_names = sorted({records_by_id[row["record_id"]]["source_name"] for row in proxy})
for source_number, source_name in enumerate(source_names, start=1):
    test_indices = np.asarray(
        [
            index
            for index, row in enumerate(proxy)
            if records_by_id[row["record_id"]]["source_name"] == source_name
        ],
        dtype=np.int64,
    )
    test_index_set = set(test_indices)
    train_indices = np.asarray(
        [index for index in range(len(proxy)) if index not in test_index_set],
        dtype=np.int64,
    )
    y_train = labels[train_indices]
    y_test = labels[test_indices]
    train_texts = [texts[index] for index in train_indices]

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 5),
        min_df=2,
        max_features=50000,
        sublinear_tf=True,
        max_df=0.98,
    )
    char_train = vectorizer.fit_transform(train_texts)
    char_test = vectorizer.transform([texts[index] for index in test_indices])
    char_model = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=3000,
        solver="liblinear",
        random_state=20265119 + source_number,
    )
    char_model.fit(char_train, y_train)
    char_probabilities = cast(np.ndarray, char_model.predict_proba(char_test))[:, 1]

    scaler = StandardScaler()
    e5_train = scaler.fit_transform(embeddings[train_indices])
    e5_test = scaler.transform(embeddings[test_indices])
    linear_model = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=3000,
        solver="liblinear",
        random_state=20266119 + source_number,
    )
    linear_model.fit(e5_train, y_train)
    linear_probabilities = cast(np.ndarray, linear_model.predict_proba(e5_test))[:, 1]

    inner_splitter = RepeatedStratifiedKFold(
        n_splits=3, n_repeats=1, random_state=20267119 + source_number
    )
    source_config_results = []
    for hidden_layer_sizes, alpha in mlp_configs:
        inner_scores = []
        for inner_train, inner_valid in inner_splitter.split(train_texts, y_train):
            inner_scaler = StandardScaler()
            inner_e5_train = inner_scaler.fit_transform(
                embeddings[train_indices][inner_train]
            )
            inner_e5_valid = inner_scaler.transform(
                embeddings[train_indices][inner_valid]
            )
            inner_model = MLPClassifier(
                hidden_layer_sizes=hidden_layer_sizes,
                alpha=alpha,
                learning_rate_init=0.001,
                max_iter=1000,
                n_iter_no_change=25,
                random_state=20268119 + source_number,
                tol=0.0001,
            )
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ConvergenceWarning)
                inner_model.fit(
                    inner_e5_train,
                    y_train[inner_train],
                    sample_weight=compute_sample_weight(
                        "balanced", y_train[inner_train]
                    ),
                )
            source_holdout_convergence["inner_non_converged_fits"] += sum(
                issubclass(warning.category, ConvergenceWarning) for warning in caught
            )
            inner_probabilities = cast(
                np.ndarray, inner_model.predict_proba(inner_e5_valid)
            )[:, 1]
            inner_scores.append(
                float(
                    average_precision_score(y_train[inner_valid], inner_probabilities)
                )
            )
        source_config_results.append(
            {
                "hidden_layer_sizes": hidden_layer_sizes,
                "alpha": alpha,
                "mean_inner_average_precision": float(np.mean(inner_scores)),
            }
        )
    selected_source_config = max(
        source_config_results,
        key=lambda result: result["mean_inner_average_precision"],
    )
    source_mlp = MLPClassifier(
        hidden_layer_sizes=selected_source_config["hidden_layer_sizes"],
        alpha=selected_source_config["alpha"],
        learning_rate_init=0.001,
        max_iter=1000,
        n_iter_no_change=25,
        random_state=20269119 + source_number,
        tol=0.0001,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        source_mlp.fit(
            e5_train,
            y_train,
            sample_weight=compute_sample_weight("balanced", y_train),
        )
    source_holdout_convergence["outer_non_converged_fits"] += sum(
        issubclass(warning.category, ConvergenceWarning) for warning in caught
    )
    mlp_probabilities = cast(np.ndarray, source_mlp.predict_proba(e5_test))[:, 1]

    source_predictions = {
        "char_tfidf_lr": char_probabilities,
        "e5_lr": linear_probabilities,
        "e5_mlp_nested": mlp_probabilities,
    }
    source_holdout_selections.append(
        {
            "held_out_source": source_name,
            "selected_hidden_layer_sizes": selected_source_config["hidden_layer_sizes"],
            "selected_alpha": selected_source_config["alpha"],
            "candidate_results": source_config_results,
        }
    )
    for model_name, probabilities in source_predictions.items():
        source_predicted = probabilities >= 0.5
        source_truth = y_test.astype(bool)
        true_positive = int(np.count_nonzero(source_truth & source_predicted))
        false_positive = int(np.count_nonzero(~source_truth & source_predicted))
        false_negative = int(np.count_nonzero(source_truth & ~source_predicted))
        source_holdout_metrics.append(
            {
                "held_out_source": source_name,
                "model": model_name,
                "test_records": len(test_indices),
                "proxy_opportunities": int(y_test.sum()),
                "proxy_non_opportunities": int(len(y_test) - y_test.sum()),
                "average_precision": float(
                    average_precision_score(y_test, probabilities)
                )
                if y_test.sum()
                else None,
                "roc_auc": float(roc_auc_score(y_test, probabilities))
                if len(set(y_test)) == 2
                else None,
                "precision_at_0_5": true_positive / (true_positive + false_positive)
                if true_positive + false_positive
                else 0.0,
                "recall_at_0_5": true_positive / (true_positive + false_negative)
                if true_positive + false_negative
                else None,
            }
        )

nested_summary = {}
for model_name in nested_model_names:
    rows = [row for row in nested_fold_metrics if row["model"] == model_name]
    nested_summary[model_name] = {
        "display_name": nested_model_names[model_name],
        "repeated_fold_metrics": {
            metric: {
                "mean": float(np.mean([row[metric] for row in rows])),
                "sd": float(np.std([row[metric] for row in rows], ddof=1)),
            }
            for metric in rows[0]
            if metric not in {"repeat", "fold", "model", "test_records"}
        },
        "pooled_mean_oof_metrics": fold_scores(
            labels, nested_mean_probabilities[model_name]
        ),
    }

output.mkdir(parents=True)
np.save(output / "e5_embeddings.npy", embeddings)
with (output / "fold_metrics.csv").open(
    "w", encoding="utf-8-sig", newline=""
) as stream:
    writer = csv.DictWriter(stream, fieldnames=list(fold_metrics[0]))
    writer.writeheader()
    writer.writerows(fold_metrics)

prediction_rows = []
for index, row in enumerate(proxy):
    record = records_by_id[row["record_id"]]
    prediction_rows.append(
        {
            "record_id": row["record_id"],
            "proxy_is_opportunity": int(row["is_opportunity"]),
            "proxy_boundary_case": int(row["boundary_case"]),
            "source_name": record["source_name"],
            "content_kind": record["content_kind"],
            **{
                f"{name}_probability": round(float(mean_probabilities[name][index]), 8)
                for name in model_names
            },
        }
    )
with (output / "oof_predictions.csv").open(
    "w", encoding="utf-8-sig", newline=""
) as stream:
    writer = csv.DictWriter(stream, fieldnames=list(prediction_rows[0]))
    writer.writeheader()
    writer.writerows(prediction_rows)

with (output / "nested_fold_metrics.csv").open(
    "w", encoding="utf-8-sig", newline=""
) as stream:
    writer = csv.DictWriter(stream, fieldnames=list(nested_fold_metrics[0]))
    writer.writeheader()
    writer.writerows(nested_fold_metrics)

nested_prediction_rows = []
for index, row in enumerate(proxy):
    record = records_by_id[row["record_id"]]
    nested_prediction_rows.append(
        {
            "record_id": row["record_id"],
            "proxy_is_opportunity": int(row["is_opportunity"]),
            "proxy_boundary_case": int(row["boundary_case"]),
            "source_name": record["source_name"],
            "content_kind": record["content_kind"],
            **{
                f"{name}_probability": round(
                    float(nested_mean_probabilities[name][index]), 8
                )
                for name in nested_model_names
            },
        }
    )
with (output / "nested_oof_predictions.csv").open(
    "w", encoding="utf-8-sig", newline=""
) as stream:
    writer = csv.DictWriter(stream, fieldnames=list(nested_prediction_rows[0]))
    writer.writeheader()
    writer.writerows(nested_prediction_rows)

(output / "nested_model_selection.json").write_text(
    json.dumps(nested_selections, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

with (output / "source_holdout_metrics.csv").open(
    "w", encoding="utf-8-sig", newline=""
) as stream:
    writer = csv.DictWriter(stream, fieldnames=list(source_holdout_metrics[0]))
    writer.writeheader()
    writer.writerows(source_holdout_metrics)

(output / "source_holdout_model_selection.json").write_text(
    json.dumps(source_holdout_selections, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

experiment = {
    "batch_id": "B01",
    "target": "AI代理机会标签，不是真人真值",
    "review_records": len(proxy),
    "proxy_opportunities": int(labels.sum()),
    "proxy_non_opportunities": int(len(labels) - labels.sum()),
    "boundary_records": sum(row["boundary_case"] for row in proxy),
    "encoder": embedder.metadata(),
    "fixed_configuration_pilot": {
        "cv": {
            "method": "RepeatedStratifiedKFold",
            "folds": 5,
            "repeats": 5,
            "random_state": 20261118,
            "decision_threshold": 0.5,
            "summary_sd": "fold-to-fold variability; not a confidence interval",
            "all_predictions_are_out_of_fold": True,
        },
        "mlp": {
            "hidden_layer_sizes": [64, 32],
            "alpha": 0.1,
            "learning_rate_init": 0.001,
            "max_iter": 300,
            "class_weighting": "balanced sample_weight",
            **convergence,
        },
        "models": model_names,
        "metrics": summary,
    },
    "nested_experiment": {
        "cv": {
            "method": "RepeatedStratifiedKFold with inner StratifiedKFold selection",
            "outer_folds": 5,
            "outer_repeats": 2,
            "inner_folds": 3,
            "outer_random_state": 20261119,
            "decision_threshold": 0.5,
            "summary_sd": "outer-fold variability; not a confidence interval",
            "all_predictions_are_out_of_fold": True,
        },
        "models": nested_model_names,
        "mlp_selection_metric": "mean inner-fold average precision",
        "mlp_candidates": [
            {
                "hidden_layer_sizes": list(hidden_layer_sizes),
                "alpha": alpha,
            }
            for hidden_layer_sizes, alpha in mlp_configs
        ],
        "mlp_max_iter": 1000,
        "mlp_class_weighting": "balanced sample_weight",
        "mlp_convergence": dict(nested_convergence),
        "complement_nb": {"alpha": 1.0, "norm": True},
        "rbf_svc": {
            "C": 1.0,
            "gamma": "scale",
            "calibration": "three-fold sigmoid calibration within outer training set",
            "class_weighting": "balanced sample_weight",
        },
        "selected_hyperparameters_by_outer_fold": nested_selections,
        "metrics": nested_summary,
    },
    "source_holdout_experiment": {
        "method": "leave-one-source-out validation",
        "source_count": len(source_names),
        "positive_class_absent_sources": [
            source_name
            for source_name in source_names
            if not any(
                records_by_id[row["record_id"]]["source_name"] == source_name
                and row["is_opportunity"]
                for row in proxy
            )
        ],
        "mlp_selection": "three-fold validation within each four-source training set",
        "mlp_convergence": dict(source_holdout_convergence),
        "metrics": source_holdout_metrics,
        "limitations": [
            "The five source groups have strongly unequal positive counts.",
            "A held-out source without proxy positives has no estimable "
            "average precision or ROC AUC.",
            "Results describe this cohort, not source-population performance.",
        ],
    },
    "source_counts": dict(
        Counter(records_by_id[row["record_id"]]["source_name"] for row in proxy)
    ),
    "content_kind_counts": dict(
        Counter(records_by_id[row["record_id"]]["content_kind"] for row in proxy)
    ),
    "limitations": [
        "The 509 labels were produced by an AI proxy; "
        "they do not measure human agreement.",
        "The cohort includes all 269 original candidates and 240 purposively "
        "sampled negatives.",
        "Cross-validation describes this cohort and cannot estimate full-batch "
        "accuracy.",
        "No probability calibration or independent external test set was performed.",
    ],
    "outputs": {
        "fold_metrics": (output / "fold_metrics.csv").relative_to(ROOT).as_posix(),
        "oof_predictions": (output / "oof_predictions.csv")
        .relative_to(ROOT)
        .as_posix(),
        "nested_fold_metrics": (output / "nested_fold_metrics.csv")
        .relative_to(ROOT)
        .as_posix(),
        "nested_oof_predictions": (output / "nested_oof_predictions.csv")
        .relative_to(ROOT)
        .as_posix(),
        "nested_model_selection": (output / "nested_model_selection.json")
        .relative_to(ROOT)
        .as_posix(),
        "source_holdout_metrics": (output / "source_holdout_metrics.csv")
        .relative_to(ROOT)
        .as_posix(),
        "source_holdout_model_selection": (
            output / "source_holdout_model_selection.json"
        )
        .relative_to(ROOT)
        .as_posix(),
        "embeddings": (output / "e5_embeddings.npy").relative_to(ROOT).as_posix(),
    },
}
(output / "experiment.json").write_text(
    json.dumps(experiment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "output": output.relative_to(ROOT).as_posix(),
            "review_records": len(proxy),
            "proxy_opportunities": int(labels.sum()),
            "fixed_pilot_models": summary,
            "nested_models": nested_summary,
            "mlp_convergence": dict(convergence),
            "nested_mlp_convergence": dict(nested_convergence),
            "source_holdout_mlp_convergence": dict(source_holdout_convergence),
        },
        ensure_ascii=False,
        indent=2,
    )
)
