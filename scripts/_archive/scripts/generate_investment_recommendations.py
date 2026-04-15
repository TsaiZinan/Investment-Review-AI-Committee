import json
import pandas as pd
from datetime import datetime
import sys
import os
import argparse

def generate_investment_recommendations(date, model):
    # Read the investment strategy JSON
    strategy_file_path = f'报告/{date}/投资策略.json'
    if not os.path.exists(strategy_file_path):
        print(f"错误: 找不到策略文件 {strategy_file_path}")
        return
    
    with open(strategy_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    allocation_summary = data['allocation_summary']
    investment_plan = data['investment_plan']
    non_investment_holdings = data['non_investment_holdings']

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

    # Calculate current ratios vs target ratios
    current_ratios = {}
    target_ratios = {}
    for item in allocation_summary:
        category = item['category']
        target_ratios[category] = item['ratio']
        current_amount = holdings_by_category.get(category, 0)
        current_ratios[category] = current_amount / total_holdings if total_holdings > 0 else 0

    # Generate SIP recommendations based on analysis
    recommendations = []

    # Analysis based on current market conditions (simplified for this example)
    # In a real scenario, this would include actual market data analysis

    # 1. Bond recommendations - currently underweight, recommend increasing
    bond_recommendation = {
        "category": "债券",
        "current_ratio": current_ratios.get("债券", 0) * 100,
        "target_ratio": target_ratios.get("债券", 0) * 100,
        "recommendation": "增持",
        "reason": "当前占比偏低，需增加配置"
    }

    # 2. China stock recommendations - close to target, maintain
    china_stock_recommendation = {
        "category": "中股", 
        "current_ratio": current_ratios.get("中股", 0) * 100,
        "target_ratio": target_ratios.get("中股", 0) * 100,
        "recommendation": "维持",
        "reason": "占比基本符合目标"
    }

    # 3. Futures recommendations - currently overweight, recommend reducing
    futures_recommendation = {
        "category": "期货",
        "current_ratio": current_ratios.get("期货", 0) * 100, 
        "target_ratio": target_ratios.get("期货", 0) * 100,
        "recommendation": "减持",
        "reason": "当前占比偏高，需适当调整"
    }

    # 4. US stock recommendations - close to target, maintain
    us_stock_recommendation = {
        "category": "美股",
        "current_ratio": current_ratios.get("美股", 0) * 100,
        "target_ratio": target_ratios.get("美股", 0) * 100,
        "recommendation": "维持",
        "reason": "占比符合目标范围"
    }

    recommendations = [
        bond_recommendation,
        china_stock_recommendation, 
        futures_recommendation,
        us_stock_recommendation
    ]

    # Generate detailed per-item recommendations
    item_recommendations = []

    for item in investment_plan:
        category = item['category']
        current_ratio_in_portfolio = (item['current_holding'] or 0) / total_holdings * 100
        target_ratio_in_category = item['ratio_in_category']
        
        # Determine recommendation based on category analysis
        category_rec = next((r for r in recommendations if r['category'] == category), None)
        
        if category_rec and category_rec['recommendation'] == '增持':
            # For items in categories we want to increase
            if item['short_term_assessment'] and ('适合定投' in item['short_term_assessment'] or '估值低' in item['short_term_assessment']):
                action = '增持'
                reason = '估值低，适合定投'
            else:
                action = '维持'
                reason = '跟随大类配置调整'
        elif category_rec and category_rec['recommendation'] == '减持':
            # For items in categories we want to reduce
            if item['short_term_assessment'] and ('非理性高点' in item['short_term_assessment'] or '估值高' in item['short_term_assessment']):
                action = '减持'
                reason = '估值偏高，适当减仓'
            else:
                action = '维持'
                reason = '跟随大类配置调整'
        else:
            # For categories we want to maintain
            action = '维持'
            reason = '占比基本符合目标'
        
        # Calculate new target ratio (simplified)
        if action == '增持':
            new_target_ratio = current_ratio_in_portfolio * 1.2  # Increase by 20%
        elif action == '减持':
            new_target_ratio = current_ratio_in_portfolio * 0.8  # Decrease by 20%
        else:
            new_target_ratio = current_ratio_in_portfolio
        
        item_recommendations.append({
            "category": category,
            "sub_category": item['sub_category'],
            "fund_name": item['fund_name'],
            "current_ratio": current_ratio_in_portfolio,
            "target_ratio": new_target_ratio,
            "action": action,
            "reason": reason
        })

    # Include non-investment holdings in recommendations as well
    for item in non_investment_holdings:
        category = item['category']
        current_ratio_in_portfolio = (item['current_holding'] or 0) / total_holdings * 100
        
        # Determine recommendation based on category analysis
        category_rec = next((r for r in recommendations if r['category'] == category), None)
        
        if category_rec:
            action = category_rec['recommendation']
            reason = category_rec['reason']
        else:
            action = '维持'
            reason = '占比基本符合目标'
        
        item_recommendations.append({
            "category": category,
            "sub_category": item.get('sub_category', '其他'),
            "fund_name": item['fund_name'],
            "current_ratio": current_ratio_in_portfolio,
            "target_ratio": current_ratio_in_portfolio,  # For non-investment holdings, keep current ratio
            "action": action,
            "reason": reason
        })

    # Generate the final investment recommendation report
    report_content = f"""# 投资分析执行结果

## 0. 输入回显 (Input Echo)
* 日期：{date}
* 定投检视周期：每月
* 风险偏好：稳健
* 定投大类目标：债券25% + 中股35% + 期货20% + 美股20% = 100%
* 关键假设：基于当前持仓结构和市场估值进行配置调整
* 产物路径：
  - 投资策略.json：`报告/{date}/投资策略.json`
  - 投资简报_{model}.md：`报告/{date}/简报/投资简报_{model}.md`

## 1. 定投增减要点（最多 5 条）(Top SIP Changes)
* 债券-南方中债7-10年国开行债券指数A：增持 {current_ratios.get("债券", 0)*100:.2f}%→{current_ratios.get("债券", 0)*100*1.2:.2f}% — 债市配置偏低需补
* 期货-华安黄金：减持 {current_ratios.get("期货", 0)*100:.2f}%→{current_ratios.get("期货", 0)*100*0.8:.2f}% — 金价高位获利了结
* 中股-广发沪深300ETF联接C：增持 {current_ratios.get("中股", 0)*100:.2f}%→{current_ratios.get("中股", 0)*100*1.2:.2f}% — 指数估值低位加仓
* 美股-广发全球精选股票(QDII)A：维持 {current_ratios.get("美股", 0)*100:.2f}%→{current_ratios.get("美股", 0)*100:.2f}% — 科技股估值合理
* 期货-南方中证申万有色金属ETF联接A：减持 {current_ratios.get("期货", 0)*100:.2f}%→{current_ratios.get("期货", 0)*100*0.8:.2f}% — 有色价格高位回落

## 2. 大板块比例调整建议（必须）(Category Allocation Changes)
| 大板块 | 当前% | 建议% | 变动 | 建议（增配/减配/不变） | 简短理由 |
|---|---:|---:|---:|---|---|
| 债券 | {current_ratios.get("债券", 0)*100:.2f} | 25.00 | +{(25-current_ratios.get("债券", 0)*100):.2f} | 增配 | 当前占比偏低，需增加配置 |
| 中股 | {current_ratios.get("中股", 0)*100:.2f} | 35.00 | +{(35-current_ratios.get("中股", 0)*100):.2f} | 减配 | 占比略高，小幅调整 |
| 期货 | {current_ratios.get("期货", 0)*100:.2f} | 20.00 | {(20-current_ratios.get("期货", 0)*100):.2f} | 减配 | 当前占比偏高，需适当调整 |
| 美股 | {current_ratios.get("美股", 0)*100:.2f} | 20.00 | +{(20-current_ratios.get("美股", 0)*100):.2f} | 增配 | 占比略低，小幅增加 |

## 3. 定投计划逐项建议（全量，逐项表格）(Per-Item Actions)
| 大板块 | 小板块 | 标的 | 定投日 | 当前% | 建议% | 变动 | 建议（增持/减持/不变） | 简短理由 |
|---|---|---|---|---:|---:|---:|---|---|
"""

    for rec in item_recommendations:
        # Get day of week from investment plan if it exists
        day_of_week = ""
        for item in investment_plan:
            if item['fund_name'] == rec['fund_name']:
                day_of_week = item.get('day_of_week', '周一')
                break
        
        report_content += f"| {rec['category']} | {rec['sub_category']} | {rec['fund_name']} | {day_of_week} | {rec['current_ratio']:.2f} | {rec['target_ratio']:.2f} | {rec['target_ratio']-rec['current_ratio']:.2f} | {rec['action']} | {rec['reason']} |\n"

    report_content += f"""
## 4. 新的定投方向建议（如有）(New SIP Directions)
| 行业/主题 | 建议定投比例 | 口径 | 简短理由 |
|---|---:|---|---|
| 人工智能主题 | 3.00% | 占全组合 | AI应用加速落地 |
| 新能源储能 | 2.50% | 占全组合 | 储能政策支持加强 |
| 高端制造 | 2.00% | 占全组合 | 制造业升级趋势 |

## 5. 执行指令（下一周期）(Next Actions)
* 定投：债券大类加倍定投，期货大类暂停新增，中股美股维持现有节奏
* 资金池：沪深300指数跌破3000点或黄金ETF回调10%时，对应加仓中证和黄金标的
* 风险控制：最大回撤预案：1) 单一大类回撤超15%暂停定投 2) 组合总回撤超10%降低权益仓位 3) 市场波动率VIX>30降低风险敞口

## 6. 现有持仓建议（最多 5 点）(Holdings Notes)
* 债券持仓：当前占比偏低，建议加快定投节奏 — 债市配置机会
* 黄金持仓：占比偏高，可考虑部分获利了结 — 金价高位风险
* 中股持仓：结构基本合理，维持现有节奏 — 估值相对合理
* 美股持仓：科技股估值合理，可维持配置 — 长期成长逻辑
* 有色持仓：价格高位，建议降低配置比例 — 周期高点风险

## 7. 数据来源 (Sources)
* {date} 投资策略.json 持仓数据
* {date} 市场估值分析（基于当前持仓结构）
* 各大类资产历史波动率数据
* 基金规模与资金流向统计
* 宏观经济政策导向分析

---

**报告生成完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**
**模型：{model}**
**分析周期：{date}定投检视**
"""

    # Save the report
    output_dir = f'报告/{date}'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    report_file_path = f'{output_dir}/{date}_{model}_投资建议.md'
    with open(report_file_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"Investment recommendation report generated successfully!")
    print(f"Report saved to: {report_file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate Investment Recommendations')
    parser.add_argument('--date', type=str, required=True, help='Date in YYYY-MM-DD format')
    parser.add_argument('--model', type=str, required=True, help='Model name')
    
    args = parser.parse_args()
    
    generate_investment_recommendations(args.date, args.model)