import argparse
import csv
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "Data/投资策略.xlsx"

FRED_SERIES = [
    "DGS10",
    "DGS2",
    "DFII10",
    "T10Y2Y",
    "DTWEXBGS",
    "T10YIE",
    "GVZCLS",
]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="GPT-5.2")
    p.add_argument("--date", dest="report_date", default=date.today().isoformat())
    p.add_argument("--fetch", action="store_true")
    p.add_argument("--template-report", action="store_true")
    p.add_argument("--validate", action="store_true")
    return p.parse_args()


def paths_for(report_date: str, model_name: str):
    report_dir = PROJECT_ROOT / "报告" / report_date
    progress_dir = report_dir / "进度"
    brief_dir = report_dir / "简报"
    json_file = report_dir / "投资策略.json"
    brief_file = brief_dir / f"投资简报_{model_name}.md"
    progress_file = progress_dir / f"进度_{model_name}.md"
    report_file = report_dir / f"{report_date}_{model_name}_投资建议.md"
    market_data_file = report_dir / "market_data.json"
    validation_report_file = report_dir / f"标的一致性校验报告_{model_name}.md"
    return {
        "report_dir": report_dir,
        "progress_dir": progress_dir,
        "brief_dir": brief_dir,
        "json_file": json_file,
        "brief_file": brief_file,
        "progress_file": progress_file,
        "report_file": report_file,
        "market_data_file": market_data_file,
        "validation_report_file": validation_report_file,
    }

# --- 1. Folders ---
def setup_folders(report_date: str, report_dir: Path, progress_dir: Path, brief_dir: Path):
    print(f"Checking folders for {report_date}...")
    for p in [report_dir, progress_dir, brief_dir]:
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            print(f"Created: {p}")
        else:
            print(f"Exists: {p}")

# --- 2. Progress File ---
def update_progress(progress_file: Path, report_date: str, model_name: str, stage, completion, details_checked=None, product_status=None):
    print(f"Updating progress: Stage {stage}, {completion}%")
    
    # Template structure
    content = f"""# 进度记录

- 日期文件夹：报告/{report_date}/
- 当前阶段：{stage}
- 完成度：{completion}%
- 阶段明细：
  - [{'x' if details_checked and 1 in details_checked else ' '}] 1) 检查/创建日期文件夹
  - [{'x' if details_checked and 2 in details_checked else ' '}] 2) 生成/复用投资策略.json
  - [{'x' if details_checked and 3 in details_checked else ' '}] 3) 生成投资简报_{model_name}.md
  - [{'x' if details_checked and 4 in details_checked else ' '}] 4) 联网数据搜集完成
  - [{'x' if details_checked and 5 in details_checked else ' '}] 5) 输出并保存投资建议报告
  - [{'x' if details_checked and 6 in details_checked else ' '}] 6) 校验文件命名、标的命名并清理无关文件（最后检查）

- 产物清单：
  - 投资策略.json：{product_status.get('json', '未生成') if product_status else '未生成'}
  - 投资简报_{model_name}.md：{product_status.get('brief', '未生成') if product_status else '未生成'}
  - 投资建议报告：{product_status.get('report', '未生成') if product_status else '未生成'}
  - 命名校验：{product_status.get('name_check', '待校验') if product_status else '待校验'}
  - 基金标的覆盖校验：{product_status.get('fund_check', '待校验') if product_status else '待校验'}
  - 标的名称一致性校验：{product_status.get('consistency_check', '待校验') if product_status else '待校验'}
  - 清理记录：{product_status.get('cleanup', '无') if product_status else '无'}
"""
    with open(progress_file, 'w', encoding='utf-8') as f:
        f.write(content)

# --- 3. Excel to JSON ---
def excel_to_json(data_file: Path, json_file: Path):
    if json_file.exists():
        print(f"JSON exists: {json_file}, skipping generation.")
        return True

    print("Generating 投资策略.json from Excel...")
    try:
        try:
            df = pd.read_excel(data_file, sheet_name=0, header=None, engine="calamine")
        except Exception:
            df = pd.read_excel(data_file, sheet_name=0, header=None)
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

    def row_has_any(row, needles):
        for val in row[:5]:
            if not isinstance(val, str):
                continue
            for n in needles:
                if n in val:
                    return True
        return False

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
        if row_has_any(row, ["定投计划", "非定投"]):
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
        if row_has_any(row, ["非定投"]):
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
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Generated: {json_file}")
    return True

# --- 4. JSON to Brief Markdown ---
def json_to_brief(json_file: Path, brief_file: Path):
    if brief_file.exists():
        print(f"Brief exists: {brief_file}, skipping generation.")
        return True

    print(f"Generating {brief_file}...")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return False

    alloc = data.get("allocation_summary", [])
    plan = data.get("investment_plan", [])
    non_inv = data.get("non_investment_holdings", [])

    lines = []
    lines.append("# 投资策略（由 JSON 转换）")
    lines.append(f"来源：[投资策略.json](file://{json_file})")
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
    
    with open(brief_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"Generated: {brief_file}")
    return True


def fetch_fred_series(series_id: str):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    with urllib.request.urlopen(url, timeout=20) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    rows = list(csv.reader(raw.splitlines()))
    if len(rows) < 2:
        return {"id": series_id, "url": url, "date": None, "value": None}

    date_idx = None
    value_idx = None
    header = rows[0]
    for i, h in enumerate(header):
        hl = h.strip().lower()
        if hl in {"date", "observation_date"}:
            date_idx = i
        if h.strip() == series_id:
            value_idx = i

    if date_idx is None or value_idx is None:
        return {"id": series_id, "url": url, "date": None, "value": None}

    last_date = None
    last_value = None
    for r in rows[1:]:
        if len(r) <= max(date_idx, value_idx):
            continue
        d = r[date_idx].strip()
        v = r[value_idx].strip()
        if not d or not v or v == ".":
            continue
        try:
            last_date = d
            last_value = float(v)
        except ValueError:
            continue

    return {"id": series_id, "url": url, "date": last_date, "value": last_value}


def fetch_fund_estimate(fund_code: str):
    url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js"
    with urllib.request.urlopen(url, timeout=20) as resp:
        raw = resp.read().decode("utf-8", errors="replace").strip()

    left = raw.find("(")
    right = raw.rfind(")")
    if left == -1 or right == -1 or right <= left:
        return {"fund_code": fund_code, "url": url, "data": None}

    payload = raw[left + 1 : right]
    try:
        data = json.loads(payload)
    except Exception:
        data = None
    return {"fund_code": fund_code, "url": url, "data": data}


def fetch_market_data(out_path: Path, strategy_json=None):
    out = {"fetched_at": date.today().isoformat(), "fred": {}, "funds": {}}
    for s in FRED_SERIES:
        try:
            out["fred"][s] = fetch_fred_series(s)
        except Exception as e:
            out["fred"][s] = {"id": s, "url": f"https://fred.stlouisfed.org/series/{s}", "date": None, "value": None, "error": str(e)}

    fund_codes = []
    if strategy_json and strategy_json.exists():
        try:
            data = json.loads(strategy_json.read_text(encoding="utf-8"))
            plan = data.get("investment_plan", [])
            fund_codes = [x.get("fund_code") for x in plan if x.get("fund_code")]
            fund_codes = list(dict.fromkeys(fund_codes))
        except Exception:
            fund_codes = []

    for code in fund_codes:
        try:
            out["funds"][code] = fetch_fund_estimate(code)
        except Exception as e:
            out["funds"][code] = {"fund_code": code, "url": f"https://fundgz.1234567.com.cn/js/{code}.js", "data": None, "error": str(e)}

    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def pct(x):
    return f"{x:.2f}%"


def build_template_report(report_date: str, model_name: str, json_file: Path, brief_file: Path, report_file: Path, market_data_file: Path):
    data = json.loads(json_file.read_text(encoding="utf-8"))
    alloc = data.get("allocation_summary", [])
    plan = data.get("investment_plan", [])
    non_inv = data.get("non_investment_holdings", [])

    cat_ratio = {x.get("category"): float(x.get("ratio") or 0) for x in alloc}

    market = None
    if market_data_file.exists():
        try:
            market = json.loads(market_data_file.read_text(encoding="utf-8"))
        except Exception:
            market = None

    lines = []
    lines.append("### 0. 输入回显 (Input Echo)")
    lines.append(f"* 日期：{report_date}")
    lines.append(f"* 模型名：{{模型名}} = {model_name}")
    lines.append("* 定投检视周期：每月（默认）")
    lines.append("* 风险偏好：稳健（默认）")
    if alloc:
        parts = [f"{x.get('category')} {pct((x.get('ratio') or 0) * 100)}" for x in alloc]
        lines.append(f"* 定投大类目标（当前）：{' / '.join(parts)}（合计 {pct(sum((x.get('ratio') or 0) for x in alloc) * 100)}）")
    else:
        lines.append("* 定投大类目标（当前）：未知")
    lines.append("* 关键假设：本文件为模板；建议%与当前%相同；后续可覆盖填写")
    lines.append("* 产物路径：")
    lines.append(f"  - 投资策略.json：`报告/{report_date}/投资策略.json`")
    lines.append(f"  - 投资简报_{model_name}.md：`报告/{report_date}/简报/投资简报_{model_name}.md`")
    if market_data_file.exists():
        lines.append(f"  - market_data.json：`报告/{report_date}/market_data.json`")
    lines.append("")

    if market and market.get("fred"):
        lines.append("### 0.1 宏观快照（可选）")
        for sid, rec in market["fred"].items():
            v = rec.get("value")
            d = rec.get("date")
            if v is None or d is None:
                continue
            lines.append(f"* {sid}：{v}（{d}）")
        lines.append("")

    lines.append("### 1. 定投增减要点（最多 5 条）(Top SIP Changes)")
    lines.append("* （待填写）")
    lines.append("")

    lines.append("### 2. 大板块比例调整建议（必须）(Category Allocation Changes)")
    lines.append("| 大板块 | 当前% | 建议% | 变动 | 建议（增配/减配/不变） | 简短理由 |")
    lines.append("|---|---:|---:|---:|---|---|")
    for a in alloc:
        c = a.get("category")
        curr = (a.get("ratio") or 0) * 100
        lines.append(f"| {c} | {pct(curr)} | {pct(curr)} | +0.00% | 不变 |  |")
    lines.append("")

    lines.append("### 3. 定投计划逐项建议（全量，逐项表格）(Per-Item Actions)")
    lines.append("| 大板块 | 小板块 | 标的 | 定投日 | 当前% | 建议% | 变动 | 建议（增持/减持/不变） | 简短理由 |")
    lines.append("|---|---|---|---|---:|---:|---:|---|---|")
    for it in plan:
        cat = it.get("category") or ""
        sub = it.get("sub_category") or ""
        name = it.get("fund_name") or ""
        day = it.get("day_of_week") or ""
        curr = (cat_ratio.get(cat, 0) * float(it.get("ratio_in_category") or 0)) * 100
        lines.append(f"| {cat} | {sub} | {name} | {day} | {pct(curr)} | {pct(curr)} | +0.00% | 不变 |  |")
    lines.append("")

    lines.append("### 4. 新的定投方向建议（如有）(New SIP Directions)")
    lines.append("| 行业/主题 | 建议定投比例 | 口径 | 简短理由 |")
    lines.append("|---|---:|---|---|")
    lines.append("| 无 | 0% | 全组合 | 本周期不新增 |")
    lines.append("")

    lines.append("### 5. 执行指令（下一周期）(Next Actions)")
    lines.append("* 定投：（待填写）")
    lines.append("* 资金池：（待填写）")
    lines.append("* 风险控制：（待填写）")
    lines.append("")

    lines.append("### 6. 现有持仓建议（最多 5 点）(Holdings Notes)")
    if non_inv:
        names = [x.get("fund_name") for x in non_inv if x.get("fund_name")]
        if len(names) <= 5:
            for nm in names:
                lines.append(f"* {nm}：（待填写） — （待填写）")
        else:
            n_groups = 5
            per = (len(names) + n_groups - 1) // n_groups
            groups = [names[i : i + per] for i in range(0, len(names), per)]
            groups = groups[:5]
            for g in groups:
                lines.append(f"* {'、'.join(g)}：（待填写） — （待填写）")
    else:
        lines.append("* 无")
    lines.append("")

    lines.append("### 7. 数据来源 (Sources)")
    if market and market.get("fred"):
        for sid, rec in market["fred"].items():
            url = rec.get("url")
            d = rec.get("date")
            if url and d:
                lines.append(f"* {sid}（{d}）：{url}")
    lines.append("* （待补充：宏观/标的级信息点）")
    lines.append("")

    report_file.write_text("\n".join(lines), encoding="utf-8")
    return True


def validate_report(report_date: str, model_name: str, json_file: Path, report_file: Path, out_md: Path):
    if not report_file.exists():
        out_md.write_text("# 标的名称一致性校验报告\n\n未找到投资建议报告文件。\n", encoding="utf-8")
        return False

    data = json.loads(json_file.read_text(encoding="utf-8"))
    plan = data.get("investment_plan", [])
    non_inv = data.get("non_investment_holdings", [])
    names = [x.get("fund_name") for x in plan if x.get("fund_name")] + [x.get("fund_name") for x in non_inv if x.get("fund_name")]
    names = list(dict.fromkeys(names))

    text = report_file.read_text(encoding="utf-8", errors="replace")
    missing = [n for n in names if n not in text]

    ok_name = report_file.name == f"{report_date}_{model_name}_投资建议.md"
    ok_cover = len(missing) == 0

    lines = []
    lines.append("# 标的名称一致性校验报告")
    lines.append("")
    lines.append(f"- 日期：{report_date}")
    lines.append(f"- 模型名：{model_name}")
    lines.append(f"- 报告文件：`报告/{report_date}/{report_file.name}`")
    lines.append("")
    lines.append("## 校验结果")
    lines.append(f"- 文件命名：{'通过' if ok_name else '不通过'}")
    lines.append(f"- 标的覆盖：{'通过' if ok_cover else '不通过'}")
    lines.append("")
    if missing:
        lines.append("## 缺失标的（未在报告正文中找到逐字匹配）")
        for n in missing:
            lines.append(f"- {n}")
        lines.append("")
    else:
        lines.append("## 覆盖明细")
        lines.append(f"- 共 {len(names)} 个标的均可在报告正文中逐字匹配到")
        lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    return ok_name and ok_cover

# --- Main Execution ---
if __name__ == "__main__":
    args = parse_args()
    model_name = args.model
    report_date = args.report_date
    paths = paths_for(report_date, model_name)
    setup_folders(report_date, paths["report_dir"], paths["progress_dir"], paths["brief_dir"])
    update_progress(paths["progress_file"], report_date, model_name, 1, 10, details_checked=[1], product_status={})
    
    if excel_to_json(DATA_FILE, paths["json_file"]):
        update_progress(paths["progress_file"], report_date, model_name, 2, 30, details_checked=[1, 2], product_status={'json': str(paths["json_file"].relative_to(PROJECT_ROOT))})
    else:
        print("Failed to generate JSON.")
        sys.exit(1)
        
    if json_to_brief(paths["json_file"], paths["brief_file"]):
        update_progress(paths["progress_file"], report_date, model_name, 3, 50, details_checked=[1, 2, 3], product_status={
            "json": str(paths["json_file"].relative_to(PROJECT_ROOT)),
            "brief": str(paths["brief_file"].relative_to(PROJECT_ROOT)),
        })
    else:
        print("Failed to generate Brief.")
        sys.exit(1)

    if args.fetch:
        ok = fetch_market_data(paths["market_data_file"], paths["json_file"])
        if ok:
            update_progress(paths["progress_file"], report_date, model_name, 4, 70, details_checked=[1, 2, 3, 4], product_status={
                "json": str(paths["json_file"].relative_to(PROJECT_ROOT)),
                "brief": str(paths["brief_file"].relative_to(PROJECT_ROOT)),
            })

    if args.template_report:
        ok = build_template_report(
            report_date,
            model_name,
            paths["json_file"],
            paths["brief_file"],
            paths["report_file"],
            paths["market_data_file"],
        )
        if ok:
            update_progress(paths["progress_file"], report_date, model_name, 5, 85, details_checked=[1, 2, 3, 4, 5], product_status={
                "json": str(paths["json_file"].relative_to(PROJECT_ROOT)),
                "brief": str(paths["brief_file"].relative_to(PROJECT_ROOT)),
                "report": str(paths["report_file"].relative_to(PROJECT_ROOT)),
            })

    if args.validate:
        ok = validate_report(report_date, model_name, paths["json_file"], paths["report_file"], paths["validation_report_file"])
        status = "通过" if ok else "不通过"
        update_progress(paths["progress_file"], report_date, model_name, 6, 100 if ok else 95, details_checked=[1, 2, 3, 4, 5, 6], product_status={
            "json": str(paths["json_file"].relative_to(PROJECT_ROOT)),
            "brief": str(paths["brief_file"].relative_to(PROJECT_ROOT)),
            "report": str(paths["report_file"].relative_to(PROJECT_ROOT)) if paths["report_file"].exists() else "未生成",
            "name_check": status,
            "fund_check": status,
            "consistency_check": status,
        })
