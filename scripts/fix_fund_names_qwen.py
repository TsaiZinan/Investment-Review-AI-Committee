#!/usr/bin/env python3
import json
import re

TODAY = "2026-03-16"
ROOT_DIR = "/Users/cai/SynologyDrive/Project/#ProjectLife-000000-理财"
JSON_FILE = f"{ROOT_DIR}/报告/{TODAY}/投资策略.json"
REPORT_FILE = f"{ROOT_DIR}/报告/{TODAY}/2026-03-16_Qwen3.5-Plus_投资建议.md"

# Load fund names from JSON
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    strategy = json.load(f)

fund_names = []
for x in strategy.get("investment_plan", []) or []:
    n = (x.get("fund_name") or "").strip()
    if n:
        fund_names.append(n)
for x in strategy.get("non_investment_holdings", []) or []:
    n = (x.get("fund_name") or "").strip()
    if n:
        fund_names.append(n)

# Read report
with open(REPORT_FILE, 'r', encoding='utf-8') as f:
    report = f.read()

# Replace fund names (remove spaces)
for fund_name in fund_names:
    # Create pattern with spaces between each character
    # E.g., "上银中债 5-10 年国开行债券指数 A" -> "上 银 中 债  5 - 1 0  年 国 开 行 债 券 指 数  A"
    spaced_name = ' '.join(fund_name)
    if spaced_name in report:
        report = report.replace(spaced_name, fund_name)
        print(f'Fixed: "{spaced_name}" -> "{fund_name}"')

# Write back
with open(REPORT_FILE, 'w', encoding='utf-8') as f:
    f.write(report)

print(f'\nFixed all fund names in report!')
