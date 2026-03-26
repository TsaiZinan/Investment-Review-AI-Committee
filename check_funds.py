import json

# Load fund names from JSON
with open('报告/2026-03-21/投资策略.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

fund_names = []
for item in data['investment_plan']:
    n = item.get('fund_name', '').strip()
    if n:
        fund_names.append(n)
for item in data['non_investment_holdings']:
    n = item.get('fund_name', '').strip()
    if n:
        fund_names.append(n)

# Load report
with open('报告/2026-03-21/2026-03-21_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    report_text = f.read()

# Remove spaces from report for comparison
report_text_no_spaces = report_text.replace(' ', '')

# Check each fund name
missing = []
for fund_name in fund_names:
    # Try exact match first
    if fund_name in report_text:
        print(f'FOUND (exact): {fund_name}')
    # Try match without spaces
    elif fund_name.replace(' ', '') in report_text_no_spaces:
        print(f'FOUND (no spaces): {fund_name}')
    else:
        missing.append(fund_name)
        print(f'MISSING: {fund_name}')

print(f'\nTotal missing: {len(missing)}')
