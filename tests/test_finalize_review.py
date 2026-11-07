import pytest

from scripts.finalize_review import finalize


def test_finalize_requires_every_review_to_be_complete(tmp_path):
    review = tmp_path / "results" / "B01" / "run" / "review"
    review.mkdir(parents=True)
    (review / "review_queue.jsonl").write_text(
        '{"record_id":"S00001","review_status":"待人工复核"}\n',
        encoding="utf-8",
    )
    (tmp_path / "data" / "reference").mkdir(parents=True)
    (tmp_path / "data" / "reference" / "labels.json").write_text(
        '{"functions":[],"industries":[]}', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="S00001"):
        finalize(review.parent, tmp_path)


def test_finalize_merges_reviewed_sample_into_full_model_labels(tmp_path):
    from opportunity.files import write_json, write_jsonl

    run = tmp_path / "results" / "B01" / "judgement"
    review = run / "review"
    review.mkdir(parents=True)
    write_json(run / "judging.json", {"complete": True, "total_records": 2})
    write_jsonl(
        run / "judgements.jsonl",
        [
            {
                "batch_id": "B01",
                "record_id": "S00001",
                "is_opportunity": True,
                "confidence": 0.8,
                "functional_category": "对话问答",
                "industry": "电商",
            },
            {
                "batch_id": "B01",
                "record_id": "S00002",
                "is_opportunity": False,
                "confidence": 0.9,
                "functional_category": "",
                "industry": "",
            },
        ],
    )
    write_json(
        review / "review_summary.json", {"judgement_run": "results/B01/judgement"}
    )
    write_jsonl(
        review / "review_queue.jsonl",
        [
            {
                "record_id": "S00001",
                "review_status": "已复核",
                "human_is_opportunity": False,
                "human_functional_category": "",
                "human_industry": "",
                "human_notes": "复核后排除",
            },
        ],
    )
    labels = tmp_path / "data/reference"
    labels.mkdir(parents=True)
    write_json(
        labels / "labels.json", {"functions": ["对话问答"], "industries": ["电商"]}
    )
    output = finalize(run, tmp_path)
    import csv

    with (output / "result2.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    final = __import__("json").loads(
        (output / "final_review.json").read_text(encoding="utf-8")
    )
    assert len(rows) == 2
    assert rows[0]["是否构成机会"] == "0"
    assert rows[1]["是否构成机会"] == "0"
    assert final["human_reviewed_records"] == 1
    assert final["model_labels_not_reviewed"] == 1
