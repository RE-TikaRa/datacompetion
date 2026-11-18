import pytest

from opportunity.judging import (
    JudgmentBatch,
    JudgmentItem,
    exact_source_quote,
    is_opportunity,
    opportunity_confidence,
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
    records = [{"record_id": "S00001", "text": "有人需要，客服工具"}]
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
                evidence=["有人需要客服工具"],
                exclusion_reason="",
            )
        ]
    )
    repairs = validate_batch(result, records, labels)
    assert result.items[0].evidence == ["有人需要，客服工具"]
    assert repairs[0]["model_quote"] == "有人需要客服工具"


def test_quote_normalization_ignores_case_spacing_and_punctuation():
    assert (
        exact_source_quote("agents work in parallel", "Agents work, in parallel.")
        == "Agents work, in parallel"
    )
    assert exact_source_quote("invented quote", "Source text only.") is None


def test_batch_parser_accepts_responses_api_results_key():
    result = JudgmentItem(
        record_id="S00001",
        confidence=0.9,
        observable_demand=False,
        ai_core=False,
        technically_feasible=True,
        excluded=True,
        functional_category="",
        industry="",
        user_need="",
        ai_role="",
        feasibility="",
        evidence=[],
        exclusion_reason="纯新闻转述",
    )
    assert JudgmentBatch.model_validate({"results": [result.model_dump()]}).items == [
        result
    ]
    assert JudgmentBatch.model_validate({"records": [result.model_dump()]}).items == [
        result
    ]
    assert JudgmentBatch.model_validate({"data": [result.model_dump()]}).items == [
        result
    ]


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


def test_opportunity_confidence_is_oriented_to_opportunity_direction():
    assert opportunity_confidence(0.91, True) == pytest.approx(0.91)
    assert opportunity_confidence(0.91, False) == pytest.approx(0.09)


def test_opportunity_threshold_is_applied_after_boolean_gate():
    item = JudgmentItem(
        record_id="S00001",
        confidence=0.49,
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
    assert not is_opportunity(item)
