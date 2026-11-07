import json
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import cast

from pydantic import BaseModel, ConfigDict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.model import ModelClient


class Probe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ready: bool
    language: str


client = ModelClient()
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
result, usage = client.generate(
    "检测结构化输出能力。按给定模式返回 ready=true、language=中文，不调用工具。",
    "连接检查，不包含研究数据。",
    Probe,
    output_tokens=512,
)
print(json.dumps({"result": result.model_dump(), "usage": usage}, ensure_ascii=False))
client.close()
