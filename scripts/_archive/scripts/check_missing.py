import json

with open('报告/2026-03-18/投资策略.json', 'r', encoding='utf-8') as f:
    strategy = json.load(f)

missing = ['富国中证消费电子主题 ETF 联接 A', '国泰中证光伏产业 ETF 联接 A', '富国中证芯片产业 ETF 联接 A']

print('Looking for exact names in JSON:')
for x in strategy.get('investment_plan', []):
    name = x.get('fund_name', '')
    for m in missing:
        if m[:6] in name:
            print(f'JSON has: {repr(name)}')
            print(f'Looking for: {repr(m)}')
            print(f'Match: {name == m}')
            print()
