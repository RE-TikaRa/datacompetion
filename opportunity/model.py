import json
import os
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, SecretStr

from opportunity.files import ROOT


@dataclass
class ModelSettings:
    base_url: str
    model: str
    api_key: SecretStr = field(repr=False)
    auth_source: str = "environment"
    concurrency: int = 3
    input_price: float | None = None
    output_price: float | None = None

    @classmethod
    def load(cls, root: Path = ROOT) -> ModelSettings:
        load_dotenv(root / ".env", override=False)
        auth_source = os.getenv("MODEL_AUTH_SOURCE", "codex")
        base_url = os.getenv("MODEL_BASE_URL", "")
        model = os.getenv("MODEL_NAME", "")
        key = os.getenv("MODEL_API_KEY", "")
        if auth_source == "codex":
            home = Path(os.getenv("CODEX_HOME", str(Path.home() / ".codex")))
            config = tomllib.loads((home / "config.toml").read_text(encoding="utf-8"))
            provider = config.get("model_providers", {}).get(
                config.get("model_provider"), {}
            )
            if provider.get("wire_api", "responses") != "responses":
                raise ValueError("模型服务需要支持 Responses API。")
            base_url = base_url or provider.get("base_url", "https://api.openai.com/v1")
            model = model or config.get("model", "")
            env_key = provider.get("env_key")
            if env_key:
                key = key or os.getenv(env_key, "")
            else:
                auth = json.loads((home / "auth.json").read_text(encoding="utf-8"))
                key = key or auth.get("OPENAI_API_KEY", "")
        if not all([base_url, model, key]):
            raise ValueError(
                "模型配置不完整，请配置 MODEL_BASE_URL、MODEL_NAME 和 MODEL_API_KEY。"
            )
        input_price = os.getenv("MODEL_INPUT_PRICE_PER_MILLION", "")
        output_price = os.getenv("MODEL_OUTPUT_PRICE_PER_MILLION", "")
        return cls(
            base_url.rstrip("/"),
            model,
            SecretStr(key),
            auth_source,
            int(os.getenv("MODEL_CONCURRENCY", "3")),
            float(input_price) if input_price else None,
            float(output_price) if output_price else None,
        )

    def public(self) -> dict:
        return {
            "base_url": self.base_url,
            "model": self.model,
            "auth_source": self.auth_source,
            "concurrency": self.concurrency,
            "input_price_per_million": self.input_price,
            "output_price_per_million": self.output_price,
        }


class ModelClient:
    def __init__(self, settings: ModelSettings | None = None) -> None:
        self.settings = settings or ModelSettings.load()
        self.client = httpx.Client(
            base_url=self.settings.base_url + "/",
            headers={
                "Authorization": "Bearer " + self.settings.api_key.get_secret_value()
            },
            timeout=180,
        )

    def generate[T: BaseModel](
        self,
        instructions: str,
        content: str,
        schema: type[T],
        output_tokens: int = 8000,
    ) -> tuple[T, dict[str, Any]]:
        started = time.monotonic()
        response = self.client.post(
            "responses",
            json={
                "model": self.settings.model,
                "instructions": instructions,
                "input": content,
                "store": False,
                "max_output_tokens": output_tokens,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": schema.__name__,
                        "schema": schema.model_json_schema(),
                        "strict": True,
                    }
                },
            },
        )
        if not response.is_success:
            raise RuntimeError(f"模型请求失败，HTTP {response.status_code}。")
        result = response.json()
        if result.get("status") != "completed":
            raise RuntimeError(f"模型没有完成请求：{result.get('status')}。")
        output = "".join(
            piece["text"]
            for item in result.get("output", [])
            if item.get("type") == "message"
            for piece in item.get("content", [])
            if piece.get("type") == "output_text"
        )
        value = schema.model_validate_json(output)
        usage = result.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens_used = usage.get("output_tokens", 0)
        price_known = (
            self.settings.input_price is not None
            and self.settings.output_price is not None
        )
        return value, {
            "response_id": result.get("id"),
            "model": result.get("model"),
            "elapsed_seconds": time.monotonic() - started,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens_used,
            "cached_input_tokens": usage.get("input_tokens_details", {}).get(
                "cached_tokens", 0
            ),
            "cost": (
                input_tokens * self.settings.input_price
                + output_tokens_used * self.settings.output_price
            )
            / 1_000_000
            if price_known
            else None,
            "cost_basis": "configured_standard_token_prices"
            if price_known
            else "price_not_configured",
        }

    def close(self) -> None:
        self.client.close()
