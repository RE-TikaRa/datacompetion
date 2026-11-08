import csv

from scripts.assistant_review import AssistantReviewBatch, build_attention_files


def test_assistant_review_accepts_result_alias():
    result = AssistantReviewBatch.model_validate(
        {
            "reviews": [
                {
                    "record_id": "S00001",
                    "is_opportunity": False,
                    "confidence": 0.8,
                    "functional_category": "",
                    "industry": "",
                    "rationale": "仅为产品介绍，没有终端需求证据。",
                    "evidence": ["产品介绍"],
                    "boundary_case": False,
                }
            ]
        }
    )
    assert result.items[0].record_id == "S00001"


def test_attention_list_contains_disagreements_and_boundary_cases(tmp_path):
    queue = [
        {
            "record_id": "S00001",
            "batch_id": "B01",
            "source_name": "论坛",
            "content_kind": "body",
            "title": "记录一",
            "content_path": "results/B01/text/one.md",
            "model_is_opportunity": 1,
        },
        {
            "record_id": "S00002",
            "batch_id": "B01",
            "source_name": "论坛",
            "content_kind": "body",
            "title": "记录二",
            "content_path": "results/B01/text/two.md",
            "model_is_opportunity": 0,
        },
    ]
    items = [
        {
            "record_id": "S00001",
            "is_opportunity": False,
            "confidence": 0.9,
            "rationale": "没有明确需求。",
            "evidence": ["介绍内容"],
            "boundary_case": False,
        },
        {
            "record_id": "S00002",
            "is_opportunity": False,
            "confidence": 0.6,
            "rationale": "需求表达不完整。",
            "evidence": ["相关内容"],
            "boundary_case": True,
        },
    ]
    build_attention_files(queue, items, tmp_path)
    with (tmp_path / "human_attention.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert [row["记录编号"] for row in rows] == ["S00001", "S00002"]
