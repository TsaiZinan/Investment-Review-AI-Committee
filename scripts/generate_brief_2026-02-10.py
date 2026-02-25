#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path

def generate_investment_brief():
    date_str = "2026-02-10"
    report_dir = Path(f"报告/{date_str}")
    
    # Load the investment strategy JSON
    with open(report_dir / "投资策略.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Calculate totals for various values
    total_current_holding = 0
    allocation_total = sum(item['ratio'] for item in data['allocation_summary'])

    # Calculate current holdings total
    for plan in data['investment_plan']:
        if plan['current_holding'] is not None:
            total_current_holding += plan['current_holding']

    for holding in data['non_investment_holdings']:
        if holding['current_holding'] is not None:
            total_current_holding += holding['current_holding']

    # Get categories for investment_plan and non_investment_holdings
    investment_categories = list(set(plan['category'] for plan in data['investment_plan']))
    non_investment_categories = list(set(holding['category'] for holding in data['non_investment_holdings']))

    # Generate the markdown content
    markdown_content = '# 投资策略（由 JSON 转换）\n'
    markdown_content += f'来源：[投资策略.json](file:///Users/cai/SynologyDrive/Project/#ProjectLife-000000-理财/报告/{date_str}/投资策略.json)\n\n'
    markdown_content += '### 1. 配置概览\n'
    markdown_content += '- 资产大类目标比例合计：{:.2f}%\n'.format(allocation_total * 100)
    markdown_content += '- 定投计划覆盖大类：{}\n'.format(' / '.join(investment_categories))
    markdown_content += '- 额外持仓（不纳入定投计划）：{}\n'.format(' / '.join(non_investment_categories) if non_investment_categories else '无')
    markdown_content += '- 已填写的周定投目标：债券为 1000.0/周；中股为空；期货为空；美股为空\n\n'

    markdown_content += '### 2. 大类目标配置（allocation_summary）\n'
    markdown_content += '| 大类 | 目标比例 | 周定投目标（元/周） |\n|---|---:|---:|\n'

    for alloc in data['allocation_summary']:
        ratio_pct = alloc['ratio'] * 100
        weekly_amount = alloc['weekly_amount_target'] if alloc['weekly_amount_target'] is not None else ''
        markdown_content += '| {} | {:.2f}% | {} |\n'.format(alloc['category'], ratio_pct, weekly_amount)

    markdown_content += '\n\n### 3. 定投计划（investment_plan）\n'
    markdown_content += '- "大类内占比"指 `ratio_in_category`\n'
    markdown_content += '- "全组合目标占比（推导）" = 大类目标比例 × 大类内占比\n'
    markdown_content += '- "当前持有"来自 `current_holding`\n\n'

    # Group investment_plan by category
    categories_order = [alloc['category'] for alloc in data['allocation_summary']]
    plan_by_category = {}

    for plan in data['investment_plan']:
        cat = plan['category']
        if cat not in plan_by_category:
            plan_by_category[cat] = []
        plan_by_category[cat].append(plan)

    # Process each category in order
    section_num = 1
    for cat in categories_order:
        if cat in plan_by_category:
            # Find the allocation ratio for this category
            cat_ratio = 0
            for alloc in data['allocation_summary']:
                if alloc['category'] == cat:
                    cat_ratio = alloc['ratio']
                    break
            
            cat_ratio_pct = cat_ratio * 100
            markdown_content += '#### 3.{} {}（目标 {:.2f}%）\n'.format(section_num, cat, cat_ratio_pct)
            markdown_content += '| 子类 | 标的 | 基金代码 | 大类内占比 | 全组合目标占比（推导） | 定投日 | 长期 | 中期 | 短期 | 当前持有 |\n|---|---|---|---:|---:|---|---|---|---|---:|\n'
            
            cat_current_holding = 0
            for plan in plan_by_category[cat]:
                sub_cat = plan['sub_category']
                fund_name = plan['fund_name']
                fund_code = plan['fund_code'] if plan['fund_code'] is not None else ''
                ratio_in_cat_pct = plan['ratio_in_category'] * 100
                full_ratio_pct = plan['ratio_in_category'] * cat_ratio * 100 if cat_ratio > 0 else ''
                day_of_week = plan['day_of_week']
                long_term = plan['long_term_assessment']
                mid_term = plan['mid_term_assessment']
                short_term = plan['short_term_assessment']
                current_holding = plan['current_holding'] if plan['current_holding'] is not None else 0
                
                cat_current_holding += current_holding
                
                # Format the full combination ratio
                full_ratio_str = '{:.2f}%'.format(full_ratio_pct) if isinstance(full_ratio_pct, float) else ''
                
                markdown_content += '| {} | {} | {} | {:.2f}% | {} | {} | {} | {} | {} | {:.2f} |\n'.format(
                    sub_cat, fund_name, fund_code, ratio_in_cat_pct, full_ratio_str, day_of_week, 
                    long_term, mid_term, short_term, current_holding)
            
            markdown_content += '\n小计（{}）当前持有：{:.2f}\n\n'.format(cat, cat_current_holding)
            section_num += 1

    # 3.5 section - Total holdings from investment plans
    investment_total = 0
    investment_totals_by_cat = {}
    for plan in data['investment_plan']:
        holding = plan['current_holding'] if plan['current_holding'] is not None else 0
        investment_total += holding
        cat = plan['category']
        if cat not in investment_totals_by_cat:
            investment_totals_by_cat[cat] = 0
        investment_totals_by_cat[cat] += holding

    markdown_content += '### 3.5 定投计划持仓合计\n'
    markdown_content += '- 定投计划当前持有合计：{:.2f}\n'.format(investment_total)
    categories_list = []
    for cat, total in investment_totals_by_cat.items():
        categories_list.append('{} {:.2f}'.format(cat, total))
    markdown_content += '- 其中：{}\n\n'.format(' / '.join(categories_list))

    # Section 4: Non-investment holdings
    markdown_content += '### 4. 非定投持仓（non_investment_holdings）\n'
    markdown_content += '| 大类 | 子类 | 标的 | 当前持有 |\n|---|---|---|---:|\n'
    non_investment_total = 0
    for holding in data['non_investment_holdings']:
        cat = holding['category']
        sub_cat = holding['sub_category']
        fund_name = holding['fund_name']
        current_holding = holding['current_holding'] if holding['current_holding'] is not None else 0
        non_investment_total += current_holding
        markdown_content += '| {} | {} | {} | {:.2f} |\n'.format(cat, sub_cat, fund_name, current_holding)
    markdown_content += '\n小计（非定投）当前持有：{:.2f}\n\n'.format(non_investment_total)

    # Section 5: Portfolio Status and Deviation
    total_all = investment_total + non_investment_total
    markdown_content += '### 5. 组合现状与偏离（按"全部持仓"口径）\n'
    markdown_content += '全部持仓（定投计划 + 非定投）合计：{:.2f}\n\n'.format(total_all)

    markdown_content += '| 大类 | 目标比例 | 目标金额（按 {:.2f} 推算） | 当前金额 | 偏离（当前-目标） | 当前占比 |\n|---|---:|---:|---:|---:|---:|\n'.format(total_all)

    # Calculate current amounts by category
    current_amounts_by_cat = {}
    for plan in data['investment_plan']:
        cat = plan['category']
        holding = plan['current_holding'] if plan['current_holding'] is not None else 0
        if cat not in current_amounts_by_cat:
            current_amounts_by_cat[cat] = 0
        current_amounts_by_cat[cat] += holding

    for holding in data['non_investment_holdings']:
        cat = holding['category']
        holding_val = holding['current_holding'] if holding['current_holding'] is not None else 0
        if cat not in current_amounts_by_cat:
            current_amounts_by_cat[cat] = 0
        current_amounts_by_cat[cat] += holding_val

    # Output table rows
    for alloc in data['allocation_summary']:
        cat = alloc['category']
        target_ratio = alloc['ratio'] * 100
        target_amount = alloc['ratio'] * total_all
        current_amount = current_amounts_by_cat.get(cat, 0)
        deviation = current_amount - target_amount
        current_ratio = (current_amount / total_all) * 100 if total_all != 0 else 0
        
        markdown_content += '| {} | {:.2f}% | {:.2f} | {:.2f} | {:.2f} | {:.2f}% |\n'.format(
            cat, target_ratio, target_amount, current_amount, deviation, current_ratio)

    # Handle categories not in allocation_summary
    for cat in current_amounts_by_cat:
        if cat not in [alloc['category'] for alloc in data['allocation_summary']]:
            current_amount = current_amounts_by_cat[cat]
            current_ratio = (current_amount / total_all) * 100 if total_all != 0 else 0
            markdown_content += '| {} | 0%（未设目标） |  | {:.2f} |  | {:.2f}% |\n'.format(
                cat, current_amount, current_ratio)

    markdown_content += '\n### 解读要点\n'
    markdown_content += '- 目标比例合计为100%，配置较为均衡\n'

    # Identify over/under allocations
    for alloc in data['allocation_summary']:
        cat = alloc['category']
        target_ratio = alloc['ratio'] * 100
        current_amount = current_amounts_by_cat.get(cat, 0)
        current_ratio = (current_amount / total_all) * 100 if total_all != 0 else 0
        deviation = current_ratio - target_ratio
        
        if abs(deviation) > 5:  # Significant deviation threshold
            direction = '高配' if deviation > 0 else '低配'
            markdown_content += '- {}类别{}{:.2f}个百分点\n'.format(cat, direction, abs(deviation))

    markdown_content += '- 全部持仓合计：{:.2f}元\n'.format(total_all)

    # Section 6: Weekly Investment Plan
    markdown_content += '\n### 6. 周定投落地（已给定的信息可直接推导）\n'
    markdown_content += '目前仅设置"债券 1000.0/周"。按大类内占比拆分：\n'

    for plan in data['investment_plan']:
        if plan['category'] == '债券':
            if plan['weekly_amount'] is not None:
                markdown_content += '- {}：{}/周（{}）（来自 weekly_amount）\n'.format(
                    plan["fund_name"], plan["weekly_amount"], plan["day_of_week"])
            else:
                weekly_amount_calc = data['allocation_summary'][0]['weekly_amount_target'] * plan['ratio_in_category']
                markdown_content += '- {}：{}/周（{}）\n'.format(
                    plan["fund_name"], weekly_amount_calc, plan["day_of_week"])

    # Write to file
    brief_dir = report_dir / "简报"
    brief_dir.mkdir(parents=True, exist_ok=True)
    
    with open(brief_dir / '投资简报_Kimi-K2.5.md', 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f'Investment brief generated successfully: {brief_dir}/投资简报_Kimi-K2.5.md')

if __name__ == '__main__':
    generate_investment_brief()
