import argparse
import json
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import cast

from opportunity.cleaning import clean_batch
from opportunity.collection import collect_batch
from opportunity.files import ROOT, new_run, read_json
from opportunity.judging import judge_batch

cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
parser = argparse.ArgumentParser(description="AI 应用机会分析系统")
commands = parser.add_subparsers(dest="command", required=True)
clean = commands.add_parser("clean", help="从采集快照清洗并导出 result1")
clean.add_argument("--batch", required=True)
collect = commands.add_parser("collect", help="按需求采集独立批次")
collect.add_argument("--batch", required=True)
collect.add_argument("--direction")
collect.add_argument("--keywords", nargs="+")
judge = commands.add_parser("judge", help="判别机会并生成 result2")
judge.add_argument("--run", required=True, type=Path)
judge.add_argument("--batch-size", type=int, default=8)
judge.add_argument("--limit", type=int)
judge.add_argument("--resume", type=Path)
args = parser.parse_args()
if args.command == "clean":
    output = new_run(args.batch)
    report = clean_batch(args.batch, output)
    print(json.dumps({"output": str(output), **report}, ensure_ascii=False, indent=2))
elif args.command == "judge":
    output = judge_batch(
        args.run.resolve(),
        batch_size=args.batch_size,
        limit=args.limit,
        resume=args.resume,
    )
    print(json.dumps({"output": output.as_posix()}, ensure_ascii=False))
else:
    config = read_json(ROOT / "configs/collection.json")
    if args.direction:
        config["direction"] = args.direction
    if args.keywords:
        config["keywords"] = args.keywords
    collect_batch(args.batch, config)
