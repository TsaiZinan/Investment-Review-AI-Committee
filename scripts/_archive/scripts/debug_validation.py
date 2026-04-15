
import json
from pathlib import Path

report_file = Path("/Users/cai/SynologyDrive/Project/#ProjectLife-000000-理财/报告/2026-03-13/2026-03-13_Gemini-3-Pro_投资建议.md")
json_file = Path("/Users/cai/SynologyDrive/Project/#ProjectLife-000000-理财/报告/2026-03-13/投资策略.json")

report_text = report_file.read_text(encoding="utf-8", errors="replace")
strategy = json.loads(json_file.read_text(encoding="utf-8"))

fund_names = []
for x in strategy.get("investment_plan", []) or []:
    n = (x.get("fund_name") or "").strip()
    if n:
        fund_names.append(n)
for x in strategy.get("non_investment_holdings", []) or []:
    n = (x.get("fund_name") or "").strip()
    if n:
        fund_names.append(n)

missing = []
for n in fund_names:
    if n not in report_text:
        missing.append(n)
        print(f"Missing: '{n}'")
    else:
        print(f"Found: '{n}'")

print(f"Total missing: {len(missing)}")
