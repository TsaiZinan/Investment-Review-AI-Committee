import json

# Load strategy
with open('报告/2026-03-25/投资策略.json', 'r', encoding='utf-8') as f:
    strategy = json.load(f)

# Load report
with open('报告/2026-03-25/2026-03-25_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    report = f.read()

report_no_spaces = report.replace(' ', '')

# Check fund names
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
    if n not in report and n.replace(' ', '') not in report_no_spaces:
        missing.append(n)
        print(f"MISSING: {repr(n)}")
    else:
        print(f"OK: {repr(n)}")

print(f"\nTotal: {len(fund_names)}, Missing: {len(missing)}")
