# 模型运行与认证

## 文本模型

系统调用支持结构化 JSON 的 Responses API，用于从公开记录提取证据、判断机会、分类、主题命名及策划案生成。

本机默认读取现有 Codex 的模型、服务地址和认证。认证内容仅在请求时使用，不复制到项目文件，不进入运行报告。此模式需要 Codex 使用 API key 认证，并将服务接口配置为 `responses`。

其他运行环境可使用 `.env.example` 中的变量配置服务，设置 `MODEL_AUTH_SOURCE=environment`，并填写地址、模型和 API key。`.env` 已忽略，不应提交。

连接检查：

```powershell
uv run python scripts/check_model.py
```

该命令进行一次小型结构化请求，输出模型名、状态和 token 用量，不打印凭据。价格由 `MODEL_INPUT_PRICE_PER_MILLION`、`MODEL_OUTPUT_PRICE_PER_MILLION` 配置，单位须来自实际服务报价。没有配置报价时成本为未知，不能显示为免费。

`MODEL_CONCURRENCY` 控制并行请求数，默认 3。任务保存每次调用的用量、耗时及服务返回的模型标识，文本只来自用户选择的公开数据。

`MODEL_TIMEOUT_SECONDS` 默认 420 秒。长文本批次可能需要较长生成时间，超时批次会自动重试并保留其他已完成检查点。

## 多语言语义模型

`configs/embedding.json` 指定 `intfloat/multilingual-e5-small` 的固定版本、ONNX 文件、分词、池化和归一化方式。模型按 MIT 许可提供，原模型说明一并保存。

```powershell
uv run python scripts/download_model.py
```

模型下载到 `data/models/multilingual-e5-small`，不会进入 Git。下载命令拒绝覆盖现有文件。运行计算使用本地 ONNX Runtime，无需 GPU 和额外的向量 API。

## 环境

```powershell
uv sync --locked
ruff format
ruff check --fix
uv run pyright
uv run python -m pytest
```

项目使用 Python 3.14，依赖由 `pyproject.toml` 声明，精确解析结果由 `uv.lock` 保存。模型权重和认证独立于源代码管理。
