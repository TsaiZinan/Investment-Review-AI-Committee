import json
import pandas as pd
from datetime import datetime

# Get today's date
today = datetime.now().strftime("%Y-%m-%d")

# Read the investment strategy JSON
with open(f'报告/{today}/投资策略.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

allocation_summary = data['allocation_summary']
investment_plan = data['investment_plan']
non_investment_holdings = data['non_investment_holdings']

# Calculate totals and summaries
total_ratio = sum(item['ratio'] for item in allocation_summary)
categories_in_plan = list(set(item['category'] for item in investment_plan))
categories_in_holdings = list(set(item['category'] for item in non_investment_holdings))

# Calculate current holdings by category
holdings_by_category = {}
for item in investment_plan:
    category = item['category']
    if category not in holdings_by_category:
        holdings_by_category[category] = 0
    if item['current_holding'] is not None:
        holdings_by_category[category] += item['current_holding']

for item in non_investment_holdings:
    category = item['category']
    if category not in holdings_by_category:
        holdings_by_category[category] = 0
    if item['current_holding'] is not None:
        holdings_by_category[category] += item['current_holding']

total_holdings = sum(holdings_by_category.values())

# Generate the markdown content
markdown_content = f"""# 投资策略（由 JSON 转换）

来源：[投资策略.json](file:///Users/cai/SynologyDrive/Project/%23ProjectLife-000000-%E7%90%86%E8%B4%A2/%E6%8A%95%E8%B5%84%E7%AD%96%E7%95%A5.json)

### 1. 配置概览
- 资产大类目标比例合计：{total_ratio*100:.2f}%（按 allocation_summary[].ratio 求和）
- 定投计划覆盖大类：{' / '.join(sorted(categories_in_plan))}
- 额外持仓（不纳入定投计划）：{'无' if not categories_in_holdings else ' / '.join(sorted(categories_in_holdings))}
- 已填写的周定投目标：{'债券为 1000/周' if any(item['category'] == '债券' and item['weekly_amount_target'] == 1000 for item in allocation_summary) else '未填写'}

### 2. 大类目标配置（allocation_summary）

| 大类 | 目标比例 | 周定投目标（元/周） |
|---|---:|---:|
"""

# Add allocation summary table
for item in allocation_summary:
    category = item['category']
    ratio = item['ratio']
    weekly_target = item['weekly_amount_target'] or ''
    markdown_content += f"| {category} | {ratio*100:.2f}% | {weekly_target} |\n"

markdown_content += f"""
### 3. 当前持仓概览（按大类）

| 大类 | 当前持仓（元） | 占比 |
|---|---:|---:|
"""

# Add current holdings table
for category, amount in holdings_by_category.items():
    percentage = (amount / total_holdings * 100) if total_holdings > 0 else 0
    markdown_content += f"| {category} | {amount:.2f} | {percentage:.2f}% |\n"

markdown_content += f"| **总计** | **{total_holdings:.2f}** | **100.00%** |\n"

markdown_content += """
### 4. 定投计划详情（investment_plan）

| 大类 | 小类 | 基金代码 | 基金名称 | 周定投额 | 定投日 | 长期评估 | 中期评估 | 短期评估 | 当前持仓 |
|---|---|---|---|---|---|---|---|---|---|
"""

# Add investment plan table
for item in investment_plan:
    category = item['category']
    sub_category = item['sub_category']
    fund_code = item['fund_code'] or ''
    fund_name = item['fund_name']
    weekly_amount = item['weekly_amount'] or ''
    day_of_week = item['day_of_week'] or ''
    long_term = item['long_term_assessment'] or ''
    mid_term = item['mid_term_assessment'] or ''
    short_term = item['short_term_assessment'] or ''
    current_holding = item['current_holding'] or ''
    
    markdown_content += f"| {category} | {sub_category} | {fund_code} | {fund_name} | {weekly_amount} | {day_of_week} | {long_term} | {mid_term} | {short_term} | {current_holding} |\n"

markdown_content += """
### 5. 非定投持仓（non_investment_holdings）

"""

if non_investment_holdings:
    markdown_content += """| 大类 | 小类 | 基金代码 | 基金名称 | 当前持仓 |
|---|---|---|---|---|
"""
    for item in non_investment_holdings:
        category = item['category']
        sub_category = item.get('sub_category', '') or ''
        fund_code = item.get('fund_code', '') or ''
        fund_name = item.get('fund_name', '') or ''
        current_holding = item.get('current_holding', '') or ''
        markdown_content += f"| {category} | {sub_category} | {fund_code} | {fund_name} | {current_holding} |\n"
else:
    markdown_content += "无\n"

markdown_content += f"""
---

*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

# Save the brief to file
brief_file = f'报告/{today}/简报/投资简报_DeepSeek-V3.1.md'
with open(brief_file, 'w', encoding='utf-8') as f:
    f.write(markdown_content)

print(f"投资简报已生成: {brief_file}")
print("="*50)
print(markdown_content)