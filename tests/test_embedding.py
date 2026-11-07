import numpy as np

from opportunity.embedding import TextEmbedder


def test_embedding_is_normalized_and_cross_language():
    vectors = TextEmbedder().encode(
        [
            "AI客服自动回答用户咨询",
            "人工智能支持机器人回应客户问题",
            "一篇无关的天气记录",
        ]
    )
    assert vectors.shape == (3, 384)
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4)
    assert float(vectors[0] @ vectors[1]) > float(vectors[0] @ vectors[2])
