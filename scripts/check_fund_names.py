import json
import re

with open('报告/2026-03-18/投资策略.json', 'r', encoding='utf-8') as f:
    strategy = json.load(f)
with open('报告/2026-03-18/2026-03-18_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    report = f.read()

fund_names = []
for x in strategy.get('investment_plan', []):
    n = (x.get('fund_name') or '').strip()
    if n:
        fund_names.append(n)
for x in strategy.get('non_investment_holdings', []):
    n = (x.get('fund_name') or '').strip()
    if n:
        fund_names.append(n)

print('Checking fund names:')
missing = []
for name in fund_names:
    if name in report:
        print(f'✓ Found: {name}')
    else:
        print(f'✗ Missing: {name}')
        # Try to find similar
        matches = re.findall(f'.*{name[:10]}.*', report)
        if matches:
            print(f'  Similar found: {repr(matches[0].strip())}')
        missing.append(name)

print(f'\n{len(missing)} missing funds')
