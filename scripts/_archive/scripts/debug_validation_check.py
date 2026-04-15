import json
from pathlib import Path

report_path = Path("报告/2026-03-16/2026-03-16_Germini-3-Pro_投资建议.md")
json_path = Path("报告/2026-03-16/投资策略.json")

report_text = report_path.read_text(encoding="utf-8")
strategy = json.loads(json_path.read_text(encoding="utf-8"))

missing = []
for x in strategy.get("non_investment_holdings", []):
    n = (x.get("fund_name") or "").strip()
    if n:
        if n not in report_text:
            print(f"Missing: '{n}'")
            print(f"In text? {n in report_text}")
            missing.append(n)
        else:
            print(f"Found: '{n}'")

if not missing:
    print("All found.")
