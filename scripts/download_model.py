import json
import shutil
import sys
import urllib.request
from datetime import UTC, datetime
from io import TextIOWrapper
from pathlib import Path
from typing import cast

root = Path(__file__).resolve().parents[1]
config = json.loads((root / "configs/embedding.json").read_text(encoding="utf-8"))
folder = root / "data/models/multilingual-e5-small"
folder.mkdir(parents=True)
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
downloads = []
for filename in [
    config["model_file"],
    config["tokenizer_file"],
    "config.json",
    "README.md",
]:
    target = folder / filename
    if target.exists():
        raise FileExistsError(f"目标文件已经存在：{target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    url = (
        f"https://huggingface.co/{config['repository']}/resolve/"
        f"{config['revision']}/{filename}"
    )
    with (
        urllib.request.urlopen(url, timeout=120) as response,
        target.open("xb") as stream,
    ):
        shutil.copyfileobj(response, stream)
    downloads.append({"file": filename, "bytes": target.stat().st_size, "url": url})
    print(f"已下载 {filename}: {target.stat().st_size:,} 字节", flush=True)
with (folder / "manifest.json").open("x", encoding="utf-8") as stream:
    json.dump(
        {
            **config,
            "downloaded_at": datetime.now(UTC).isoformat(),
            "downloads": downloads,
        },
        stream,
        ensure_ascii=False,
        indent=2,
    )
