import json

# Read JSON to get correct fund names
with open("报告/2026-04-02/投资策略.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    fund_names = [item["fund_name"] for item in data["investment_plan"]]

# Read report
with open("报告/2026-04-02/2026-04-02_Qwen3.5-Plus_投资建议.md", "r", encoding="utf-8") as f:
    content = f.read()

# Fund names with spaces (as they appear in my report)
funds_with_spaces = [
    "上银中债 5-10 年国开行债券指数 A",
    "南方中债 7-10 年国开行债券指数 A",
    "广发汽车指数 A",
    "富国中证消费电子主题 ETF 联接 A",
    "广发沪深 300ETF 联接 C",
    "国泰中证光伏产业 ETF 联接 A",
    "富国中证芯片产业 ETF 联接 A",
    "永赢高端装备智选混合 A",
    "广发创新药产业 ETF 联接 A",
    "广发港股创新药 ETF 联接 (QDII)A",
    "华泰柏瑞中证红利低波动 ETF 联接 A",
    "南方中证全指房地产 ETF 联接 A",
    "南方中证申万有色金属 ETF 联接 A",
    "国投瑞银白银期货 (LOF)C",
    "华安黄金",
    "广发全球精选股票 (QDII)A",
    "广发纳斯达克 100ETF 联接 (QDII)C",
    "广发全球医疗保健指数 (QDII)A"
]

# Replace each fund name
for i, fund in enumerate(funds_with_spaces):
    correct_name = fund_names[i]
    if fund in content:
        content = content.replace(fund, correct_name)
        print(f"Replaced: '{fund}' -> '{correct_name}'")
    else:
        print(f"Not found: '{fund}'")

# Write back
with open("报告/2026-04-02/2026-04-02_Qwen3.5-Plus_投资建议.md", "w", encoding="utf-8") as f:
    f.write(content)

print("\nDone! File updated.")
