from pathlib import Path
from typing import cast

import numpy as np
import onnxruntime
from tokenizers import Tokenizer

from opportunity.files import ROOT, read_json


class TextEmbedder:
    def __init__(self, root: Path = ROOT) -> None:
        config = read_json(root / "configs/embedding.json")
        manifest = read_json(root / "data/models/multilingual-e5-small/manifest.json")
        if config["revision"] != manifest["revision"]:
            raise ValueError("本地语义模型版本与配置不一致。")
        folder = root / "data/models/multilingual-e5-small"
        self.config = config
        self.tokenizer = Tokenizer.from_file(str(folder / config["tokenizer_file"]))
        self.tokenizer.enable_truncation(max_length=config["max_tokens"])
        self.tokenizer.enable_padding(
            direction="right", pad_id=1, pad_type_id=0, pad_token="<pad>"
        )
        self.session = onnxruntime.InferenceSession(
            str(folder / config["model_file"]), providers=["CPUExecutionProvider"]
        )

    def encode(self, texts: list[str]) -> np.ndarray:
        prepared = [self.config["prefix"] + text for text in texts]
        encoded = self.tokenizer.encode_batch(prepared)
        inputs = {
            "input_ids": np.asarray([row.ids for row in encoded], dtype=np.int64),
            "attention_mask": np.asarray(
                [row.attention_mask for row in encoded], dtype=np.int64
            ),
            "token_type_ids": np.asarray(
                [row.type_ids for row in encoded], dtype=np.int64
            ),
        }
        hidden = cast(np.ndarray, self.session.run(["last_hidden_state"], inputs)[0])
        mask = inputs["attention_mask"].astype(np.float32)[..., None]
        pooled = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1.0)
        pooled /= np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
        return pooled.astype(np.float32)

    def metadata(self) -> dict:
        return {
            "repository": self.config["repository"],
            "revision": self.config["revision"],
            "dimensions": self.config["dimensions"],
            "max_tokens": self.config["max_tokens"],
            "pooling": self.config["pooling"],
            "normalization": self.config["normalization"],
            "provider": "onnxruntime-CPU",
        }
