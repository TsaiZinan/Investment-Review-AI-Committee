import json
import sys
import datetime
from pathlib import Path
import argparse

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "报告"
DATA_DIR = PROJECT_ROOT / "Data"

def get_today_str():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def _bp_to_pct(bp: int):
    return bp / 100

def _bp_to_pct_str(bp: int):
    return f"{_bp_to_pct(bp):.2f}%"

def _action_from_diff_bp(diff_bp: int):
    if diff_bp >= 15:
        return "增持"
    if diff_bp <= -15:
        return "减持"
    return "不变"

def _clamp(x: float, lo: float, hi: float):
    return max(lo, min(hi, x))

def _get_fred_value(market_data, series_id: str):
    fred = (market_data or {}).get("fred", {}) or {}
    v = (fred.get(series_id) or {}).get("value")
    return float(v) if v is not None else None

def _get_fred_obs(market_data, series_id: str):
    fred = (market_data or {}).get("fred", {}) or {}
    x = fred.get(series_id) or {}
    if x.get("value") is None:
        return None
    return {
        "id": series_id,
        "value": x.get("value"),
        "date": x.get("date"),
        "url": x.get("url") or f"https://fred.stlouisfed.org/series/{series_id}",
    }

def _normalize_ratio_map(ratios: dict):
    s = sum(float(v) for v in ratios.values()) if ratios else 0.0
    if s <= 0:
        n = len(ratios) or 1
        return {k: 1.0 / n for k in ratios.keys()}
    return {k: float(v) / s for k, v in ratios.items()}

def _propose_category_ratios(cat_ratio_current: dict, market_data):
    proposed = dict(cat_ratio_current)
    real_yield = _get_fred_value(market_data, "DFII10")
    curve = _get_fred_value(market_data, "T10Y2Y")
    usd = _get_fred_value(market_data, "DTWEXBGS")
    gvz = _get_fred_value(market_data, "GVZCLS")
    breakeven = _get_fred_value(market_data, "T10YIE")

    risk_off = 0
    if curve is not None and curve < 0:
        risk_off += 1
    if real_yield is not None and real_yield >= 1.5:
        risk_off += 1
    if gvz is not None and gvz >= 20:
        risk_off += 1
    if usd is not None and usd >= 120:
        risk_off += 1

    if "债券" in proposed:
        proposed["债券"] = _clamp(
            proposed["债券"] + (0.03 if risk_off >= 2 else 0.01 if risk_off == 1 else 0.0),
            0.05,
            0.7,
        )

    if "期货" in proposed:
        gold_bias = 0.0
        if breakeven is not None and breakeven >= 2.5 and (real_yield is None or real_yield < 1.5):
            gold_bias += 0.01
        if real_yield is not None and real_yield >= 2.0 and (usd is None or usd >= 120):
            gold_bias -= 0.01
        proposed["期货"] = _clamp(proposed["期货"] + gold_bias, 0.05, 0.5)

    equity_delta = 0.0
    if "债券" in proposed and "债券" in cat_ratio_current:
        equity_delta -= proposed["债券"] - cat_ratio_current["债券"]
    if "期货" in proposed and "期货" in cat_ratio_current:
        equity_delta -= proposed["期货"] - cat_ratio_current["期货"]

    equities = [c for c in ["中股", "美股"] if c in proposed]
    if equities and abs(equity_delta) > 1e-9:
        each = equity_delta / len(equities)
        for c in equities:
            proposed[c] = _clamp(proposed[c] + each, 0.05, 0.7)

    for k in list(proposed.keys()):
        proposed[k] = max(0.0, float(proposed[k]))
    proposed = _normalize_ratio_map(proposed)

    return proposed, {
        "real_yield": real_yield,
        "curve": curve,
        "usd": usd,
        "gvz": gvz,
        "breakeven": breakeven,
        "risk_off": risk_off,
    }

def _build_category_plan(data, market_data):
    allocation_summary = data.get("allocation_summary", [])
    investment_plan = data.get("investment_plan", [])

    cat_order = [x.get("category") for x in allocation_summary if x.get("category")]
    cat_ratio_current = {x.get("category"): float(x.get("ratio") or 0) for x in allocation_summary if x.get("category")}
    cat_ratio_current = _normalize_ratio_map(cat_ratio_current)
    cat_ratio_proposed, signals = _propose_category_ratios(cat_ratio_current, market_data)

    items_by_cat = {}
    for it in investment_plan:
        c = it.get("category")
        if not c:
            continue
        items_by_cat.setdefault(c, []).append(it)

    def propose_internal(c, items):
        base = [float(x.get("ratio_in_category") or 0) for x in items]
        if not base or sum(base) <= 0:
            n = len(items) or 1
            return [1.0 / n for _ in range(n)]

        if c == "中股":
            if signals.get("risk_off", 0) >= 1:
                delta_by_sub = {"中证": 0.04, "红利低波": 0.03, "芯片": -0.04, "消费电子": -0.03}
            else:
                delta_by_sub = {"中证": -0.02, "红利低波": -0.02, "芯片": 0.03, "消费电子": 0.01}
            raw = []
            for it in items:
                sub = (it.get("sub_category") or "").strip()
                raw.append(max((it.get("ratio_in_category") or 0) + delta_by_sub.get(sub, 0.0), 0.0))
            s = sum(raw)
            return [x / s for x in raw] if s > 0 else base

        if c == "期货":
            real_yield = signals.get("real_yield")
            if real_yield is not None and real_yield >= 1.5:
                delta_by_sub = {"黄金": -0.03, "白银": -0.02, "有色": 0.05}
            else:
                delta_by_sub = {"黄金": 0.03, "白银": 0.01, "有色": -0.04}
            raw = []
            for it in items:
                sub = (it.get("sub_category") or "").strip()
                raw.append(max((it.get("ratio_in_category") or 0) + delta_by_sub.get(sub, 0.0), 0.0))
            s = sum(raw)
            return [x / s for x in raw] if s > 0 else base

        if c == "美股":
            healthcare_idx = [i for i, it in enumerate(items) if "医疗" in (it.get("sub_category") or "")]
            if healthcare_idx:
                h_i = healthcare_idx[0]
                weights = [0.0 for _ in items]
                weights[h_i] = 0.5 if signals.get("risk_off", 0) >= 1 else 0.4
                remaining = 1.0 - weights[h_i]
                others = [i for i in range(len(items)) if i != h_i]
                each = remaining / len(others) if others else 0.0
                for i in others:
                    weights[i] = each
                return weights
            return base

        return base

    item_rows = []
    for c in cat_order:
        items = items_by_cat.get(c, [])
        if not items:
            continue
        proposed_internal = propose_internal(c, items)
        for it, p_int in zip(items, proposed_internal):
            curr = cat_ratio_current.get(c, 0.0) * float(it.get("ratio_in_category") or 0.0)
            prop = cat_ratio_proposed.get(c, 0.0) * float(p_int or 0.0)
            item_rows.append(
                {
                    "category": c,
                    "sub_category": (it.get("sub_category") or "").strip(),
                    "fund_name": (it.get("fund_name") or "").strip(),
                    "day_of_week": (it.get("day_of_week") or "").strip(),
                    "curr_bp": int(round(curr * 10000)),
                    "prop_bp": int(round(prop * 10000)),
                }
            )

    total_prop = sum(x["prop_bp"] for x in item_rows)
    if item_rows and total_prop != 10000:
        item_rows[-1]["prop_bp"] += 10000 - total_prop

    total_curr = sum(x["curr_bp"] for x in item_rows)
    if item_rows and total_curr != 10000:
        item_rows[-1]["curr_bp"] += 10000 - total_curr

    cat_curr_bp = {c: 0 for c in cat_order}
    cat_prop_bp = {c: 0 for c in cat_order}
    for r in item_rows:
        cat_curr_bp[r["category"]] = cat_curr_bp.get(r["category"], 0) + r["curr_bp"]
        cat_prop_bp[r["category"]] = cat_prop_bp.get(r["category"], 0) + r["prop_bp"]

    return cat_order, cat_curr_bp, cat_prop_bp, item_rows, signals

def generate_report_content(strategy, market_data, model_name, today_str):
    review_cycle = "每月"
    risk_pref = "稳健"

    cat_order, cat_curr_bp, cat_prop_bp, item_rows, signals = _build_category_plan(strategy, market_data)

    alloc_echo = " / ".join([f"{c} {_bp_to_pct_str(cat_prop_bp.get(c, 0))}" for c in cat_order])

    fred = (market_data or {}).get("fred", {})
    fred_parts = []
    for sid in ["DGS10", "DFII10", "T10Y2Y", "DTWEXBGS", "T10YIE", "GVZCLS"]:
        x = fred.get(sid) or {}
        if x.get("value") is None:
            continue
        fred_parts.append(f"{sid}={x['value']}({x.get('date')})")

    md = []
    md.append("### 0. 输入回显 (Input Echo)")
    md.append(f"* 日期：{today_str}")
    md.append(f"* 模型名：{model_name}")
    md.append(f"* 定投检视周期：{review_cycle}")
    md.append(f"* 风险偏好：{risk_pref}")
    md.append(f"* 定投大类目标：{alloc_echo}（合计 100%）")
    md.append(f"* 关键假设：以本地 market_data.json 与策略表为准；未引入新增大类")
    md.append(f"* 产物路径：")
    md.append(f"  - 投资策略.json：`报告/{today_str}/投资策略.json`")
    md.append(f"  - 投资简报_{model_name}.md：`报告/{today_str}/简报/投资简报_{model_name}.md`")
    md.append(f"  - 投资建议报告：`报告/{today_str}/{today_str}_{model_name}_投资建议.md`")
    md.append("")

    md.append("### 1. 定投增减要点（最多 5 条）(Top SIP Changes)")
    deltas = []
    for r in item_rows:
        diff = r["prop_bp"] - r["curr_bp"]
        if diff == 0:
            continue
        deltas.append((abs(diff), diff, r))
    deltas.sort(key=lambda x: x[0], reverse=True)
    for _, diff, r in deltas[:5]:
        action = "增持" if diff > 0 else "减持"
        curr = _bp_to_pct_str(r["curr_bp"])
        prop = _bp_to_pct_str(r["prop_bp"])
        reason = "防御+估值低" if "医疗" in r["sub_category"] else "估值偏高" if r["sub_category"] in {"芯片"} else "震荡加仓" if r["fund_name"].endswith("沪深300ETF联接C") else "现金流稳" if r["sub_category"] == "红利低波" else "波动加大" if r["sub_category"] == "消费电子" else "跟随调整"
        md.append(f"* {r['fund_name']}：{action} {curr}→{prop} — {reason}")
    if not deltas:
        md.append("* 全部标的：不变 — 本周期维持既定配置")
    md.append("")

    md.append("### 2. 大板块比例调整建议（必须）(Category Allocation Changes)")
    md.append("| 大板块 | 当前% | 建议% | 变动 | 建议（增配/减配/不变） | 简短理由 |")
    md.append("|---|---:|---:|---:|---|---|")
    for c in cat_order:
        curr_bp = cat_curr_bp.get(c, 0)
        prop_bp = cat_prop_bp.get(c, 0)
        diff_bp = prop_bp - curr_bp
        action = "增配" if diff_bp > 0 else "减配" if diff_bp < 0 else "不变"
        if c == "债券":
            reason = "曲线倒挂防御" if signals.get("curve") is not None and signals["curve"] < 0 else "收益率偏高"
        elif c == "中股":
            reason = "估值博弈"
        elif c == "期货":
            reason = "实际利率影响"
        elif c == "美股":
            reason = "偏防御配置" if signals.get("risk_off", 0) >= 1 else "维持结构"
        else:
            reason = "跟随策略"
        md.append(f"| {c} | {_bp_to_pct_str(curr_bp)} | {_bp_to_pct_str(prop_bp)} | {_bp_to_pct(diff_bp):+.2f}% | {action} | {reason} |")
    md.append("")

    md.append("### 3. 定投计划逐项建议（全量，逐项表格）(Per-Item Actions)")
    md.append("| 大板块 | 小板块 | 标的 | 定投日 | 当前% | 建议% | 变动 | 建议（增持/减持/不变） | 简短理由 |")
    md.append("|---|---|---|---|---:|---:|---:|---|---|")
    for r in item_rows:
        diff_bp = r["prop_bp"] - r["curr_bp"]
        action = _action_from_diff_bp(diff_bp)
        reason = "稳健压舱" if r["category"] == "债券" else "震荡加仓" if r["sub_category"] == "中证" else "估值偏高" if r["sub_category"] == "芯片" else "波动加大" if r["sub_category"] == "消费电子" else "现金流稳" if r["sub_category"] == "红利低波" else "高波动控仓" if r["category"] == "期货" else "偏防御" if r["sub_category"] == "医疗保健" else "跟随调整"
        md.append(
            f"| {r['category']} | {r['sub_category']} | {r['fund_name']} | {r['day_of_week']} | {_bp_to_pct_str(r['curr_bp'])} | {_bp_to_pct_str(r['prop_bp'])} | {_bp_to_pct(diff_bp):+.2f}% | {action} | {reason} |"
        )
    md.append("")

    md.append("### 4. 新的定投方向建议（如有）(New SIP Directions)")
    md.append("| 行业/主题 | 建议定投比例 | 口径 | 简短理由 |")
    md.append("|---|---:|---|---|")
    md.append("| 无 | 0% | 占全组合 | 优先执行结构调整 |")
    md.append("")

    md.append("### 5. 执行指令（下一周期）(Next Actions)")
    md.append("* 定投：维持（板块不变，板块内按“建议%”微调）")
    plan = (strategy or {}).get("investment_plan", []) or []
    pool_fund = None
    for it in plan:
        n = (it.get("fund_name") or "").strip()
        if not n:
            continue
        if "沪深300" in n or "中证500" in n or "中证A500" in n:
            pool_fund = n
            break
    if not pool_fund and plan:
        pool_fund = (plan[0].get("fund_name") or "").strip() or None
    if pool_fund:
        md.append(f"* 资金池：权益类单周回撤≥3%时，优先加仓“{pool_fund}”")
    else:
        md.append("* 资金池：权益类单周回撤≥3%时，优先加仓“中股核心指数”")
    md.append("* 风险控制：1) 分批执行 2) 期货不追涨杀跌 3) 回撤>10%降风险")
    md.append("")

    md.append("### 6. 现有持仓建议（最多 5 点）(Holdings Notes)")
    non_inv = strategy.get("non_investment_holdings", []) or []
    non_names = [str(x.get("fund_name") or "").strip() for x in non_inv if str(x.get("fund_name") or "").strip()]
    if non_names:
        joined = " / ".join(non_names)
        md.append(f"* {joined}：持有 — 底仓定期复核")
    else:
        md.append("* 非定投持仓：无 — ")
    if signals.get("risk_off", 0) >= 2:
        md.append("* 权益仓位：分批执行 — 降追涨风险")
    md.append("* 定投节奏：不加杠杆 — 控回撤")
    md.append("")

    md.append("### 7. 数据来源 (Sources)")
    for sid in ["DFII10", "T10Y2Y", "DTWEXBGS", "DEXCHUS", "NAPM"]:
        obs = _get_fred_obs(market_data, sid)
        if not obs:
            continue
        md.append(f"* {obs['date']} FRED {obs['id']}={obs['value']}：{obs['url']}")
    pmi_source = (market_data or {}).get("china_pmi_source")
    if pmi_source:
        md.append(f"* {pmi_source}")
    xau = ((market_data or {}).get("stooq", {}) or {}).get("xauusd") or {}
    if xau.get("close") is not None and xau.get("date"):
        md.append(f"* {xau['date']} Stooq XAUUSD close={xau['close']}：{xau.get('url') or 'https://stooq.com/q/d/?s=xauusd'}")
    md.append(f"* {today_str} Eastmoney 基金估值接口：market_data.json funds[*].url")

    return "\n".join(md)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--date", default=get_today_str())
    p.add_argument("--market", default=None)
    args = p.parse_args()

    model_name = args.model
    today_str = args.date

    json_path = REPORTS_DIR / today_str / "投资策略.json"
    strategy = load_json(json_path)

    market_data = None
    if args.market:
        market_path = Path(args.market)
        if market_path.exists():
            market_data = load_json(market_path)

    report_content = generate_report_content(strategy, market_data, model_name, today_str)

    report_name = f"{today_str}_{model_name}_投资建议.md"
    output_path = REPORTS_DIR / today_str / report_name

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Generated report: {output_path}")

if __name__ == "__main__":
    main()
