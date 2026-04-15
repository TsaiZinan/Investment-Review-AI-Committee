import json
from pathlib import Path

report_path = Path("报告/2026-03-16/2026-03-16_Germini-3-Pro_投资建议.md")
json_path = Path("报告/2026-03-16/投资策略.json")

report_text = report_path.read_text(encoding="utf-8")
strategy = json.loads(json_path.read_text(encoding="utf-8"))

# Find the exact strings in JSON
name1 = next(x["fund_name"] for x in strategy["non_investment_holdings"] if "富国上证" in x["fund_name"])
name2 = next(x["fund_name"] for x in strategy["non_investment_holdings"] if "广发创新药" in x["fund_name"] and "QDII" not in x["fund_name"])

# Replace manually typed names with JSON names to ensure byte-for-byte match
# I suspect my manual typing might have different whitespace or encoding issue?
# Or maybe the file on disk has different encoding?

print(f"JSON Name 1: '{name1}'")
print(f"JSON Name 2: '{name2}'")

new_text = report_text.replace("富国上证综指联接C", name1).replace("广发创新药产业ETF联接C", name2)

if new_text != report_text:
    report_path.write_text(new_text, encoding="utf-8")
    print("Updated report with exact JSON strings.")
else:
    print("No change needed or strings match already (which is weird if validation failed).")
