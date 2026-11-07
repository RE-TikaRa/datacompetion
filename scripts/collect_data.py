import argparse
import sys
from datetime import date
from io import TextIOWrapper
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opportunity.collection import collect_batch
from opportunity.files import ROOT, read_json

parser = argparse.ArgumentParser(description="采集独立批次的公开 AI 应用相关内容。")
parser.add_argument("--batch", required=True)
parser.add_argument("--reference-date", type=date.fromisoformat)
parser.add_argument("--direction")
parser.add_argument("--keywords", nargs="+")
args = parser.parse_args()
cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
config = read_json(ROOT / "configs/collection.json")
if args.direction:
    config["direction"] = args.direction
if args.keywords:
    config["keywords"] = args.keywords
collect_batch(args.batch, config, args.reference_date)
