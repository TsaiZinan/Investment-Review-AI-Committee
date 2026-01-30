#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate investment brief from JSON using the prompt instructions
"""

import json
from pathlib import Path

def load_investment_strategy(json_path):
    """Load the investment strategy JSON file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_investment_brief(strategy_data):
    """Generate investment brief markdown based on the prompt instructions"""
    
    # Extract data from JSON
    allocation_summary = strategy_data.get('allocation_summary', [])
    investment_plan = strategy_data.get('investment_plan', [])
    non_investment_holdings = strategy_data.get('non_investment_holdings', [])
    
    # Start building the markdown content
    md_content = []
    md_content.append("# 投资策略（由 JSON 转换）")
    md_content.append("来源：[投资策略.json](file:///Users/cai/SynologyDrive/Project/#ProjectLife-000000-理财/报告/2026-01-30/投资策略.json)")
    md_content.append("")  # Empty line
    
    # Section 1: Configuration Overview
    md_content.append("### 1. 配置概览")
    total_ratio = sum(item['ratio'] for item in allocation_summary)
    plan_categories = list(set(item['category'] for item in investment_plan))
    non_investment_categories = list(set(item['category'] for item in non_investment_holdings)) if non_investment_holdings else []
    
    md_content.append(f"- 资产大类目标比例合计：{total_ratio*100:.2f}%（按 allocation_summary[].ratio 求和）")
    md_content.append(f"- 定投计划覆盖大类：{' / '.join(plan_categories)}")
    md_content.append(f"- 额外持仓（不纳入定投计划）：{' / '.join(non_investment_categories) if non_investment_categories else '无'}")
    
    # Find weekly targets
    weekly_targets = []
    for item in allocation_summary:
        if item.get('weekly_amount_target') is not None:
            weekly_targets.append(f"{item['category']}为 {item['weekly_amount_target']}/周")
        else:
            weekly_targets.append(f"{item['category']}为空")
    
    md_content.append(f"- 已填写的周定投目标：{'；'.join(weekly_targets)}")
    md_content.append("")
    
    # Section 2: Category Target Allocation
    md_content.append("### 2. 大类目标配置（allocation_summary）")
    md_content.append("| 大类 | 目标比例 | 周定投目标（元/周） |")
    md_content.append("|---|---:|---:|")
    
    for item in allocation_summary:
        ratio_pct = item['ratio'] * 100
        weekly_target = item.get('weekly_amount_target')
        weekly_str = f"{weekly_target}" if weekly_target is not None else ""
        md_content.append(f"| {item['category']} | {ratio_pct:.2f}% | {weekly_str} |")
    md_content.append("")
    
    # Section 3: Investment Plan
    md_content.append("### 3. 定投计划（investment_plan）")
    md_content.append("- \"大类内占比\"指 `ratio_in_category`")
    md_content.append("- \"全组合目标占比（推导）\" = 大类目标比例 × 大类内占比")
    md_content.append("- \"当前持有\"来自 `current_holding`")
    md_content.append("")
    
    # Group investment_plan by category
    categories_order = {item['category']: idx for idx, item in enumerate(allocation_summary)}
    plan_by_category = {}
    for item in investment_plan:
        cat = item['category']
        if cat not in plan_by_category:
            plan_by_category[cat] = []
        plan_by_category[cat].append(item)
    
    # Sort categories by order in allocation_summary, then others
    sorted_categories = sorted(plan_by_category.keys(), key=lambda x: categories_order.get(x, float('inf')))
    
    for idx, category in enumerate(sorted_categories, 1):
        # Get target ratio for this category
        cat_target_ratio = 0
        for alloc_item in allocation_summary:
            if alloc_item['category'] == category:
                cat_target_ratio = alloc_item['ratio']
                break
        
        cat_target_pct = cat_target_ratio * 100
        md_content.append(f"#### 3.{idx} {category}（目标 {cat_target_pct:.2f}%）")
        
        md_content.append("| 子类 | 标的 | 基金代码 | 大类内占比 | 全组合目标占比（推导） | 定投日 | 长期 | 中期 | 短期 | 当前持有 |")
        md_content.append("|---|---|---|---:|---:|---|---|---|---|---:|")
        
        total_holding = 0
        for plan_item in plan_by_category[category]:
            sub_category = plan_item['sub_category']
            fund_name = plan_item['fund_name']
            fund_code = plan_item.get('fund_code', '')
            fund_code_str = fund_code if fund_code else ""
            
            ratio_in_cat_pct = plan_item['ratio_in_category'] * 100
            combined_ratio = cat_target_ratio * plan_item['ratio_in_category']
            combined_ratio_pct = combined_ratio * 100
            
            day_of_week = plan_item.get('day_of_week', '')
            long_term = plan_item.get('long_term_assessment', '')
            mid_term = plan_item.get('mid_term_assessment', '')
            short_term = plan_item.get('short_term_assessment', '')
            current_holding = plan_item.get('current_holding', 0)
            if current_holding is None:
                current_holding = 0
            total_holding += current_holding
            
            md_content.append(f"| {sub_category} | {fund_name} | {fund_code_str} | {ratio_in_cat_pct:.2f}% | {combined_ratio_pct:.2f}% | {day_of_week} | {long_term} | {mid_term} | {short_term} | {current_holding:.2f} |")
        
        md_content.append(f"小计（{category}）当前持有：{total_holding:.2f}")
        md_content.append("")
    
    # Section 3.5: Investment Plan Holdings Total
    md_content.append("### 3.5 定投计划持仓合计")
    total_investment_holding = sum(
        item.get('current_holding', 0) or 0 for item in investment_plan
    )
    
    # Calculate holdings by category
    holdings_by_category = {}
    for item in investment_plan:
        cat = item['category']
        holding = item.get('current_holding', 0) or 0
        if cat not in holdings_by_category:
            holdings_by_category[cat] = 0
        holdings_by_category[cat] += holding
    
    category_holding_strs = [f"{cat} {holding:.2f}" for cat, holding in holdings_by_category.items()]
    
    md_content.append(f"- 定投计划当前持有合计：{total_investment_holding:.2f}")
    md_content.append(f"- 其中：{' / '.join(category_holding_strs)}")
    md_content.append("")
    
    # Section 4: Non-Investment Holdings
    md_content.append("### 4. 非定投持仓（non_investment_holdings）")
    md_content.append("| 大类 | 子类 | 标的 | 当前持有 |")
    md_content.append("|---|---|---|---:|")
    
    total_non_investment_holding = 0
    for item in non_investment_holdings:
        category = item['category']
        sub_category = item.get('sub_category', '')
        fund_name = item['fund_name']
        current_holding = item.get('current_holding', 0) or 0
        total_non_investment_holding += current_holding
        md_content.append(f"| {category} | {sub_category} | {fund_name} | {current_holding:.2f} |")
    
    md_content.append(f"小计（非定投）当前持有：{total_non_investment_holding:.2f}")
    md_content.append("")
    
    # Section 5: Portfolio Status and Deviation
    total_all_holdings = total_investment_holding + total_non_investment_holding
    md_content.append("### 5. 组合现状与偏离（按\"全部持仓\"口径）")
    md_content.append(f"全部持仓（定投计划 + 非定投）合计：{total_all_holdings:.2f}")
    md_content.append("")
    
    md_content.append("| 大类 | 目标比例 | 目标金额（按 {total_all_holdings:.2f} 推算） | 当前金额 | 偏离（当前-目标） | 当前占比 |".replace("{total_all_holdings:.2f}", f"{total_all_holdings:.2f}"))
    md_content.append("|---|---:|---:|---:|---:|---:|")
    
    # Calculate holdings by category for all investments
    all_holdings_by_category = {}
    for item in investment_plan:
        cat = item['category']
        holding = item.get('current_holding', 0) or 0
        if cat not in all_holdings_by_category:
            all_holdings_by_category[cat] = 0
        all_holdings_by_category[cat] += holding
    
    for item in non_investment_holdings:
        cat = item['category']
        holding = item.get('current_holding', 0) or 0
        if cat not in all_holdings_by_category:
            all_holdings_by_category[cat] = 0
        all_holdings_by_category[cat] += holding
    
    # Print each category row
    for alloc_item in allocation_summary:
        cat = alloc_item['category']
        target_ratio = alloc_item['ratio']
        target_ratio_pct = target_ratio * 100
        target_amount = total_all_holdings * target_ratio
        current_amount = all_holdings_by_category.get(cat, 0)
        deviation = current_amount - target_amount
        current_pct = (current_amount / total_all_holdings) * 100 if total_all_holdings > 0 else 0
        md_content.append(f"| {cat} | {target_ratio_pct:.2f}% | {target_amount:.2f} | {current_amount:.2f} | {deviation:.2f} | {current_pct:.2f}% |")
    
    # Handle categories in holdings but not in allocation summary
    for cat in all_holdings_by_category:
        if not any(item['category'] == cat for item in allocation_summary):
            current_amount = all_holdings_by_category[cat]
            current_pct = (current_amount / total_all_holdings) * 100 if total_all_holdings > 0 else 0
            md_content.append(f"| {cat} | 0%（未设目标） |  | {current_amount:.2f} |  | {current_pct:.2f}% |")
    
    md_content.append("")
    
    # Interpretation Points
    md_content.append("#### 解读要点")
    # Identify significant over/under allocations
    for alloc_item in allocation_summary:
        cat = alloc_item['category']
        target_ratio = alloc_item['ratio']
        target_amount = total_all_holdings * target_ratio
        current_amount = all_holdings_by_category.get(cat, 0)
        deviation = current_amount - target_amount
        deviation_pct = abs((deviation / total_all_holdings) * 100) if total_all_holdings > 0 else 0
        
        if deviation_pct > 5:  # Significant deviation (>5% of total portfolio)
            direction = "高配" if deviation > 0 else "低配"
            md_content.append(f"- {cat}：{direction}{abs(deviation):.2f}元（偏离{deviation_pct:.2f}%）")
    
    if abs(total_ratio - 1.0) > 0.01:  # More than 1% away from 100%
        md_content.append(f"- 目标比例合计为{total_ratio*100:.2f}%，非100%")
    
    # Check for categories in holdings but not in allocation summary
    for cat in all_holdings_by_category:
        if not any(item['category'] == cat for item in allocation_summary):
            md_content.append(f"- {cat}：未设目标比例，当前持仓{all_holdings_by_category[cat]:.2f}元")
    
    md_content.append("")
    
    # Section 6: Weekly Investment Implementation
    md_content.append("### 6. 周定投落地（已给定的信息可直接推导）")
    
    # Find categories with weekly targets
    weekly_target_categories = [item for item in allocation_summary if item.get('weekly_amount_target') is not None]
    
    if not weekly_target_categories:
        md_content.append("目前未设置任何大类的周定投目标。")
    else:
        for alloc_item in weekly_target_categories:
            cat = alloc_item['category']
            weekly_target = alloc_item['weekly_amount_target']
            md_content.append(f"目前仅设置\"{cat} {weekly_target}/周\"。按大类内占比拆分：")
            
            # Get all investment plans for this category
            cat_plans = [plan for plan in investment_plan if plan['category'] == cat]
            for plan_item in cat_plans:
                # Check if plan has its own weekly_amount
                if plan_item.get('weekly_amount') is not None:
                    weekly_amount = plan_item['weekly_amount']
                    md_content.append(f"  - {plan_item['fund_name']}：{weekly_amount}/周（{plan_item.get('day_of_week', '')}）（来自 weekly_amount）")
                else:
                    weekly_amount = weekly_target * plan_item['ratio_in_category']
                    md_content.append(f"  - {plan_item['fund_name']}：{weekly_amount:.2f}/周（{plan_item.get('day_of_week', '')}）")
            md_content.append("")
    
    return "\n".join(md_content)

def main():
    # Load the investment strategy JSON
    json_path = Path("报告/2026-01-30/投资策略.json")
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        return
    
    strategy_data = load_investment_strategy(json_path)
    
    # Generate the brief
    brief_content = generate_investment_brief(strategy_data)
    
    # Save to the brief directory
    output_path = Path("报告/2026-01-30/简报/投资简报_Qwen-3-Coder.md")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(brief_content)
    
    print(f"Generated investment brief at {output_path}")

if __name__ == "__main__":
    main()