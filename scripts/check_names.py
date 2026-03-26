import json

with open('报告/2026-03-18/投资策略.json', 'r', encoding='utf-8') as f:
    strategy = json.load(f)

for x in strategy.get('investment_plan', []):
    name = x.get('fund_name', '')
    if '消费电子' in name or '光伏' in name or '芯片' in name:
        print(f'{repr(name)} | len={len(name)} | spaces={name.count(" ")}')
