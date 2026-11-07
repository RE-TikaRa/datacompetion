import argparse
import json

from opportunity.cleaning import clean_batch
from opportunity.collection import collect_batch
from opportunity.files import ROOT, new_run, read_json

parser = argparse.ArgumentParser(description="AI 应用机会分析系统")
commands = parser.add_subparsers(dest="command", required=True)
clean = commands.add_parser("clean", help="从采集快照清洗并导出 result1")
clean.add_argument("--batch", required=True)
collect = commands.add_parser("collect", help="按需求采集独立批次")
collect.add_argument("--batch", required=True)
collect.add_argument("--direction")
collect.add_argument("--keywords", nargs="+")
args = parser.parse_args()
if args.command == "clean":
    output = new_run(args.batch)
    report = clean_batch(args.batch, output)
    print(json.dumps({"output": str(output), **report}, ensure_ascii=False, indent=2))
else:
    config = read_json(ROOT / "configs/collection.json")
    if args.direction:
        config["direction"] = args.direction
    if args.keywords:
        config["keywords"] = args.keywords
    collect_batch(args.batch, config)
