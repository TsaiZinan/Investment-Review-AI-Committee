import json

TODAY = '2026-04-02'
MODEL_NAME = 'Qwen3.5-Plus'
report_file = f'报告/{TODAY}/{TODAY}_{MODEL_NAME}_投资建议.md'
json_file = f'报告/{TODAY}/投资策略.json'

with open(report_file, 'r', encoding='utf-8') as f:
    report_text = f.read()

with open(json_file, 'r', encoding='utf-8') as f:
    strategy = json.load(f)

fund_names = []
for x in strategy.get('investment_plan', []) or []:
    n = (x.get('fund_name') or '').strip()
    if n:
        fund_names.append(n)
for x in strategy.get('non_investment_holdings', []) or []:
    n = (x.get('fund_name') or '').strip()
    if n:
        fund_names.append(n)

fund_missing = []
report_text_no_spaces = report_text.replace(' ', '')
for n in fund_names:
    if n not in report_text and n.replace(' ', '') not in report_text_no_spaces:
        fund_missing.append(n)

print(f'Total funds: {len(fund_names)}')
print(f'Missing: {len(fund_missing)}')
if fund_missing:
    for f in fund_missing:
        print(f'  - {f}')
        print(f'    In report: {f in report_text}')
        print(f'    No spaces: {f.replace(" ", "") in report_text_no_spaces}')
else:
    print('✓ All funds covered!')
