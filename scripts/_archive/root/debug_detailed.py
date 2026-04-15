#!/usr/bin/env python3

import json
from pathlib import Path

# Read the investment strategy JSON
strategy_path = Path("报告/2026-04-15/投资策略.json")
with open(strategy_path, 'r', encoding='utf-8') as f:
    strategy = json.load(f)

# Collect all fund names from both investment_plan and non_investment_holdings
fund_names = []

# From investment_plan
for item in strategy.get('investment_plan', []):
    if 'fund_name' in item and item['fund_name']:
        fund_names.append(item['fund_name'])

# From non_investment_holdings  
for item in strategy.get('non_investment_holdings', []):
    if 'fund_name' in item and item['fund_name']:
        fund_names.append(item['fund_name'])

print(f"Total funds to check: {len(fund_names)}")

# Read the report
report_path = Path("报告/2026-04-15/2026-04-15_DeepSeek-V3.1_投资建议.md")
with open(report_path, 'r', encoding='utf-8') as f:
    report_text = f.read()

report_text_no_spaces = report_text.replace(' ', '')

print("\nDetailed fund name matching:")
missing_funds = []
for name in fund_names:
    exact_match = name in report_text
    no_spaces_match = name.replace(' ', '') in report_text_no_spaces
    
    print(f"基金: {name}")
    print(f"  精确匹配: {exact_match}")
    print(f"  无空格匹配: {no_spaces_match}")
    
    if not exact_match and not no_spaces_match:
        missing_funds.append(name)
        print(f"  ❌ 缺失")
    else:
        print(f"  ✅ 存在")
    print()

print(f"\nMissing funds: {len(missing_funds)}")
for name in missing_funds:
    print(f"  - {name}")
    
print(f"\nReport length: {len(report_text)} characters")
print(f"Report without spaces length: {len(report_text_no_spaces)} characters")