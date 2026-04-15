#!/usr/bin/env python3

import json

# 读取投资策略JSON文件
with open('报告/2026-03-27/投资策略.json', 'r', encoding='utf-8') as f:
    strategy = json.load(f)

# 读取投资建议报告
with open('报告/2026-03-27/2026-03-27_DeepSeek-V3.1_投资建议.md', 'r', encoding='utf-8') as f:
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
for i, name in enumerate(fund_names, 1):
    print(f"{i:2d}. {name}")

print("\n检查匹配情况:")
missing = []
for name in fund_names:
    if name not in report_text and name.replace(' ', '') not in report_text.replace(' ', ''):
        missing.append(name)
        print(f"❌ 缺失: {name}")
    else:
        print(f"✅ 存在: {name}")

print(f"\n总共缺失 {len(missing)} 个基金名称")
if missing:
    print("缺失的基金名称:")
    for name in missing:
        print(f"- {name}")