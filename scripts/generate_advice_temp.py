
import json

data = {
    "allocation_summary": [
        {"category": "债券", "current_ratio": 0.25, "suggested_ratio": 0.30, "reason": "美债收益率高位，避险+票息"},
        {"category": "中股", "current_ratio": 0.35, "suggested_ratio": 0.30, "reason": "持仓超配，宏观复苏待验证"},
        {"category": "期货", "current_ratio": 0.20, "suggested_ratio": 0.15, "reason": "黄金高位波动加剧，适度止盈"},
        {"category": "美股", "current_ratio": 0.20, "suggested_ratio": 0.25, "reason": "补足低配缺口，长期看好科技/医疗"}
    ],
    "investment_plan": [
        # 债券 (30%)
        {"fund_name": "上银中债5-10年国开行债券指数A", "category": "债券", "sub": "国债", "day": "周三", "ratio_in_cat": 0.5, "reason": "利率高位锁定收益"},
        {"fund_name": "南方中债7-10年国开行债券指数A", "category": "债券", "sub": "国债", "day": "周四", "ratio_in_cat": 0.5, "reason": "利率高位锁定收益"},
        
        # 中股 (30%) - Adjusted internal weights
        {"fund_name": "广发汽车指数A", "category": "中股", "sub": "汽车", "day": "周一", "ratio_in_cat": 0.1, "reason": "出海逻辑仍在"},
        {"fund_name": "富国中证消费电子主题ETF联接A", "category": "中股", "sub": "消费电子", "day": "周二", "ratio_in_cat": 0.1, "reason": "消费复苏缓慢"},
        {"fund_name": "广发沪深300ETF联接C", "category": "中股", "sub": "中证", "day": "周四", "ratio_in_cat": 0.2, "reason": "核心资产底仓"},
        {"fund_name": "国泰中证光伏产业ETF联接A", "category": "中股", "sub": "光伏", "day": "周三", "ratio_in_cat": 0.1, "reason": "估值低位磨底"},
        {"fund_name": "富国中证芯片产业ETF联接A", "category": "中股", "sub": "芯片", "day": "周四", "ratio_in_cat": 0.1, "reason": "估值偏高，减配"},
        {"fund_name": "永赢高端装备智选混合A", "category": "中股", "sub": "商业航天", "day": "周四", "ratio_in_cat": 0.1, "reason": "高成长但高波动"},
        {"fund_name": "广发创新药产业ETF联接A", "category": "中股", "sub": "创新药", "day": "周三", "ratio_in_cat": 0.05, "reason": "长坡厚雪"},
        {"fund_name": "广发港股创新药ETF联接(QDII)A", "category": "中股", "sub": "创新药", "day": "周二", "ratio_in_cat": 0.05, "reason": "低估值弹性"},
        {"fund_name": "华泰柏瑞中证红利低波动ETF联接A", "category": "中股", "sub": "红利低波", "day": "周三", "ratio_in_cat": 0.15, "reason": "防御属性增强"}, # Increased slightly for defense
        {"fund_name": "南方中证全指房地产ETF联接A", "category": "中股", "sub": "房地产", "day": "周一", "ratio_in_cat": 0.05, "reason": "政策博弈"},

        # 期货 (15%)
        {"fund_name": "南方中证申万有色金属ETF联接A", "category": "期货", "sub": "有色", "day": "周二", "ratio_in_cat": 0.3, "reason": "顺周期需求"},
        {"fund_name": "国投瑞银白银期货(LOF)C", "category": "期货", "sub": "白银", "day": "周二", "ratio_in_cat": 0.1, "reason": "跟随黄金波动"},
        {"fund_name": "华安黄金", "category": "期货", "sub": "黄金", "day": "周一", "ratio_in_cat": 0.6, "reason": "高位回调风险"},

        # 美股 (25%)
        {"fund_name": "广发全球精选股票(QDII)A", "category": "美股", "sub": "科技", "day": "周二", "ratio_in_cat": 0.33, "reason": "AI龙头强者恒强"},
        {"fund_name": "广发纳斯达克100ETF联接(QDII)C", "category": "美股", "sub": "科技", "day": "周三", "ratio_in_cat": 0.33, "reason": "美股核心资产"},
        {"fund_name": "广发全球医疗保健指数(QDII)A", "category": "美股", "sub": "医疗保健", "day": "周一", "ratio_in_cat": 0.34, "reason": "防御性+创新"},
    ]
}

# Generate Markdown
md = []
md.append("# 2026-02-09 Germini-3-Pro 投资建议\n")

# 0. Input Echo
md.append("### 0. 输入回显 (Input Echo)")
md.append("* 日期：2026-02-09")
md.append("* 定投检视周期：每月")
md.append("* 风险偏好：稳健")
md.append("* 定投大类目标：债券 25% / 中股 35% / 期货 20% / 美股 20% (合计 100%)")
md.append("* 关键假设：基于 2026-02-09 联网数据分析")
md.append("* 产物路径：")
md.append("  - 投资策略.json：`报告/2026-02-09/投资策略.json`")
md.append("  - 投资简报_Germini-3-Pro.md：`报告/2026-02-09/简报/投资简报_Germini-3-Pro.md`\n")

# 1. Top SIP Changes
md.append("### 1. 定投增减要点（最多 5 条）(Top SIP Changes)")
md.append("* 债券：增持 25%→30% — 美债收益率4.21%高位，配置价值凸显")
md.append("* 中股：减持 35%→30% — 现有持仓超配严重，且宏观不确定性")
md.append("* 黄金：减持 12%→9% — 波动率GVZ 35.53过高，止盈避险")
md.append("* 美股：增持 20%→25% — 现有持仓严重低配，科技股虽有泡沫风险但需补仓")
md.append("* 芯片：减持 5.25%→3% — 估值较高，自主可控预期已部分兑现\n")

# 2. Category Allocation Changes
md.append("### 2. 大板块比例调整建议（必须）(Category Allocation Changes)")
md.append("| 大板块 | 当前% | 建议% | 变动 | 建议（增配/减配/不变） | 简短理由 |")
md.append("|---|---:|---:|---:|---|---|")
for item in data["allocation_summary"]:
    change = item["suggested_ratio"] - item["current_ratio"]
    action = "增配" if change > 0 else "减配" if change < 0 else "不变"
    md.append(f"| {item['category']} | {item['current_ratio']:.2%} | {item['suggested_ratio']:.2%} | {change:+.2%} | {action} | {item['reason']} |")
md.append("")

# 3. Per-Item Actions
md.append("### 3. 定投计划逐项建议（全量，逐项表格）(Per-Item Actions)")
md.append("| 大板块 | 小板块 | 标的 | 定投日 | 当前% | 建议% | 变动 | 建议（增持/减持/不变） | 简短理由 |")
md.append("|---|---|---|---|---:|---:|---:|---|---|")

current_alloc_map = {x['category']: x['current_ratio'] for x in data['allocation_summary']}
suggest_alloc_map = {x['category']: x['suggested_ratio'] for x in data['allocation_summary']}

# Note: In the real strategy file, ratio_in_category is fixed. 
# Here I hardcoded ratios in `investment_plan` list above to sum to 1.0 per category roughly.
# Let's double check sum.
# Bond: 0.5+0.5=1.0
# China: 0.1+0.1+0.2+0.1+0.1+0.1+0.05+0.05+0.15+0.05 = 1.0
# Futures: 0.3+0.1+0.6=1.0
# US: 0.33+0.33+0.34=1.0
# OK.

# Also need the "Current %" from the JSON file logic: allocation_summary[].ratio * investment_plan[].ratio_in_category (OLD)
# Wait, the `investment_plan` list above has `ratio_in_cat` which is my NEW proposed internal ratio? 
# Or should I keep the OLD internal ratio and just scale by category?
# The prompt says: "In same category, if structure needs adjustment, prioritize re-distribution via 'Suggested %'".
# So I can change `ratio_in_category`.
# But for "Current %", I must use the OLD ratios.
# I need to know the OLD ratios from `投资策略.json`.
# Bond: 0.5, 0.5
# China: Auto 0.1, Cons 0.13, CSI 0.2, PV 0.09, Chips 0.15, Space 0.1, DrugA 0.05, DrugH 0.05, Div 0.1, RE 0.03. (Sum=1.0)
# Futures: Non-ferrous 0.3, Silver 0.1, Gold 0.6
# US: Tech 0.33, Tech 0.33, Med 0.33

old_ratios = {
    "上银中债5-10年国开行债券指数A": 0.5,
    "南方中债7-10年国开行债券指数A": 0.5,
    "广发汽车指数A": 0.1,
    "富国中证消费电子主题ETF联接A": 0.13,
    "广发沪深300ETF联接C": 0.2,
    "国泰中证光伏产业ETF联接A": 0.09,
    "富国中证芯片产业ETF联接A": 0.15,
    "永赢高端装备智选混合A": 0.1,
    "广发创新药产业ETF联接A": 0.05,
    "广发港股创新药ETF联接(QDII)A": 0.05,
    "华泰柏瑞中证红利低波动ETF联接A": 0.1,
    "南方中证全指房地产ETF联接A": 0.03,
    "南方中证申万有色金属ETF联接A": 0.3,
    "国投瑞银白银期货(LOF)C": 0.1,
    "华安黄金": 0.6,
    "广发全球精选股票(QDII)A": 0.33,
    "广发纳斯达克100ETF联接(QDII)C": 0.33,
    "广发全球医疗保健指数(QDII)A": 0.33
}

for item in data["investment_plan"]:
    cat = item["category"]
    fund = item["fund_name"]
    
    current_cat_ratio = current_alloc_map[cat]
    old_internal_ratio = old_ratios.get(fund, 0)
    current_total_ratio = current_cat_ratio * old_internal_ratio
    
    suggest_cat_ratio = suggest_alloc_map[cat]
    new_internal_ratio = item["ratio_in_cat"]
    suggest_total_ratio = suggest_cat_ratio * new_internal_ratio
    
    change = suggest_total_ratio - current_total_ratio
    action = "增持" if change > 0 else "减持" if change < 0 else "不变"
    
    md.append(f"| {cat} | {item['sub']} | {fund} | {item['day']} | {current_total_ratio:.2%} | {suggest_total_ratio:.2%} | {change:+.2%} | {action} | {item['reason']} |")

md.append("")

# 4. New SIP Directions
md.append("### 4. 新的定投方向建议（如有）(New SIP Directions)")
md.append("| 行业/主题 | 建议定投比例 | 口径 | 简短理由 |")
md.append("|---|---:|---|---|")
md.append("| 低空经济 | 1% | 占全组合 | 政策扶持，万亿市场启动 |")
md.append("")

# 5. Next Actions
md.append("### 5. 执行指令（下一周期）(Next Actions)")
md.append("* 定投：债券加倍，中股/期货缩减，美股加大定投")
md.append("* 资金池：若 VIX > 40 买入黄金；若 沪深300 < 3500 加仓中股")
md.append("* 风险控制：期货单日跌幅 > 5% 暂停定投一周")
md.append("")

# 6. Holdings Notes
md.append("### 6. 现有持仓建议（最多 5 点）(Holdings Notes)")
md.append("* 中股非定投（芯片）：减持 — 收益若超10%止盈，置换为美股定投")
md.append("* 货币基金：减持 — 余额宝资金逐步转入债券/美股定投")
md.append("* 港股创新药：持有 — 等待估值修复")
md.append("")

# 7. Sources
md.append("### 7. 数据来源 (Sources)")
md.append("* FRED DGS10 10-Year Treasury Yield: 4.21% (2026-02-05)")
md.append("* FRED GVZ Gold Volatility Index: 35.53 (2026-02-05)")
md.append("* FRED DGS2 2-Year Treasury Yield: 3.47% (2026-02-05)")
md.append("* FRED T10YIE 10-Year Breakeven Inflation: 2.34% (2026-02-06)")
md.append("* FRED DTWEXBGS Trade Weighted US Dollar Index: 117.8996 (2026-01-30)")

print("\n".join(md))
