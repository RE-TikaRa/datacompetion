from opportunity.topics import short_title, top_keywords


def test_topic_title_is_bounded():
    assert len(short_title("一" * 100)) <= 48


def test_topic_keywords_drop_single_letter_fragments():
    keywords = top_keywords(
        [
            "AI assistant helps people search documents and answer questions",
            "AI assistant helps people summarize documents",
        ]
    )
    assert all(len(word.strip()) >= 3 for word in keywords if word.isascii())
