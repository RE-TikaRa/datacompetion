import csv
import json

from scripts.assistant_review import (
    AssistantReviewBatch,
    build_attention_files,
    build_prompt,
)


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


def test_blind_prompt_omits_automatic_judgement(tmp_path):
    labels = tmp_path / "data" / "reference"
    labels.mkdir(parents=True)
    (labels / "labels.json").write_text(
        json.dumps({"functions": ["对话问答"], "industries": ["教育"]}),
        encoding="utf-8",
    )
    content = tmp_path / "content.md"
    content.write_text("用户需要根据课程资料检索答案。", encoding="utf-8")
    row = {
        "record_id": "S00001",
        "source_name": "论坛",
        "content_kind": "body",
        "title": "课程资料检索",
        "content_path": "content.md",
        "model_is_opportunity": 1,
        "model_confidence": 0.99,
        "observable_demand": True,
        "ai_core": True,
        "technically_feasible": True,
        "excluded": False,
        "model_functional_category": "对话问答",
        "model_industry": "教育",
        "model_evidence": ["用户需要"],
    }
    blind_payload = json.loads(
        build_prompt([row], tmp_path, include_model_judgement=False)
    )
    visible_payload = json.loads(build_prompt([row], tmp_path))
    assert "automatic_judgement" not in blind_payload["records"][0]
    assert blind_payload["records"][0]["content"] == content.read_text(encoding="utf-8")
    assert "automatic_judgement" in visible_payload["records"][0]
