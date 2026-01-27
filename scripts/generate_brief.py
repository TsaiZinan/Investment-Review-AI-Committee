import json
import sys
import datetime
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "报告"

def get_today_str():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def format_currency(value):
    if value is None:
        return ""
    return f"{value:.2f}"

def format_percent(value):
    if value is None:
        return ""
    return f"{value * 100:.2f}%"

def generate_markdown(data, model_name, today_str):
    allocation_summary = data.get("allocation_summary", [])
    investment_plan = data.get("investment_plan", [])
    non_investment_holdings = data.get("non_investment_holdings", [])

    # Calculations
    total_allocation_ratio = sum(item["ratio"] for item in allocation_summary if item["ratio"] is not None)
    
    plan_categories = sorted(list(set(item["category"] for item in investment_plan if item["category"])))
    non_plan_categories = sorted(list(set(item["category"] for item in non_investment_holdings if item["category"])))
    
    weekly_targets = [f"{item['category']}为 {item['weekly_amount_target']}/周" for item in allocation_summary if item.get("weekly_amount_target")]
    weekly_targets_str = " / ".join(weekly_targets) if weekly_targets else "无"

    # Header
    md = [
        f"# 投资策略（由 JSON 转换）",
        f"来源：[投资策略.json](file://{REPORTS_DIR}/{today_str}/投资策略.json)",
        "",
        "### 1. 配置概览",
        f"- 资产大类目标比例合计：{format_percent(total_allocation_ratio)}",
        f"- 定投计划覆盖大类：{' / '.join(plan_categories)}",
        f"- 额外持仓（不纳入定投计划）：{' / '.join(non_plan_categories) if non_plan_categories else '无'}",
        f"- 已填写的周定投目标：{weekly_targets_str}",
        ""
    ]

    # 2. 大类目标配置
    md.append("### 2. 大类目标配置（allocation_summary）")
    md.append("| 大类 | 目标比例 | 周定投目标（元/周） |")
    md.append("|---|---:|---:|")
    for item in allocation_summary:
        ratio = format_percent(item['ratio']) if item['ratio'] is not None else ""
        target = item['weekly_amount_target'] if item['weekly_amount_target'] is not None else ""
        md.append(f"| {item['category']} | {ratio} | {target} |")
    md.append("")

    # 3. 定投计划
    md.append("### 3. 定投计划（investment_plan）")
    md.append("#### 说明")
    md.append("- “大类内占比”指 `ratio_in_category`")
    md.append("- “全组合目标占比（推导）” = 大类目标比例 × 大类内占比")
    md.append("- “当前持有”来自 `current_holding`")
    md.append("")

    # Group by category
    grouped_plan = {}
    for item in investment_plan:
        cat = item['category']
        if cat not in grouped_plan:
            grouped_plan[cat] = []
        grouped_plan[cat].append(item)

    # Order by allocation_summary
    ordered_categories = [item['category'] for item in allocation_summary]
    # Add any missing categories
    for cat in grouped_plan:
        if cat not in ordered_categories:
            ordered_categories.append(cat)

    idx = 1
    total_plan_holding = 0
    plan_holding_by_cat = {}

    for cat in ordered_categories:
        if cat not in grouped_plan:
            continue
        
        items = grouped_plan[cat]
        # Find target ratio for this category
        target_ratio = next((item['ratio'] for item in allocation_summary if item['category'] == cat), None)
        target_ratio_str = format_percent(target_ratio) if target_ratio is not None else "未知"
        
        md.append(f"#### 3.{idx} {cat}（目标 {target_ratio_str}）")
        md.append("| 子类 | 标的 | 基金代码 | 大类内占比 | 全组合目标占比（推导） | 定投日 | 长期 | 中期 | 短期 | 当前持有 |")
        md.append("|---|---|---|---:|---:|---|---|---|---|---:|")
        
        cat_holding = 0
        for item in items:
            sub = item['sub_category']
            name = item['fund_name']
            code = item['fund_code'] if item['fund_code'] else ""
            ratio_in_cat = item['ratio_in_category']
            ratio_in_cat_str = format_percent(ratio_in_cat) if ratio_in_cat is not None else ""
            
            global_ratio = ""
            if target_ratio is not None and ratio_in_cat is not None:
                global_ratio = format_percent(target_ratio * ratio_in_cat)
            
            day = item['day_of_week']
            long_term = item['long_term_assessment']
            mid_term = item['mid_term_assessment']
            short_term = item['short_term_assessment']
            holding = item['current_holding'] if item['current_holding'] is not None else 0
            cat_holding += holding
            
            md.append(f"| {sub} | {name} | {code} | {ratio_in_cat_str} | {global_ratio} | {day} | {long_term} | {mid_term} | {short_term} | {format_currency(holding)} |")
        
        md.append(f"**小计（{cat}）当前持有：{format_currency(cat_holding)}**")
        md.append("")
        
        plan_holding_by_cat[cat] = cat_holding
        total_plan_holding += cat_holding
        idx += 1

    # 3.5 定投计划持仓合计
    md.append("### 3.5 定投计划持仓合计")
    md.append(f"- 定投计划当前持有合计：{format_currency(total_plan_holding)}")
    breakdown = [f"{cat} {format_currency(val)}" for cat, val in plan_holding_by_cat.items()]
    md.append(f"- 其中：{' / '.join(breakdown)}")
    md.append("")

    # 4. 非定投持仓
    md.append("### 4. 非定投持仓（non_investment_holdings）")
    md.append("| 大类 | 子类 | 标的 | 当前持有 |")
    md.append("|---|---|---|---:|")
    
    total_non_plan_holding = 0
    non_plan_holding_by_cat = {}
    
    for item in non_investment_holdings:
        cat = item['category']
        sub = item['sub_category']
        name = item['fund_name']
        holding = item['current_holding'] if item['current_holding'] is not None else 0
        total_non_plan_holding += holding
        
        if cat not in non_plan_holding_by_cat:
            non_plan_holding_by_cat[cat] = 0
        non_plan_holding_by_cat[cat] += holding
        
        md.append(f"| {cat} | {sub} | {name} | {format_currency(holding)} |")
    
    md.append(f"**小计（非定投）当前持有：{format_currency(total_non_plan_holding)}**")
    md.append("")

    # 5. 组合现状与偏离
    total_holding = total_plan_holding + total_non_plan_holding
    
    md.append("### 5. 组合现状与偏离（按“全部持仓”口径）")
    md.append(f"- 全部持仓（定投计划 + 非定投）合计：{format_currency(total_holding)}")
    md.append("")
    md.append("| 大类 | 目标比例 | 目标金额（按总额推算） | 当前金额 | 偏离（当前-目标） | 当前占比 |")
    md.append("|---|---:|---:|---:|---:|---:|")
    
    # Calculate totals per category
    all_categories = sorted(list(set(list(plan_holding_by_cat.keys()) + list(non_plan_holding_by_cat.keys()) + [item['category'] for item in allocation_summary])))
    
    deviations = []
    
    for cat in all_categories:
        target_ratio = next((item['ratio'] for item in allocation_summary if item['category'] == cat), None)
        current_amt = plan_holding_by_cat.get(cat, 0) + non_plan_holding_by_cat.get(cat, 0)
        
        target_ratio_str = format_percent(target_ratio) if target_ratio is not None else "0%（未设目标）"
        target_amt_str = ""
        deviation_str = ""
        current_ratio_str = format_percent(current_amt / total_holding) if total_holding > 0 else "0.00%"
        
        if target_ratio is not None:
            target_amt = total_holding * target_ratio
            target_amt_str = format_currency(target_amt)
            deviation = current_amt - target_amt
            deviation_str = format_currency(deviation)
            deviations.append((cat, deviation))
        
        md.append(f"| {cat} | {target_ratio_str} | {target_amt_str} | {format_currency(current_amt)} | {deviation_str} | {current_ratio_str} |")
    
    md.append("")
    md.append("#### 解读要点")
    # Generate simple insights
    if abs(total_allocation_ratio - 1.0) > 0.001:
        md.append(f"- **注意**：目标比例合计为 {format_percent(total_allocation_ratio)}，不等于 100%。")
    
    # Check category internal ratio sums
    for cat in ordered_categories:
        if cat not in grouped_plan:
            continue
        items = grouped_plan[cat]
        cat_ratio_sum = sum(item['ratio_in_category'] for item in items if item['ratio_in_category'] is not None)
        if abs(cat_ratio_sum - 1.0) > 0.01: # allow small float error
             md.append(f"- **注意**：{cat} 大类内占比合计为 {format_percent(cat_ratio_sum)}，不等于 100%。")

    # High/Low allocation
    sorted_devs = sorted(deviations, key=lambda x: x[1])
    if sorted_devs:
        lowest = sorted_devs[0]
        highest = sorted_devs[-1]
        md.append(f"- 最低配大类：{lowest[0]}（偏离 {format_currency(lowest[1])}）")
        md.append(f"- 最高配大类：{highest[0]}（偏离 {format_currency(highest[1])}）")

    md.append("")

    # 6. 周定投落地
    md.append("### 6. 周定投落地（已给定的信息可直接推导）")
    
    has_weekly_targets = any(item.get("weekly_amount_target") for item in allocation_summary)
    
    if not has_weekly_targets:
        md.append("目前未设置任何大类的周定投目标。")
    else:
        for item in allocation_summary:
            cat = item['category']
            weekly_target = item.get('weekly_amount_target')
            
            if weekly_target is None:
                continue
                
            md.append(f"- 目前设置“{cat} {weekly_target}/周”。按大类内占比拆分：")
            
            if cat in grouped_plan:
                for plan_item in grouped_plan[cat]:
                    name = plan_item['fund_name']
                    day = plan_item['day_of_week']
                    
                    if plan_item.get('weekly_amount') is not None:
                         amount = plan_item['weekly_amount']
                         source = "（来自 weekly_amount）"
                    else:
                        ratio = plan_item['ratio_in_category']
                        amount = weekly_target * ratio if ratio is not None else 0
                        source = ""
                    
                    md.append(f"  - {name}：{format_currency(amount)}/周（{day}）{source}")
            else:
                 md.append(f"  - （该大类下无定投计划，无法拆分）")
    
    return "\n".join(md)

def update_progress(model_name, today_str):
    progress_file = REPORTS_DIR / today_str / "进度" / f"进度_{model_name}.md"
    if not progress_file.exists():
        print(f"Warning: Progress file not found: {progress_file}")
        return

    with open(progress_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update progress
    content = content.replace("当前阶段：1", "当前阶段：3")
    content = content.replace("完成度：10%", "完成度：50%")
    content = content.replace("- [ ] 2) 生成/复用投资策略.json", "- [x] 2) 生成/复用投资策略.json")
    content = content.replace("- [ ] 3) 生成投资简报_{model_name}.md".replace("{model_name}", model_name), f"- [x] 3) 生成投资简报_{model_name}.md")
    
    # Add artifacts
    content = content.replace("投资策略.json：{路径或未生成}", f"投资策略.json：报告/{today_str}/投资策略.json")
    content = content.replace("投资简报_{模型名}.md：{路径或未生成}".replace("{模型名}", model_name), f"投资简报_{model_name}.md：报告/{today_str}/简报/投资简报_{model_name}.md")

    with open(progress_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated progress file: {progress_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_brief.py <model_name>")
        sys.exit(1)
    
    model_name = sys.argv[1]
    today_str = get_today_str()
    
    json_path = REPORTS_DIR / today_str / "投资策略.json"
    if not json_path.exists():
        print(f"Error: {json_path} does not exist.")
        sys.exit(1)
        
    data = load_json(json_path)
    md_content = generate_markdown(data, model_name, today_str)
    
    output_path = REPORTS_DIR / today_str / "简报" / f"投资简报_{model_name}.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
        
    print(f"Generated brief: {output_path}")
    
    update_progress(model_name, today_str)

if __name__ == "__main__":
    main()
