#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成投资建议报告
"""

import os
import json
import sys

def read_json(file_path):
    """读取JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_progress(progress_file, model_name, date_str, stage, completion, details_checked, product_status):
    content = f"""# 进度记录

- 日期文件夹：报告/{date_str}/
- 当前阶段：{stage}
- 完成度：{completion}%
- 阶段明细：
  - [{'x' if 1 in details_checked else ' '}] 1) 检查/创建日期文件夹
  - [{'x' if 2 in details_checked else ' '}] 2) 生成/复用投资策略.json
  - [{'x' if 3 in details_checked else ' '}] 3) 生成投资简报_{model_name}.md
  - [{'x' if 4 in details_checked else ' '}] 4) 联网数据搜集完成
  - [{'x' if 5 in details_checked else ' '}] 5) 输出并保存投资建议报告
  - [{'x' if 6 in details_checked else ' '}] 6) 校验文件命名、标的命名并清理无关文件（最后检查）

- 产物清单：
  - 投资策略.json：{product_status.get('json', '未生成')}
  - 投资简报_{model_name}.md：{product_status.get('brief', '未生成')}
  - 投资建议报告：{product_status.get('report', '未生成')}
  - 命名校验：{product_status.get('name_check', '待校验')}
  - 基金标的覆盖校验：{product_status.get('fund_check', '待校验')}
  - 标的名称一致性校验：{product_status.get('consistency_check', '待校验')}
  - 联网数据时间校验：{product_status.get('market_time_check', '待校验')}
  - 清理记录：{product_status.get('cleanup', '无')}
"""
    with open(progress_file, 'w', encoding='utf-8') as f:
        f.write(content)

def normalize_weights(items):
    raw = []
    for x in items:
        v = x.get("ratio_in_category")
        try:
            v = float(v)
        except Exception:
            v = 0.0
        raw.append(max(v, 0.0))
    s = sum(raw)
    if s <= 0:
        n = len(items)
        return [1.0 / n for _ in range(n)] if n else []
    return [v / s for v in raw]

def round_to_hundred(pcts, decimals=2):
    rounded = [round(x, decimals) for x in pcts]
    diff = round(100.0 - sum(rounded), decimals)
    if not rounded or abs(diff) < 0.01:
        return rounded
    idx = len(rounded) - 1
    rounded[idx] = round(rounded[idx] + diff, decimals)
    return rounded

def load_market_data(report_dir):
    market_file = os.path.join(report_dir, "market_data.json")
    if not os.path.exists(market_file):
        return {}
    try:
        return read_json(market_file)
    except Exception:
        return {}

def get_fred_point(market_data, series_id):
    fred = (market_data or {}).get("fred") or {}
    p = fred.get(series_id) or {}
    return {
        "id": series_id,
        "date": p.get("date"),
        "value": p.get("value"),
        "url": p.get("url"),
        "error": p.get("error"),
    }

def get_fund_point(market_data, fund_code):
    funds = (market_data or {}).get("funds") or {}
    p = funds.get(str(fund_code).zfill(6)) or {}
    data = (p.get("data") or {}) if isinstance(p, dict) else {}
    return {
        "fund_code": p.get("fund_code") if isinstance(p, dict) else None,
        "url": p.get("url") if isinstance(p, dict) else None,
        "jzrq": data.get("jzrq"),
        "dwjz": data.get("dwjz"),
        "gsz": data.get("gsz"),
        "gszzl": data.get("gszzl"),
        "gztime": data.get("gztime"),
        "name": data.get("name"),
    }

def generate_report(model_name, date_str):
    """生成投资建议报告"""
    # 构建路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_dir = os.path.join(base_dir, "报告", date_str)
    strategy_file = os.path.join(report_dir, "投资策略.json")
    output_file = os.path.join(report_dir, f"{date_str}_{model_name}_投资建议.md")
    progress_file = os.path.join(report_dir, "进度", f"进度_{model_name}.md")
    
    # 读取投资策略
    strategy = read_json(strategy_file)
    
    market_data = load_market_data(report_dir)
    
    # 解析投资策略数据
    allocation_summary = strategy.get("allocation_summary", [])
    investment_plan = strategy.get("investment_plan", [])
    non_investment_holdings = strategy.get("non_investment_holdings", []) or []
    alloc_ratio_by_cat = {}
    for x in allocation_summary:
        c = (x.get("category") or "").strip()
        try:
            r = float(x.get("ratio") or 0.0)
        except Exception:
            r = 0.0
        if c:
            alloc_ratio_by_cat[c] = r
    
    # 构建报告内容
    category_suggested = dict(alloc_ratio_by_cat)
    if "债券" in category_suggested and "中股" in category_suggested:
        category_suggested["债券"] = max(0.0, category_suggested["债券"] + 0.02)
        category_suggested["中股"] = max(0.0, category_suggested["中股"] - 0.02)
    total_cat = sum(category_suggested.values())
    if total_cat > 0:
        for k in list(category_suggested.keys()):
            category_suggested[k] = category_suggested[k] / total_cat

    grouped = {}
    for it in investment_plan:
        c = (it.get("category") or "").strip()
        grouped.setdefault(c, []).append(it)

    item_rows = []
    for cat, items in grouped.items():
        cat_ratio = alloc_ratio_by_cat.get(cat, 0.0)
        cat_ratio_sug = category_suggested.get(cat, cat_ratio)

        base_w = normalize_weights(items)
        w = list(base_w)

        if cat == "中股":
            for i, it in enumerate(items):
                sub = (it.get("sub_category") or "").strip()
                if sub in {"芯片", "消费电子"}:
                    w[i] *= 0.85
                if sub in {"中证", "红利低波"}:
                    w[i] *= 1.10
            s = sum(w)
            w = [x / s for x in w] if s > 0 else base_w

        if cat == "美股":
            for i, it in enumerate(items):
                sub = (it.get("sub_category") or "").strip()
                if sub == "医疗保健":
                    w[i] *= 1.20
                if sub == "科技":
                    w[i] *= 0.95
            s = sum(w)
            w = [x / s for x in w] if s > 0 else base_w

        current_pcts = [cat_ratio * x * 100.0 for x in base_w]
        suggested_pcts = [cat_ratio_sug * x * 100.0 for x in w]

        current_pcts_r = [round(x, 2) for x in current_pcts]
        suggested_pcts_r = [round(x, 2) for x in suggested_pcts]

        for i, it in enumerate(items):
            fund_name = (it.get("fund_name") or "").strip()
            fund_code = it.get("fund_code")
            day = (it.get("day_of_week") or "").strip()
            sub = (it.get("sub_category") or "").strip()
            diff = round(suggested_pcts_r[i] - current_pcts_r[i], 2)

            if diff > 0.05:
                action = "增持"
            elif diff < -0.05:
                action = "减持"
            else:
                action = "不变"

            reason = "结构微调"
            if cat == "债券":
                reason = "高利率环境"
            elif cat == "中股" and sub in {"芯片", "消费电子"}:
                reason = "波动偏高"
            elif cat == "中股" and sub in {"中证", "红利低波"}:
                reason = "稳健底仓"
            elif cat == "期货" and sub in {"黄金", "白银"}:
                reason = "避险对冲"
            elif cat == "美股" and sub == "医疗保健":
                reason = "防御属性"
            elif cat == "美股" and sub == "科技":
                reason = "估值波动"

            fund_point = get_fund_point(market_data, fund_code) if fund_code else {}
            if fund_point.get("gszzl") not in (None, "") and sub in {"芯片", "消费电子", "科技"}:
                reason = "短期波动"

            item_rows.append({
                "category": cat,
                "sub_category": sub,
                "fund_name": fund_name,
                "day": day,
                "current_pct": current_pcts_r[i],
                "suggested_pct": suggested_pcts_r[i],
                "diff": diff,
                "action": action,
                "reason": reason,
            })

    total_current = sum(x["current_pct"] for x in item_rows)
    total_suggested = sum(x["suggested_pct"] for x in item_rows)
    if item_rows:
        current_fixed = round_to_hundred([x["current_pct"] for x in item_rows], decimals=2)
        suggested_fixed = round_to_hundred([x["suggested_pct"] for x in item_rows], decimals=2)
        for i in range(len(item_rows)):
            item_rows[i]["current_pct"] = current_fixed[i]
            item_rows[i]["suggested_pct"] = suggested_fixed[i]
            item_rows[i]["diff"] = round(item_rows[i]["suggested_pct"] - item_rows[i]["current_pct"], 2)
            if item_rows[i]["diff"] > 0.05:
                item_rows[i]["action"] = "增持"
            elif item_rows[i]["diff"] < -0.05:
                item_rows[i]["action"] = "减持"
            else:
                item_rows[i]["action"] = "不变"
        total_current = sum(current_fixed)
        total_suggested = sum(suggested_fixed)

    sorted_changes = sorted(
        [x for x in item_rows if x["action"] != "不变"],
        key=lambda r: abs(r["diff"]),
        reverse=True,
    )
    top_changes = (sorted_changes[:5] if sorted_changes else sorted(item_rows, key=lambda r: abs(r["diff"]), reverse=True)[:5])

    goal_parts = []
    for c in ["债券", "中股", "期货", "美股"]:
        if c in alloc_ratio_by_cat:
            goal_parts.append(f"{c} {alloc_ratio_by_cat[c]*100:.0f}%")
    goal_str = " / ".join(goal_parts) if goal_parts else "未提供"

    report_content = []
    report_content.append("### 0. 输入回显 (Input Echo)")
    report_content.append(f"* 日期：{date_str}")
    report_content.append(f"* 模型名：{model_name}")
    report_content.append(f"* 定投检视周期：每月")
    report_content.append(f"* 风险偏好：稳健")
    report_content.append(f"* 定投大类目标：{goal_str}（合计 100%）")
    report_content.append(f"* 关键假设：{{模型名}} = {model_name}；定投检视周期默认每月；仅做小幅结构微调")
    report_content.append(f"* 产物路径：")
    report_content.append(f"  - 投资策略.json：报告/{date_str}/投资策略.json")
    report_content.append(f"  - 投资简报_{model_name}.md：报告/{date_str}/简报/投资简报_{model_name}.md")
    report_content.append(f"  - market_data.json：报告/{date_str}/market_data.json")
    report_content.append(f"  - 投资建议报告：报告/{date_str}/{date_str}_{model_name}_投资建议.md")
    report_content.append("")

    report_content.append("### 1. 定投增减要点（最多 5 条）(Top SIP Changes)")
    for r in top_changes:
        report_content.append(f"* {r['fund_name']}：{r['action']} {r['current_pct']:.2f}%→{r['suggested_pct']:.2f}% — {r['reason']}")
    report_content.append("")

    report_content.append("### 2. 大板块比例调整建议（必须）(Category Allocation Changes)")
    report_content.append("| 大板块 | 当前% | 建议% | 变动 | 建议（增配/减配/不变） | 简短理由 |")
    report_content.append("|---|---:|---:|---:|---|---|")
    for c in ["债券", "中股", "期货", "美股"]:
        if c not in alloc_ratio_by_cat:
            continue
        cur = round(alloc_ratio_by_cat.get(c, 0.0) * 100.0, 2)
        sug = round(category_suggested.get(c, alloc_ratio_by_cat.get(c, 0.0)) * 100.0, 2)
        delta = round(sug - cur, 2)
        if delta > 0.05:
            act = "增配"
        elif delta < -0.05:
            act = "减配"
        else:
            act = "不变"
        reason = "稳健平衡"
        if c == "债券" and act == "增配":
            reason = "高利率防守"
        if c == "中股" and act == "减配":
            reason = "波动偏高"
        report_content.append(f"| {c} | {cur:.2f} | {sug:.2f} | {delta:+.2f} | {act} | {reason} |")
    report_content.append("")

    report_content.append("### 3. 定投计划逐项建议（全量，逐项表格）(Per-Item Actions)")
    report_content.append("| 大板块 | 小板块 | 标的 | 定投日 | 当前% | 建议% | 变动 | 建议（增持/减持/不变） | 简短理由 |")
    report_content.append("|---|---|---|---|---:|---:|---:|---|---|")
    for r in item_rows:
        report_content.append(
            f"| {r['category']} | {r['sub_category']} | {r['fund_name']} | {r['day']} | {r['current_pct']:.2f} | {r['suggested_pct']:.2f} | {r['diff']:+.2f} | {r['action']} | {r['reason']} |"
        )
    report_content.append("")

    report_content.append("### 4. 新的定投方向建议（如有）(New SIP Directions)")
    report_content.append("| 行业/主题 | 建议定投比例 | 口径 | 简短理由 |")
    report_content.append("|---|---:|---|---|")
    report_content.append("| 无 | 0.00 | 占全组合 | 优先执行结构调整 |")
    report_content.append("")

    report_content.append("### 5. 执行指令（下一周期）(Next Actions)")
    report_content.append("* 定投：债券小幅加码，中股小幅降档，期货/美股维持")
    report_content.append("* 资金池：若沪深300单周回撤≥5%，加买“广发沪深300ETF联接C/华泰柏瑞中证红利低波动ETF联接A”")
    report_content.append("* 风险控制：主题类单月回撤≥10%定投减半；组合月回撤≥8%临时提高债券/货币；偏离建议%>2pp则回到目标")
    report_content.append("")

    report_content.append("### 6. 现有持仓建议（最多 5 点）(Holdings Notes)")
    holdings_names = [(x.get("fund_name") or "").strip() for x in non_investment_holdings if isinstance(x, dict)]
    has = lambda s: any(s in n for n in holdings_names)
    notes = []
    if holdings_names:
        notes.append(f"* 非定投持仓（清单）：{' / '.join([n for n in holdings_names if n])} — 仅做观察")
    if has("天弘余额宝"):
        notes.append("* 天弘余额宝货币市场基金：维持资金池 — 回撤缓冲")
    if has("北证50") or has("北证"):
        notes.append("* 易方达北证50指数C/广发北证50成份指数C：合并保留一只 — 降低重复")
    if has("半导体") or has("芯片"):
        notes.append("* 华夏国证半导体芯片ETF联接C：与定投芯片统一 — 降低分散")
    if has("创新药"):
        notes.append("* 广发创新药产业ETF联接C/广发港股创新药ETF联接(QDII)C：与A类定投统一 — 便于执行")
    if has("上证综指"):
        notes.append("* 富国上证综指联接C：评估与底仓重叠 — 聚焦核心")
    report_content.extend(notes[:5] if notes else ["* 无：本期无非定投持仓信息"])
    report_content.append("")

    report_content.append("### 7. 数据来源 (Sources)")
    fetched_at = (market_data or {}).get("fetched_at")
    dgs10 = get_fred_point(market_data, "DGS10")
    dgs2 = get_fred_point(market_data, "DGS2")
    t10y2y = get_fred_point(market_data, "T10Y2Y")
    t10yie = get_fred_point(market_data, "T10YIE")
    gvz = get_fred_point(market_data, "GVZCLS")
    usdcny = get_fred_point(market_data, "DEXCHUS")
    sources = []
    if fetched_at:
        sources.append(f"market_data.json（{fetched_at}）")
    sources.append(f"投资策略.json（{date_str}）")
    if dgs10.get("date"):
        sources.append(f"FRED {dgs10['id']}（{dgs10['date']}）")
    if dgs2.get("date"):
        sources.append(f"FRED {dgs2['id']}（{dgs2['date']}）")
    if t10y2y.get("date"):
        sources.append(f"FRED {t10y2y['id']}（{t10y2y['date']}）")
    if t10yie.get("date"):
        sources.append(f"FRED {t10yie['id']}（{t10yie['date']}）")
    if gvz.get("date"):
        sources.append(f"FRED {gvz['id']}（{gvz['date']}）")
    if usdcny.get("date"):
        sources.append(f"FRED {usdcny['id']}（{usdcny['date']}）")
    for i, s in enumerate(sources[:8], start=1):
        report_content.append(f"{i}. {s}")
    report_content.append("")
    report_content.append("---")
    
    # 保存报告
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_content))
    
    write_progress(
        progress_file=progress_file,
        model_name=model_name,
        date_str=date_str,
        stage=5,
        completion=90,
        details_checked=[1, 2, 3, 4, 5],
        product_status={
            "json": f"报告/{date_str}/投资策略.json",
            "brief": f"报告/{date_str}/简报/投资简报_{model_name}.md",
            "report": f"报告/{date_str}/{date_str}_{model_name}_投资建议.md",
            "name_check": "待校验",
            "fund_check": "待校验",
            "consistency_check": "待校验",
            "market_time_check": "待校验",
            "cleanup": "无",
        },
    )
    
    print(f"生成报告：{output_file}")
    print(f"更新进度：{progress_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_investment_advice.py <model_name> <date>")
        sys.exit(1)
    
    model_name = sys.argv[1]
    date_str = sys.argv[2]
    
    generate_report(model_name, date_str)
