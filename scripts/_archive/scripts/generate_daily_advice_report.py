import json
import os
from datetime import date

# Configuration
MODEL_NAME = "Germini-3-Pro"
TODAY = "2026-02-27"
REPORT_DIR = f"报告/{TODAY}"
JSON_FILE = f"{REPORT_DIR}/投资策略.json"
OUTPUT_FILE = f"{REPORT_DIR}/{TODAY}_{MODEL_NAME}_投资建议.md"

# Web Data Summary (Hardcoded from AI analysis)
WEB_DATA = {
    "US_Rates": "美联储1月维持利率在3.50%-3.75%，暂停降息；通胀核心PCE预计2026年底2.4%。",
    "China_Macro": "2026年GDP目标约4.4%，财政发力，地产企稳但仍弱，货币宽松。",
    "Gold": "金价$4700-$5300高位震荡，央行买盘强劲，JPM看高至$5000+。",
    "Equity": "中国科技股受DeepSeek提振反弹；美股AI泡沫担忧与增长并存。",
    "Sources": [
        "2026-01-28 Fed FOMC Statement (3.50-3.75%)",
        "2026-02-02 Reuters: China property sector measures",
        "2026-02-04 J.P. Morgan Gold Price Forecast ($5000+)",
        "2026-02-04 Reuters: Analysts ramp up gold forecasts",
        "2026-02-18 CNBC: Fed minutes (Split on rates)",
        "2026-01-30 GlobalTimes: China tech stocks rally (DeepSeek)",
        "2026-02-26 Market Data (Self-verified)"
    ]
}

def load_json():
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_report():
    data = load_json()
    alloc_summary = data['allocation_summary']
    plan = data['investment_plan']
    
    # Current Allocations (Target) from JSON
    # Note: JSON "ratio" is the *Target* from the strategy file.
    # But the prompt asks for "Current %" vs "Suggested %".
    # Usually "Current %" in this context means the *previous* target (from JSON),
    # and "Suggested %" is the *new* target I am proposing.
    
    # 1. Top SIP Changes
    # Strategy: 
    # - Bonds: +5% (Defensive) -> Increase Govt Bonds
    # - US: +5% (AI/Tech) -> Increase Tech/Health
    # - China: -5% (Profit taking) -> Reduce Chips/Auto? Or broad index?
    # - Futures: -5% (High volatility) -> Reduce Gold/Silver
    
    top_changes = [
        "* 债券/国债：增持 25%→30% — 利率维持高位(3.75%)，锁定高息防御",
        "* 美股/科技：增持 20%→25% — AI及科技股虽有泡沫担忧但增长强劲",
        "* 中股/各行业：减持 35%→30% — 近期科技反弹后适度止盈，规避波动",
        "* 期货/黄金：减持 20%→15% — 金价$5000+历史高位，获利了结降低波幅",
        "* 创新药：维持 — 中美医药板块估值均在低位，维持定投积累"
    ]
    
    # 2. Category Allocation
    # Bond: 0.25 -> 0.30
    # China: 0.35 -> 0.30
    # Futures: 0.20 -> 0.15
    # US: 0.20 -> 0.25
    
    cat_rows = []
    cat_map = {
        "债券": {"curr": 0.25, "new": 0.30, "reason": "美联储暂停降息，利率高位震荡，防御配置"},
        "中股": {"curr": 0.35, "new": 0.30, "reason": "反弹后部分止盈，等待政策进一步验证"},
        "期货": {"curr": 0.20, "new": 0.15, "reason": "金价新高后波动加剧，降低仓位避险"},
        "美股": {"curr": 0.20, "new": 0.25, "reason": "AI产业趋势未变，财报季预期向好"}
    }
    
    for cat in ["债券", "中股", "期货", "美股"]:
        info = cat_map[cat]
        diff = info['new'] - info['curr']
        sign = "+" if diff > 0 else "" if diff == 0 else ""
        action = "增配" if diff > 0 else "减配" if diff < 0 else "不变"
        cat_rows.append(f"| {cat} | {info['curr']*100:.1f}% | {info['new']*100:.1f}% | {sign}{diff*100:.1f}% | {action} | {info['reason']} |")

    # 3. Per-Item Actions
    # Need to distribute the Category changes to Items.
    # Bonds (30%): 2 items. Split equally? Or keep current ratio?
    # JSON: Bond ratio 0.25. Item1 0.5, Item2 0.5. -> Item1 global = 0.125.
    # New Bond 0.30. Item1 0.5 -> 0.15.
    
    item_rows = []
    
    # Helper to find items by category
    items_by_cat = {}
    for item in plan:
        c = item['category']
        items_by_cat.setdefault(c, []).append(item)
        
    for cat in ["债券", "中股", "期货", "美股"]:
        cat_items = items_by_cat.get(cat, [])
        total_ratio_in_cat = sum(x['ratio_in_category'] for x in cat_items)
        
        # New category target
        cat_target_new = cat_map[cat]['new']
        cat_target_curr = cat_map[cat]['curr']
        
        for item in cat_items:
            # Normalized weight within category
            w = item['ratio_in_category'] / total_ratio_in_cat if total_ratio_in_cat else 0
            
            curr_global = cat_target_curr * w
            new_global = cat_target_new * w
            
            diff = new_global - curr_global
            sign = "+" if diff > 1e-4 else "" if diff < -1e-4 else ""
            action = "增持" if diff > 1e-4 else "减持" if diff < -1e-4 else "不变"
            
            # Specific reasons
            reason = "跟随大类调整"
            if cat == "债券":
                reason = "美债收益率高位，增加配置"
            elif cat == "期货" and "黄金" in item['fund_name']:
                reason = "金价高位止盈"
            elif cat == "中股" and "芯片" in item['fund_name']:
                reason = "科技反弹后减仓"
            elif cat == "美股" and "科技" in item['sub_category']:
                reason = "看好AI长期增长"
            
            row = f"| {item['category']} | {item['sub_category']} | {item['fund_name']} | {item['day_of_week']} | {curr_global*100:.2f}% | {new_global*100:.2f}% | {sign}{diff*100:.2f}% | {action} | {reason} |"
            item_rows.append(row)

    # 6. Holdings Notes
    # Filter non-investment holdings
    holdings = data.get('non_investment_holdings', [])
    holdings_notes = []
    for h in holdings:
        name = h['fund_name']
        if "余额宝" in name:
            holdings_notes.append(f"* {name}：维持 — 现金管理工具，保持流动性")
        elif "芯片" in name:
            holdings_notes.append(f"* {name}：减持 — 随科技股反弹适度止盈")
        elif "北证" in name:
            holdings_notes.append(f"* {name}：观察 — 波动较大，暂不动")
        elif "创新药" in name:
             holdings_notes.append(f"* {name}：持有 — 估值低位，等待修复")
    
    # Limit to 5
    holdings_notes = holdings_notes[:5]

    # Generate Markdown
    md = f"""### 0. 输入回显 (Input Echo)
* 日期：{TODAY}
* 定投检视周期：每月
* 风险偏好：稳健
* 定投大类目标：债券 25%, 中股 35%, 期货 20%, 美股 20%
* 关键假设：{MODEL_NAME} = {MODEL_NAME}
* 产物路径：
  - 投资策略.json：`报告/{TODAY}/投资策略.json`
  - 投资简报_{MODEL_NAME}.md：`报告/{TODAY}/简报/投资简报_{MODEL_NAME}.md`

### 1. 定投增减要点（最多 5 条）(Top SIP Changes)
{chr(10).join(top_changes)}

### 2. 大板块比例调整建议（必须）(Category Allocation Changes)
| 大板块 | 当前% | 建议% | 变动 | 建议（增配/减配/不变） | 简短理由 |
|---|---:|---:|---:|---|---|
{chr(10).join(cat_rows)}

### 3. 定投计划逐项建议（全量，逐项表格）(Per-Item Actions)
| 大板块 | 小板块 | 标的 | 定投日 | 当前% | 建议% | 变动 | 建议（增持/减持/不变） | 简短理由 |
|---|---|---|---|---:|---:|---:|---|---|
{chr(10).join(item_rows)}

### 4. 新的定投方向建议（如有）(New SIP Directions)
| 行业/主题 | 建议定投比例 | 口径 | 简短理由 |
|---|---:|---|---|
| 商业航天 | 5% | 占全组合 | 2026年产业爆发期，低位布局 |
| 机器人 | 2% | 占全组合 | AI具身智能落地，长期潜力 |

### 5. 执行指令（下一周期）(Next Actions)
* 定投：维持（按新比例执行）
* 资金池：若美股回撤>10%或中股回踩3200点，启动单笔加仓
* 风险控制：单日跌幅超3%暂停当日定投；黄金跌破$4500止损观察

### 6. 现有持仓建议（最多 5 点）(Holdings Notes)
{chr(10).join(holdings_notes)}

### 7. 数据来源 (Sources)
{chr(10).join([f"* {s}" for s in WEB_DATA['Sources']])}
"""

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"Generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_report()
