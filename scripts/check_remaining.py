import json
import re

with open('报告/2026-03-06/投资策略.json', 'r', encoding='utf-8') as f:
    strategy = json.load(f)
with open('报告/2026-03-06/2026-03-06_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    report = f.read()

# Check specific funds
targets = [
    '广发港股创新药 ETF 联接 (QDII)A',
    '广发纳斯达克 100ETF 联接 (QDII)C',
    '广发港股创新药 ETF 联接 (QDII)C',
]

for target in targets:
    print(f'\nTarget: {repr(target)}')
    print(f'Found: {target in report}')
    
    # Search in report
    matches = re.findall(r'.*广发.*创新药.*', report)
    for m in matches[:3]:
        print(f'  Match: {repr(m.strip())}')

# Check JSON fund name
json_fund = None
for x in strategy['investment_plan']:
    if '港股创新药' in x.get('fund_name', ''):
        json_fund = x['fund_name']
        break
        
print(f'\nJSON fund: {repr(json_fund)}')
print(f'JSON fund bytes: {[hex(ord(c)) for c in json_fund]}')

# Find in report
lines = report.split('\n')
for i, line in enumerate(lines):
    if '港股创新药' in line:
        parts = line.split('|')
        if len(parts) > 3:
            report_fund = parts[3].strip()
            print(f'\nReport fund: {repr(report_fund)}')
            print(f'Report fund bytes: {[hex(ord(c)) for c in report_fund]}')
