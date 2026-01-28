import pandas as pd
import json
import os
import sys
from datetime import date
from pathlib import Path
import re
import argparse

# --- Command Line Arguments ---
parser = argparse.ArgumentParser()
parser.add_argument('--model', type=str, default="Gemini-3-Pro-Preview", help='Model name')
parser.add_argument('--date', type=str, default=date.today().isoformat(), help='Date in YYYY-MM-DD format')
parser.add_argument('--fetch', action='store_true', help='Fetch market data')
parser.add_argument('--validate', action='store_true', help='Validate files')
args = parser.parse_args()

# --- Configuration ---
MODEL_NAME = args.model
TODAY = args.date
ROOT_DIR = Path("/Users/cai/SynologyDrive/Project/#ProjectLife-000000-理财")
REPORT_DIR = ROOT_DIR / f"报告/{TODAY}"
PROGRESS_DIR = REPORT_DIR / "进度"
BRIEF_DIR = REPORT_DIR / "简报"
DATA_FILE = ROOT_DIR / "Data/投资策略.xlsx"
JSON_FILE = REPORT_DIR / "投资策略.json"
BRIEF_FILE = BRIEF_DIR / f"投资简报_{MODEL_NAME}.md"
PROGRESS_FILE = PROGRESS_DIR / f"进度_{MODEL_NAME}.md"

# --- 1. Folders ---
def setup_folders():
    print(f"Checking folders for {TODAY}...")
    for p in [REPORT_DIR, PROGRESS_DIR, BRIEF_DIR]:
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            print(f"Created: {p}")
        else:
            print(f"Exists: {p}")

# --- 2. Progress File ---
def update_progress(stage, completion, details_checked=None, product_status=None):
    print(f"Updating progress: Stage {stage}, {completion}%")
    
    # Template structure
    content = f"""# 进度记录

- 日期文件夹：报告/{TODAY}/
- 当前阶段：{stage}
- 完成度：{completion}%
- 阶段明细：
  - [{'x' if details_checked and 1 in details_checked else ' '}] 1) 检查/创建日期文件夹
  - [{'x' if details_checked and 2 in details_checked else ' '}] 2) 生成/复用投资策略.json
  - [{'x' if details_checked and 3 in details_checked else ' '}] 3) 生成投资简报_{MODEL_NAME}.md
  - [{'x' if details_checked and 4 in details_checked else ' '}] 4) 联网数据搜集完成
  - [{'x' if details_checked and 5 in details_checked else ' '}] 5) 输出并保存投资建议报告
  - [{'x' if details_checked and 6 in details_checked else ' '}] 6) 校验文件命名、标的命名并清理无关文件（最后检查）

- 产物清单：
  - 投资策略.json：{product_status.get('json', '未生成') if product_status else '未生成'}
  - 投资简报_{MODEL_NAME}.md：{product_status.get('brief', '未生成') if product_status else '未生成'}
  - 投资建议报告：{product_status.get('report', '未生成') if product_status else '未生成'}
  - 命名校验：{product_status.get('name_check', '待校验') if product_status else '待校验'}
  - 基金标的覆盖校验：{product_status.get('fund_check', '待校验') if product_status else '待校验'}
  - 标的名称一致性校验：{product_status.get('consistency_check', '待校验') if product_status else '待校验'}
  - 清理记录：{product_status.get('cleanup', '无') if product_status else '无'}
"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

# --- 3. Excel to JSON ---
def excel_to_json():
    if JSON_FILE.exists():
        print(f"JSON exists: {JSON_FILE}, skipping generation.")
        return True

    print("Generating 投资策略.json from Excel...")
    try:
        df = pd.read_excel(DATA_FILE, sheet_name=0, header=None)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return False

    # Helper to find row index containing a string
    def find_row(s, start=0):
        for idx, row in df.iloc[start:].iterrows():
            # Check first few columns for the keyword
            for val in row[:5]: 
                if isinstance(val, str) and s in val:
                    return idx
        return None

    # Parse allocation_summary
    start_alloc = find_row("定投大板块比例")
    if start_alloc is None:
        print("Error: Could not find '定投大板块比例'")
        return False
    
    # Headers are usually next row
    header_row_idx = start_alloc + 1
    headers = df.iloc[header_row_idx].astype(str).tolist()
    
    # Map headers
    try:
        col_cat = next(i for i, h in enumerate(headers) if "大板块" in h)
        col_ratio = next(i for i, h in enumerate(headers) if "比例" in h)
        col_weekly = next(i for i, h in enumerate(headers) if "周定投额" in h)
    except StopIteration:
        print("Error: Could not find headers for allocation_summary")
        return False

    allocation_summary = []
    # Iterate until next section
    current_row = header_row_idx + 1
    while current_row < len(df):
        row = df.iloc[current_row]
        first_cell = str(row[0]) if pd.notna(row[0]) else ""
        if "定投计划" in first_cell or "非定投" in first_cell:
            break
        
        cat = row[col_cat]
        if pd.isna(cat) or str(cat).strip() == "":
            current_row += 1
            continue
            
        ratio = row[col_ratio]
        weekly = row[col_weekly]
        
        allocation_summary.append({
            "category": str(cat).strip(),
            "ratio": float(ratio) if pd.notna(ratio) else 0.0,
            "weekly_amount_target": float(weekly) if pd.notna(weekly) else None
        })
        current_row += 1

    # Parse investment_plan
    start_plan = find_row("定投计划", start=current_row)
    if start_plan is None:
         print("Error: Could not find '定投计划'")
         return False
         
    header_row_idx = start_plan + 1
    headers = df.iloc[header_row_idx].astype(str).tolist()
    
    # Map headers (flexible)
    def get_col_idx(keywords):
        for k in keywords:
            for i, h in enumerate(headers):
                if k in h:
                    return i
        return None

    col_cat = get_col_idx(["大板块"])
    col_sub = get_col_idx(["小板块"])
    col_ratio = get_col_idx(["对应大板块比例", "占对应大板块比例"])
    col_code = get_col_idx(["基金代码"])
    col_name = get_col_idx(["基金名", "基金名称"])
    col_weekly = get_col_idx(["周定投额"])
    col_day = get_col_idx(["定投日期", "周几"])
    col_long = get_col_idx(["长期评估", "5年"])
    col_mid = get_col_idx(["中期评估", "1年"])
    col_short = get_col_idx(["短期评估", "1季度"])
    col_holding = get_col_idx(["持仓"]) # This might match "持仓" in date string

    investment_plan = []
    current_row = header_row_idx + 1
    while current_row < len(df):
        row = df.iloc[current_row]
        first_cell = str(row[0]) if pd.notna(row[0]) else ""
        if "非定投" in first_cell:
            break
            
        # Skip if name is empty
        name = row[col_name] if col_name is not None else None
        if pd.isna(name) or str(name).strip() == "":
            current_row += 1
            continue
            
        fund_code = row[col_code] if col_code is not None else None
        if pd.notna(fund_code):
            fund_code = str(fund_code).strip()
            # Ensure leading zeros if it looks like a number code (e.g. 6 digits)
            if fund_code.endswith(".0"): # Remove .0 from float conversion
                fund_code = fund_code[:-2]
            if len(fund_code) < 6 and fund_code.isdigit():
                 fund_code = fund_code.zfill(6)
        else:
            fund_code = None
            
        investment_plan.append({
            "category": str(row[col_cat]).strip() if col_cat is not None and pd.notna(row[col_cat]) else None,
            "sub_category": str(row[col_sub]).strip() if col_sub is not None and pd.notna(row[col_sub]) else None,
            "ratio_in_category": float(row[col_ratio]) if col_ratio is not None and pd.notna(row[col_ratio]) else 0.0,
            "fund_code": fund_code,
            "fund_name": str(name).strip(),
            "weekly_amount": float(row[col_weekly]) if col_weekly is not None and pd.notna(row[col_weekly]) else None,
            "day_of_week": str(row[col_day]).strip() if col_day is not None and pd.notna(row[col_day]) else None,
            "long_term_assessment": str(row[col_long]).strip() if col_long is not None and pd.notna(row[col_long]) else None,
            "mid_term_assessment": str(row[col_mid]).strip() if col_mid is not None and pd.notna(row[col_mid]) else None,
            "short_term_assessment": str(row[col_short]).strip() if col_short is not None and pd.notna(row[col_short]) else None,
            "current_holding": float(row[col_holding]) if col_holding is not None and pd.notna(row[col_holding]) else 0.0
        })
        current_row += 1

    # Parse non_investment_holdings
    start_non = find_row("非定投持仓", start=current_row)
    non_investment_holdings = []
    
    if start_non is not None:
        header_row_idx = start_non + 1
        headers = df.iloc[header_row_idx].astype(str).tolist()
        
        col_cat = get_col_idx(["大板块"])
        col_sub = get_col_idx(["小板块"])
        col_name = get_col_idx(["基金", "标的"])
        col_holding = get_col_idx(["持仓"])
        
        current_row = header_row_idx + 1
        while current_row < len(df):
            row = df.iloc[current_row]
            # Stop if empty row or end
            if pd.isna(row[0]) and pd.isna(row[1]) and pd.isna(row[2]): # weak check
                # Check if really empty
                if all(pd.isna(x) for x in row[:5]):
                    current_row += 1
                    continue # or break? usually break if block ends
                    
            name = row[col_name] if col_name is not None else None
            if pd.isna(name) or str(name).strip() == "":
                current_row += 1
                continue
                
            non_investment_holdings.append({
                "category": str(row[col_cat]).strip() if col_cat is not None and pd.notna(row[col_cat]) else None,
                "sub_category": str(row[col_sub]).strip() if col_sub is not None and pd.notna(row[col_sub]) else None,
                "fund_name": str(name).strip(),
                "current_holding": float(row[col_holding]) if col_holding is not None and pd.notna(row[col_holding]) else 0.0
            })
            current_row += 1

    output = {
        "allocation_summary": allocation_summary,
        "investment_plan": investment_plan,
        "non_investment_holdings": non_investment_holdings
    }
    
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Generated: {JSON_FILE}")
    return True

# --- 4. JSON to Brief Markdown ---
def json_to_brief():
    if BRIEF_FILE.exists():
        print(f"Brief exists: {BRIEF_FILE}, skipping generation.")
        return True

    print(f"Generating {BRIEF_FILE}...")
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return False

    alloc = data.get("allocation_summary", [])
    plan = data.get("investment_plan", [])
    non_inv = data.get("non_investment_holdings", [])

    lines = []
    lines.append("# 投资策略（由 JSON 转换）")
    lines.append(f"来源：[投资策略.json](file://{JSON_FILE})")
    lines.append("")

    # 1. 配置概览
    total_target_ratio = sum(x.get("ratio", 0) for x in alloc) * 100
    plan_cats = sorted(list(set(x.get("category", "") for x in plan if x.get("category"))))
    non_cats = sorted(list(set(x.get("category", "") for x in non_inv if x.get("category"))))
    weekly_targets = [f"{x['category']}为 {x['weekly_amount_target']}/周" for x in alloc if x.get("weekly_amount_target")]
    
    lines.append("### 1. 配置概览")
    lines.append(f"- 资产大类目标比例合计：{total_target_ratio:.2f}%")
    lines.append(f"- 定投计划覆盖大类：{' / '.join(plan_cats) if plan_cats else '无'}")
    lines.append(f"- 额外持仓（不纳入定投计划）：{' / '.join(non_cats) if non_cats else '无'}")
    lines.append(f"- 已填写的周定投目标：{'; '.join(weekly_targets) if weekly_targets else '无'}")
    lines.append("")

    # 2. 大类目标配置
    lines.append("### 2. 大类目标配置（allocation_summary）")
    lines.append("| 大类 | 目标比例 | 周定投目标（元/周） |")
    lines.append("|---|---:|---:|")
    for item in alloc:
        ratio_str = f"{item.get('ratio', 0)*100:.2f}%"
        wk = item.get('weekly_amount_target')
        wk_str = f"{wk:.2f}" if wk is not None else ""
        lines.append(f"| {item.get('category')} | {ratio_str} | {wk_str} |")
    lines.append("")

    # 3. 定投计划
    lines.append("### 3. 定投计划（investment_plan）")
    lines.append("#### 说明")
    lines.append("- “大类内占比”指 `ratio_in_category`")
    lines.append("- “全组合目标占比（推导）” = 大类目标比例 × 大类内占比")
    lines.append("- “当前持有”来自 `current_holding`")
    lines.append("")

    # Group by category, ordered by alloc
    alloc_cats = [x.get("category") for x in alloc]
    # Add any missing categories from plan
    for c in plan_cats:
        if c not in alloc_cats:
            alloc_cats.append(c)

    section_idx = 1
    total_plan_holding = 0
    cat_holdings = {}

    for cat in alloc_cats:
        items = [x for x in plan if x.get("category") == cat]
        if not items:
            continue
        
        # Get target ratio for this category
        cat_ratio = next((x.get("ratio") for x in alloc if x.get("category") == cat), None)
        cat_ratio_str = f"{cat_ratio*100:.2f}" if cat_ratio is not None else "未知"
        
        lines.append(f"#### 3.{section_idx} {cat}（目标 {cat_ratio_str}%）")
        lines.append("| 子类 | 标的 | 基金代码 | 大类内占比 | 全组合目标占比（推导） | 定投日 | 长期 | 中期 | 短期 | 当前持有 |")
        lines.append("|---|---|---|---:|---:|---|---|---|---|---:|")
        
        cat_total_holding = 0
        for item in items:
            sub = item.get("sub_category", "")
            name = item.get("fund_name", "")
            code = item.get("fund_code") or ""
            ratio_in = item.get("ratio_in_category", 0)
            ratio_in_str = f"{ratio_in*100:.2f}%"
            
            total_ratio_str = ""
            if cat_ratio is not None:
                total_ratio_str = f"{cat_ratio * ratio_in * 100:.2f}%"
            
            day = item.get("day_of_week", "")
            long_t = item.get("long_term_assessment", "")
            mid_t = item.get("mid_term_assessment", "")
            short_t = item.get("short_term_assessment", "")
            holding = item.get("current_holding", 0) or 0
            
            cat_total_holding += holding
            total_plan_holding += holding
            
            lines.append(f"| {sub} | {name} | {code} | {ratio_in_str} | {total_ratio_str} | {day} | {long_t} | {mid_t} | {short_t} | {holding:.2f} |")
        
        lines.append(f"\n- 小计（{cat}）当前持有：{cat_total_holding:.2f}\n")
        cat_holdings[cat] = cat_total_holding
        section_idx += 1

    # 3.5
    lines.append("### 3.5 定投计划持仓合计")
    lines.append(f"- 定投计划当前持有合计：{total_plan_holding:.2f}")
    parts = [f"{k} {v:.2f}" for k, v in cat_holdings.items()]
    lines.append(f"- 其中：{' / '.join(parts)}")
    lines.append("")

    # 4. 非定投
    lines.append("### 4. 非定投持仓（non_investment_holdings）")
    lines.append("| 大类 | 子类 | 标的 | 当前持有 |")
    lines.append("|---|---|---|---:|")
    total_non_holding = 0
    for item in non_inv:
        h = item.get("current_holding", 0) or 0
        total_non_holding += h
        lines.append(f"| {item.get('category')} | {item.get('sub_category')} | {item.get('fund_name')} | {h:.2f} |")
    lines.append("")
    lines.append(f"- 小计（非定投）当前持有：{total_non_holding:.2f}")
    lines.append("")

    # 5. 组合现状
    total_all = total_plan_holding + total_non_holding
    lines.append("### 5. 组合现状与偏离（按“全部持仓”口径）")
    lines.append(f"- 全部持仓（定投计划 + 非定投）合计：{total_all:.2f}")
    lines.append("")
    lines.append("| 大类 | 目标比例 | 目标金额（按 总额 推算） | 当前金额 | 偏离（当前-目标） | 当前占比 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    
    # Calculate per category total holding (plan + non)
    all_cats_set = set(cat_holdings.keys())
    for item in non_inv:
        c = item.get("category")
        if c: all_cats_set.add(c)
    
    sorted_cats = sorted(list(all_cats_set))
    # Sort by alloc order if possible
    alloc_order = {x.get("category"): i for i, x in enumerate(alloc)}
    sorted_cats.sort(key=lambda x: alloc_order.get(x, 999))
    
    dev_notes = []

    for cat in sorted_cats:
        # Get target
        target_item = next((x for x in alloc if x.get("category") == cat), None)
        target_ratio = target_item.get("ratio") if target_item else None
        
        # Get current
        curr_val = cat_holdings.get(cat, 0)
        curr_val += sum(x.get("current_holding", 0) or 0 for x in non_inv if x.get("category") == cat)
        
        if target_ratio is not None:
            target_amt = total_all * target_ratio
            dev = curr_val - target_amt
            dev_str = f"{dev:.2f}"
            target_ratio_str = f"{target_ratio*100:.2f}%"
            target_amt_str = f"{target_amt:.2f}"
            
            # Note for deviations
            curr_pct = curr_val / total_all if total_all > 0 else 0
            if abs(curr_pct - target_ratio) > 0.05: # 5% threshold
                 dev_notes.append(f"{cat} 偏离较大：目标 {target_ratio*100:.1f}% vs 当前 {curr_pct*100:.1f}%，偏离 {dev:.2f}")

        else:
            target_ratio_str = "0%（未设目标）"
            target_amt_str = ""
            dev_str = ""
        
        curr_pct_str = f"{curr_val / total_all * 100:.2f}%" if total_all > 0 else "0.00%"
        
        lines.append(f"| {cat} | {target_ratio_str} | {target_amt_str} | {curr_val:.2f} | {dev_str} | {curr_pct_str} |")
        
    lines.append("")
    lines.append("#### 解读要点")
    if dev_notes:
        for n in dev_notes:
            lines.append(f"- {n}")
    else:
        lines.append("- 各板块偏离均在 5% 以内。")
    
    if abs(total_target_ratio - 100) > 0.1:
        lines.append(f"- 注意：目标比例合计为 {total_target_ratio:.2f}%，不等于 100%。")
        
    lines.append("")
    
    # 6. 周定投落地
    lines.append("### 6. 周定投落地（已给定的信息可直接推导）")
    has_weekly_target = any(x.get("weekly_amount_target") for x in alloc)
    
    if not has_weekly_target:
        lines.append("目前未设置任何大类的周定投目标。")
    else:
        for cat_item in alloc:
            cat = cat_item.get("category")
            wk_tgt = cat_item.get("weekly_amount_target")
            if not wk_tgt:
                continue
            
            lines.append(f"- 目前仅设置“{cat} {wk_tgt:.2f}/周”。按大类内占比拆分：")
            
            # Find plan items
            items = [x for x in plan if x.get("category") == cat]
            for item in items:
                name = item.get("fund_name")
                ratio_in = item.get("ratio_in_category", 0)
                day = item.get("day_of_week", "未知")
                
                # Check explicit weekly amount
                explicit_wk = item.get("weekly_amount")
                if explicit_wk is not None:
                    amt = explicit_wk
                    suffix = "（来自 weekly_amount）"
                else:
                    amt = wk_tgt * ratio_in
                    suffix = ""
                
                lines.append(f"  - {name}：{amt:.2f}/周（{day}）{suffix}")
    
    with open(BRIEF_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"Generated: {BRIEF_FILE}")
    return True

# --- Main Execution ---
if __name__ == "__main__":
    setup_folders()
    update_progress(1, 10, details_checked=[1], product_status={})
    
    if excel_to_json():
        update_progress(2, 30, details_checked=[1, 2], product_status={'json': str(JSON_FILE.relative_to(ROOT_DIR))})
    else:
        print("Failed to generate JSON.")
        sys.exit(1)
        
    if json_to_brief():
        update_progress(3, 50, details_checked=[1, 2, 3], product_status={
            'json': str(JSON_FILE.relative_to(ROOT_DIR)),
            'brief': str(BRIEF_FILE.relative_to(ROOT_DIR))
        })
    else:
        print("Failed to generate Brief.")
        sys.exit(1)
