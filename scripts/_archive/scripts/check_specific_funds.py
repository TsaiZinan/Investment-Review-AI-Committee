import json

# Read JSON
with open("报告/2026-04-02/投资策略.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    funds_json = [item["fund_name"] for item in data["investment_plan"]]

# Read Report
with open("报告/2026-04-02/2026-04-02_Qwen3.5-Plus_投资建议.md", "r", encoding="utf-8") as f:
    content = f.read()

# Check specific funds
target_funds = [
    "国投瑞银白银期货 (LOF)C",
    "华安黄金",
    "广发全球精选股票 (QDII)A",
    "广发纳斯达克 100ETF 联接 (QDII)C",
    "广发全球医疗保健指数 (QDII)A"
]

print("Checking funds from JSON:")
for fund in target_funds:
    in_json = fund in funds_json
    in_report = fund in content
    print(f"  {fund}: JSON={in_json}, Report={in_report}")
    
    # Try to find in report with regex
    import re
    # Remove all spaces and search
    fund_no_space = fund.replace(" ", "")
    if fund_no_space != fund:
        found_no_space = fund_no_space in content
        print(f"    -> Without spaces '{fund_no_space}': {found_no_space}")
