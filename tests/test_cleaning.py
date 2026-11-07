from opportunity.cleaning import (
    canonical_url,
    deduplicate,
    normalize_content,
    quality_flags,
)
from opportunity.collection import matches_keywords


def test_canonical_url_discards_trackers_and_fragments():
    assert (
        canonical_url("https://EXAMPLE.com/path/?utm_source=feed&ref=topic#comments")
        == "https://example.com/path?ref=topic"
    )


def test_content_cleanup_removes_urls_and_channel_noise():
    text = normalize_content(
        "量子位 | 公众号 QbitAI\n标题 https://example.com/a\n\n正文里的痛点。"
    )
    assert "量子位" not in text
    assert "https://" not in text
    assert "正文里的痛点。" in text


def test_exact_long_content_merges_provenance_and_keeps_short_titles():
    records = [
        {
            "text": "不同来源的项目长说明" * 40,
            "source_url": "https://one.example/item",
            "content_kind": "description",
            "provenance": [{"source_id": "one"}],
        },
        {
            "text": "不同来源的项目长说明" * 40,
            "source_url": "https://two.example/item",
            "content_kind": "body",
            "provenance": [{"source_id": "two"}],
        },
        {
            "text": "发布了一个 AI 工具",
            "source_url": "https://three.example/item",
            "content_kind": "title_only",
            "provenance": [{"source_id": "three"}],
        },
        {
            "text": "发布了一个 AI 工具",
            "source_url": "https://four.example/item",
            "content_kind": "title_only",
            "provenance": [{"source_id": "four"}],
        },
    ]
    retained, duplicates = deduplicate(records)
    assert len(retained) == 3
    assert retained[0]["provenance"] == [{"source_id": "one"}, {"source_id": "two"}]
    assert len(duplicates) == 1


def test_missing_heat_is_not_counted_as_zero():
    row = {
        "content_kind": "body",
        "text": "完整的应用场景描述。" * 20,
        "metrics": {"stars": None},
    }
    assert quality_flags(row) == ["missing_heat"]


def test_collection_direction_keywords_are_applied():
    assert matches_keywords("农业智能问答工具", [])
    assert matches_keywords("农业智能问答工具", ["农业", "医疗"])
    assert not matches_keywords("电商客服助手", ["农业", "医疗"])
