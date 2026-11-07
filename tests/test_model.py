import json

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, SecretStr

from opportunity.model import ModelClient, ModelSettings


class Result(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ready: bool


def test_codex_configuration_reads_key_without_copying(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.delenv("MODEL_BASE_URL", raising=False)
    (tmp_path / "config.toml").write_text(
        'model="local-model"\nmodel_provider="local"\n'
        '[model_providers.local]\nbase_url="https://example.test/v1"\n'
        'wire_api="responses"\n',
        encoding="utf-8",
    )
    (tmp_path / "auth.json").write_text(
        json.dumps({"OPENAI_API_KEY": "test-secret"}), encoding="utf-8"
    )
    settings = ModelSettings.load(tmp_path)
    assert settings.model == "local-model"
    assert settings.api_key.get_secret_value() == "test-secret"
    assert "test-secret" not in repr(settings)
    assert "test-secret" not in json.dumps(settings.public())
    assert settings.public()["base_url"] == "https://example.test/v1"
    assert not (tmp_path / ".env").exists()


def test_responses_schema_and_usage(monkeypatch):
    settings = ModelSettings(
        "https://example.test/v1",
        "local-model",
        SecretStr("test-secret"),
        input_price=2,
        output_price=4,
    )

    def post(client, url, *, json):
        assert url == "responses"
        assert json["store"] is False
        assert json["text"]["format"]["strict"] is True
        assert json["text"]["format"]["schema"]["additionalProperties"] is False
        return httpx.Response(
            200,
            json={
                "id": "response-test",
                "status": "completed",
                "model": "local-model",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"ready":true}'}],
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 25},
            },
        )

    monkeypatch.setattr(httpx.Client, "post", post)
    client = ModelClient(settings)
    result, usage = client.generate("instructions", "content", Result)
    client.close()
    assert result.ready
    assert usage["input_tokens"] == 100
    assert usage["cost"] == pytest.approx(0.0003)


def test_http_failure_does_not_expose_response_secrets(monkeypatch):
    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda *args, **kwargs: httpx.Response(401, text="test-secret"),
    )
    client = ModelClient(
        ModelSettings(
            "https://example.test/v1", "local-model", SecretStr("test-secret")
        )
    )
    with pytest.raises(RuntimeError, match="HTTP 401") as error:
        client.generate("instructions", "content", Result)
    client.close()
    assert "test-secret" not in str(error.value)
