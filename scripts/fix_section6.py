# Read the file
with open('报告/2026-03-25/2026-03-25_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace section 6 to include all 7 non-investment holdings
old_section = """### 6. 现有持仓建议（最多 5 点）(Holdings Notes)
* 天弘余额宝货币市场基金：维持 — 现金管理工具，保持流动性
* 富国上证综指联接 C：持有 — 大盘指数，稳定配置
* 华夏国证半导体芯片 ETF 联接 C：持有 — 芯片估值较高，但长期看好
* 易方达北证 50 指数 C：观察 — 波动较大，暂不动
* 广发北证 50 成份指数 C：观察 — 波动较大，暂不动"""

new_section = """### 6. 现有持仓建议（非定投全量）(Holdings Notes)
* 天弘余额宝货币市场基金：维持 — 现金管理工具，保持流动性
* 富国上证综指联接 C：持有 — 大盘指数，稳定配置
* 华夏国证半导体芯片 ETF 联接 C：持有 — 芯片估值较高，但长期看好
* 易方达北证 50 指数 C：观察 — 波动较大，暂不动
* 广发北证 50 成份指数 C：观察 — 波动较大，暂不动
* 广发创新药产业 ETF 联接 C：持有 — 估值低位，等待修复
* 广发港股创新药 ETF 联接 (QDII)C：持有 — 估值低位，等待修复"""

new_content = content.replace(old_section, new_section)

# Write back
with open('报告/2026-03-25/2026-03-25_Qwen3.5-Plus_投资建议.md', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("File updated successfully")

# Verify
with open('报告/2026-03-25/2026-03-25_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    content = f.read()
    
funds = [
    '天弘余额宝货币市场基金',
    '富国上证综指联接 C',
    '华夏国证半导体芯片 ETF 联接 C',
    '易方达北证 50 指数 C',
    '广发北证 50 成份指数 C',
    '广发创新药产业 ETF 联接 C',
    '广发港股创新药 ETF 联接 (QDII)C'
]

for fund in funds:
    print(f"{fund} in content: {fund in content}")