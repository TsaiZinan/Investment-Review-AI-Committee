import json

with open('报告/2026-03-06/投资策略.json', 'r', encoding='utf-8') as f:
    strategy = json.load(f)
with open('报告/2026-03-06/2026-03-06_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    report = f.read()

# Check first fund
json_fund = strategy['investment_plan'][0]['fund_name']
print(f'JSON fund: {repr(json_fund)}')
print(f'JSON fund bytes: {[hex(ord(c)) for c in json_fund]}')

# Find the line in report with 上银
lines = report.split('\n')
for i, line in enumerate(lines):
    if '上银' in line:
        report_fund = line.split('|')[3].strip()
        print(f'\nReport fund: {repr(report_fund)}')
        print(f'Report fund bytes: {[hex(ord(c)) for c in report_fund]}')
        break
