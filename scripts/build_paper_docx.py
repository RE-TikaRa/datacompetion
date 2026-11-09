import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPAIR = ROOT / "scripts" / "repair_docx_surface.py"


def expand_inputs(path: Path, seen: set[Path] | None = None) -> str:
    seen = set() if seen is None else seen
    path = path.resolve()
    if path in seen:
        raise ValueError(f"重复或循环引用：{path}")
    seen.add(path)
    text = path.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        include = match.group(1).strip()
        target = (path.parent / include).with_suffix(".tex")
        if not target.exists():
            raise FileNotFoundError(target)
        return expand_inputs(target, seen.copy())

    return re.sub(r"\\input\{([^}]+)\}", replace, text)


def prepare_docx_tex(source: Path, workdir: Path) -> Path:
    text = expand_inputs(source)
    text = re.sub(
        r"(\\includegraphics(?:\[[^]]*\])?\{[^}]*?)\.pdf(\})",
        r"\1.png\2",
        text,
    )
    text = text.replace("{../figures/", "{figures/")
    figures = workdir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    for image in (ROOT / "paper" / "figures").glob("*.png"):
        shutil.copy2(image, figures / image.name)
    flat = workdir / "main.tex"
    flat.write_text(text, encoding="utf-8")
    return flat


def build(source: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(output)
    temp_root = Path(tempfile.mkdtemp(prefix="datacompetition-paper-", dir="C:/Tmp"))
    flat_tex = prepare_docx_tex(source, temp_root)
    raw_docx = temp_root / "raw.docx"
    subprocess.run(
        [
            "pandoc",
            str(flat_tex),
            "--from=latex",
            "--to=docx",
            "--resource-path",
            f"{temp_root};{source.parent}",
            "--output",
            str(raw_docx),
        ],
        check=True,
        cwd=temp_root,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, str(REPAIR), str(raw_docx), str(output)],
        check=True,
        cwd=ROOT,
    )
    print(f"DOCX staging files retained at {temp_root}")


parser = argparse.ArgumentParser(description="从论文 TeX 源生成可编辑 Word 文档。")
parser.add_argument("--source", type=Path, default=ROOT / "paper/manuscript/main.tex")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
build(args.source, args.output)
print(args.output.resolve())
