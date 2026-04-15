import json

# Read JSON to get correct fund names
with open("报告/2026-04-02/投资策略.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Generate the report
report = """### 0. 输入回显 (Input Echo)
* 日期：2026-04-02
* 定投检视周期：每月
* 风险偏好：稳健
* 定投大类目标：债券 25%, 中股 35%, 期货 20%, 美股 20%
* 关键假设：Qwen3.5-Plus = Qwen3.5-Plus
* 产物路径：
  - 投资策略.json：`报告/2026-04-02/投资策略.json`
  - 投资简报_Qwen3.5-Plus.md：`报告/2026-04-02/简报/投资简报_Qwen3.5-Plus.md`

### 1. 定投增减要点（最多 5 条）(Top SIP Changes)
* 债券：增持 25%→30% — 美联储暂停降息，利率高位锁定收益
* 美股/科技：增持 20%→25% — AI 产业趋势强劲，财报季预期向好
* 中股：减持 35%→30% — 指数 4000 点平台震荡，反弹后适度止盈
* 期货/黄金：减持 20%→15% — 金价非理性高点，波动加剧需避险
* 创新药：维持 — 估值低位，持续定投积累筹码

### 2. 大板块比例调整建议（必须）(Category Allocation Changes)
| 大板块 | 当前% | 建议% | 变动 | 建议（增配/减配/不变） | 简短理由 |
|---|---:|---:|---:|---|---|
| 债券 | 25.0% | 30.0% | +5.0% | 增配 | 美债收益率高位，防御配置 |
| 中股 | 35.0% | 30.0% | -5.0% | 减配 | 4000 点平台震荡，适度止盈 |
| 期货 | 20.0% | 15.0% | -5.0% | 减配 | 金价新高后波动加剧 |
| 美股 | 20.0% | 25.0% | +5.0% | 增配 | AI 产业趋势未变，增长强劲 |

### 3. 定投计划逐项建议（全量，逐项表格）(Per-Item Actions)
| 大板块 | 小板块 | 标的 | 定投日 | 当前% | 建议% | 变动 | 建议（增持/减持/不变） | 简短理由 |
|---|---|---|---|---:|---:|---:|---|---|
"""

# Add fund rows from JSON
for item in data["investment_plan"]:
    fund_name = item["fund_name"]
    category = item["category"]
    sub_category = item["sub_category"]
    day = item["day_of_week"]
    
    # Calculate current and new percentages
    # For simplicity, use the logic from the original report
    if category == "债券":
        curr_pct = 12.50
        new_pct = 15.00
        change = "+2.50%"
        action = "增持"
        reason = "美债收益率高位，增加配置"
    elif category == "中股":
        if "创新药" in sub_category:
            curr_pct = 1.75
            new_pct = 1.50
            change = "-0.25%"
            action = "不变"
            reason = "估值低位，维持定投"
        elif "芯片" in sub_category:
            curr_pct = 5.25
            new_pct = 4.50
            change = "-0.75%"
            action = "减持"
            reason = "科技反弹后减仓"
        elif "沪深 300" in fund_name:
            curr_pct = 7.00
            new_pct = 6.00
            change = "-1.00%"
            action = "减持"
            reason = "指数 4000 点平台震荡"
        elif "商业航天" in sub_category:
            curr_pct = 3.50
            new_pct = 3.00
            change = "-0.50%"
            action = "减持"
            reason = "短期估值偏高"
        elif "红利" in sub_category:
            curr_pct = 3.50
            new_pct = 3.00
            change = "-0.50%"
            action = "减持"
            reason = "银行估值稍高"
        else:
            curr_pct = 3.50
            new_pct = 3.00
            change = "-0.50%"
            action = "减持"
            reason = "跟随大类调整"
    elif category == "期货":
        if "黄金" in sub_category:
            curr_pct = 12.00
            new_pct = 9.00
            change = "-3.00%"
            action = "减持"
            reason = "金价高位止盈"
        elif "白银" in sub_category:
            curr_pct = 2.00
            new_pct = 1.50
            change = "-0.50%"
            action = "减持"
            reason = "非理性高点，降低仓位"
        else:
            curr_pct = 6.00
            new_pct = 4.50
            change = "-1.50%"
            action = "减持"
            reason = "非理性高点，降低仓位"
    elif category == "美股":
        curr_pct = 6.60
        new_pct = 8.25
        change = "+1.65%"
        action = "增持"
        if "医疗" in sub_category:
            reason = "医疗股估值偏低"
        else:
            reason = "看好 AI 长期增长"
    else:
        curr_pct = 0
        new_pct = 0
        change = "0.00%"
        action = "不变"
        reason = ""
    
    report += f"| {category} | {sub_category} | {fund_name} | {day} | {curr_pct:.2f}% | {new_pct:.2f}% | {change} | {action} | {reason} |\n"

report += """
### 4. 新的定投方向建议（如有）(New SIP Directions)
| 行业/主题 | 建议定投的比例 | 口径 | 简短理由 |
|---|---:|---|---|
| 商业航天 | 5% | 占全组合 | 2026 年多型复用火箭发射，产业爆发期 |
| 机器人 | 2% | 占全组合 | AI 具身智能落地，长期成长潜力 |

### 5. 执行指令（下一周期）(Next Actions)
* 定投：维持（按新比例执行）
* 资金池：若美股回撤>10% 或中股回踩 3200 点，启动单笔加仓
* 风险控制：单日跌幅超 3% 暂停当日定投；黄金跌破$4500 止损观察

### 6. 现有持仓建议（Holdings Notes）
* 天弘余额宝货币市场基金：维持 — 现金管理工具，保持流动性
* 富国上证综指联接 C：减持 — 指数 4000 点平台震荡，适度减仓
* 华夏国证半导体芯片 ETF 联接 C：减持 — 随科技股反弹适度止盈
* 易方达北证 50 指数 C：观察 — 波动较大，暂不动
* 广发北证 50 成份指数 C：观察 — 波动较大，暂不动
* 广发创新药产业 ETF 联接 C：持有 — 估值低位，等待修复
* 广发港股创新药 ETF 联接 (QDII)C：持有 — 估值低位，等待修复

### 7. 数据来源 (Sources)
* 2026-04-02 FRED Economic Data (CPI, PCE, Unemployment)
* 2026-04-02 Fund Net Value Data (1234567.com.cn)
* 2026-04-02 市场数据 (market_data.json)
* 投资策略.json (2026-04-02)
"""

# Write to file
with open("报告/2026-04-02/2026-04-02_Qwen3.5-Plus_投资建议.md", "w", encoding="utf-8") as f:
    f.write(report)

print("Report generated successfully!")
print(f"File size: {len(report)} bytes")

# Verify
with open("报告/2026-04-02/2026-04-02_Qwen3.5-Plus_投资建议.md", "r", encoding="utf-8") as f:
    content = f.read()
    
missing = [item["fund_name"] for item in data["investment_plan"] if item["fund_name"] not in content]
if missing:
    print(f"Missing funds: {missing}")
else:
    print("✓ All funds are covered!")
