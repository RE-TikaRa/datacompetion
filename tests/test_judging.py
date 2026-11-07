import pytest

from opportunity.judging import (
    JudgmentBatch,
    JudgmentItem,
    is_opportunity,
    validate_batch,
)


def test_validate_judgement_requires_allowed_labels_and_evidence():
    labels = {"functions": ["对话问答"], "industries": ["电商"]}
    records = [{"record_id": "S00001", "text": "有没有客服工具"}]
    valid = JudgmentBatch(
        items=[
            JudgmentItem(
                record_id="S00001",
                confidence=0.8,
                observable_demand=True,
                ai_core=True,
                technically_feasible=True,
                excluded=False,
                functional_category="对话问答",
                industry="电商",
                user_need="客服压力",
                ai_role="回答咨询",
                feasibility="成熟模型可实现",
                evidence=["有没有客服工具"],
                exclusion_reason="",
            )
        ]
    )
    validate_batch(valid, records, labels)
    assert is_opportunity(valid.items[0])
    invalid = valid.model_copy(
        update={"items": [valid.items[0].model_copy(update={"evidence": []})]}
    )
    with pytest.raises(ValueError, match="缺少证据"):
        validate_batch(invalid, records, labels)


def test_evidence_must_be_an_exact_source_quote():
    labels = {"functions": ["对话问答"], "industries": ["电商"]}
    records = [{"record_id": "S00001", "text": "有人需要客服工具"}]
    result = JudgmentBatch(
        items=[
            JudgmentItem(
                record_id="S00001",
                confidence=0.9,
                observable_demand=True,
                ai_core=True,
                technically_feasible=True,
                excluded=False,
                functional_category="对话问答",
                industry="电商",
                user_need="客服压力",
                ai_role="回答咨询",
                feasibility="成熟模型可实现",
                evidence=["有没有客服工具"],
                exclusion_reason="",
            )
        ]
    )
    with pytest.raises(ValueError, match="证据不在原文"):
        validate_batch(result, records, labels)


def test_product_without_an_observable_demand_is_not_an_opportunity():
    labels = {"functions": ["对话问答"], "industries": ["电商"]}
    records = [{"record_id": "S00001", "text": "这是一段纯教程"}]
    result = JudgmentBatch(
        items=[
            JudgmentItem(
                record_id="S00001",
                confidence=0.9,
                observable_demand=False,
                ai_core=True,
                technically_feasible=True,
                excluded=False,
                functional_category="",
                industry="",
                user_need="",
                ai_role="",
                feasibility="",
                evidence=[],
                exclusion_reason="纯教程",
            )
        ]
    )
    validate_batch(result, records, labels)
    assert not is_opportunity(result.items[0])
