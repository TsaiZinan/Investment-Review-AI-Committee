#!/usr/bin/env python3

import json
import os

# 读取投资策略JSON
json_path = "/Users/cai/SynologyDrive/Project/#ProjectLife-000000-理财/报告/2026-03-16/投资策略.json"
with open(json_path, 'r', encoding='utf-8') as f:
    strategy = json.load(f)

# 读取投资建议报告
report_path = "/Users/cai/SynologyDrive/Project/#ProjectLife-000000-理财/报告/2026-03-16/2026-03-16_DeepSeek-V3.1_投资建议.md"
with open(report_path, 'r', encoding='utf-8') as f:
    report_text = f.read()

# 提取所有基金名称
fund_names = []
for x in strategy.get("investment_plan", []) or []:
    n = (x.get("fund_name") or "").strip()
    if n:
        fund_names.append(n)
for x in strategy.get("non_investment_holdings", []) or []:
    n = (x.get("fund_name") or "").strip()
    if n:
        fund_names.append(n)

print("所有基金名称:")
for name in fund_names:
    print(f"- {name}")

print("\n缺失的基金名称:")
missing = []
for name in fund_names:
    if name not in report_text:
        missing.append(name)
        print(f"- {name}")

print(f"\n总共 {len(fund_names)} 个基金，缺失 {len(missing)} 个")