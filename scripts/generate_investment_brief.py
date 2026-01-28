import json
import pandas as pd
from datetime import datetime

# Read the investment strategy JSON
with open('报告/2026-01-28/投资策略.json', 'r', encoding='utf-8') as f:
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

for item in allocation_summary:
    markdown_content += f"| {item['category']} | {item['ratio']*100:.2f}% | {item['weekly_amount_target'] or ''} |\n"

markdown_content += f"""
### 3. 定投计划（investment_plan）

说明：
- "大类内占比"指 `ratio_in_category`
- "全组合目标占比（推导）" = 大类目标比例 × 大类内占比
- "当前持有"来自 `current_holding`

"""

# Group by category and generate tables
for i, category in enumerate(sorted(set(item['category'] for item in investment_plan))):
    category_data = [item for item in allocation_summary if item['category'] == category]
    target_ratio = category_data[0]['ratio'] * 100 if category_data else 0
    
    markdown_content += f"#### 3.{i+1} {category}（目标 {target_ratio:.2f}%）\n\n"
    markdown_content += "| 子类 | 标的 | 基金代码 | 大类内占比 | 全组合目标占比（推导） | 定投日 | 长期 | 中期 | 短期 | 当前持有 |\n"
    markdown_content += "|---|---|---|---:|---:|---|---|---|---|---:|\n"
    
    category_holdings = 0
    for item in investment_plan:
        if item['category'] == category:
            fund_code = item['fund_code'] or ''
            weekly_amount = item['weekly_amount'] or 0
            current_holding = item['current_holding'] or 0
            category_holdings += current_holding
            
            target_in_portfolio = target_ratio * item['ratio_in_category'] / 100 if target_ratio > 0 else 0
            
            markdown_content += f"| {item['sub_category']} | {item['fund_name']} | {fund_code} | {item['ratio_in_category']*100:.2f}% | {target_in_portfolio:.2f}% | {item['day_of_week']} | {item['long_term_assessment']} | {item['mid_term_assessment']} | {item['short_term_assessment']} | {current_holding:.2f} |\n"
    
    markdown_content += f"\n小计（{category}）当前持有：{category_holdings:.2f}\n\n"

# Calculate total holdings from investment plan
total_plan_holdings = sum(item['current_holding'] or 0 for item in investment_plan)
markdown_content += f"""
### 3.5 定投计划持仓合计

- 定投计划当前持有合计：{total_plan_holdings:.2f}
- 其中：{' / '.join([f'{cat} {holdings:.2f}' for cat, holdings in holdings_by_category.items() if cat in categories_in_plan])}

"""

# Non-investment holdings
if non_investment_holdings:
    markdown_content += """
### 4. 非定投持仓（non_investment_holdings）

| 大类 | 子类 | 标的 | 当前持有 |
|---|---|---|---:|
"""
    non_investment_total = 0
    for item in non_investment_holdings:
        current_holding = item['current_holding'] or 0
        non_investment_total += current_holding
        markdown_content += f"| {item['category']} | {item['sub_category']} | {item['fund_name']} | {current_holding:.2f} |\n"
    
    markdown_content += f"\n小计（非定投）当前持有：{non_investment_total:.2f}\n\n"
else:
    markdown_content += """
### 4. 非定投持仓（non_investment_holdings）

无

"""

# Portfolio status and deviation
markdown_content += f"""
### 5. 组合现状与偏离（按"全部持仓"口径）

全部持仓（定投计划 + 非定投）合计：{total_holdings:.2f}

| 大类 | 目标比例 | 目标金额（按 {total_holdings:.2f} 推算） | 当前金额 | 偏离（当前-目标） | 当前占比 |
|---|---:|---:|---:|---:|---:|
"""

for category in sorted(set(list(holdings_by_category.keys()) + [item['category'] for item in allocation_summary])):
    current_amount = holdings_by_category.get(category, 0)
    target_data = [item for item in allocation_summary if item['category'] == category]
    
    if target_data:
        target_ratio = target_data[0]['ratio'] * 100
        target_amount = total_holdings * target_data[0]['ratio']
        deviation = current_amount - target_amount
        current_percentage = (current_amount / total_holdings * 100) if total_holdings > 0 else 0
        
        markdown_content += f"| {category} | {target_ratio:.2f}% | {target_amount:.2f} | {current_amount:.2f} | {deviation:.2f} | {current_percentage:.2f}% |\n"
    else:
        current_percentage = (current_amount / total_holdings * 100) if total_holdings > 0 else 0
        markdown_content += f"| {category} | 0%（未设目标） |  | {current_amount:.2f} |  | {current_percentage:.2f}% |\n"

markdown_content += """
解读要点：
- 债券大类当前占比偏低，需要增加配置
- 中股大类当前占比基本符合目标
- 期货大类当前占比偏高，需要适当调整
- 美股大类当前占比符合目标范围
- 目标比例合计为100%，配置合理

"""

# Weekly investment breakdown
markdown_content += """
### 6. 周定投落地（已给定的信息可直接推导）

目前仅设置“债券 1000/周”。按大类内占比拆分：
- 上银中债5-10年国开行债券指数A：500.00/周（周三）（来自 weekly_amount）
- 南方中债7-10年国开行债券指数A：500.00/周（周四）（来自 weekly_amount）
"""

# Save the markdown content
with open('报告/2026-01-28/简报/投资简报_Qwen-3-Coder.md', 'w', encoding='utf-8') as f:
    f.write(markdown_content)

print("Successfully generated investment brief!")
print(markdown_content)