with open('报告/2026-03-18/2026-03-18_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    report = f.read()

names_with_spaces = ['富国中证消费电子主题 ETF联接A', '国泰中证光伏产业 ETF联接A', '富国中证芯片产业 ETF联接A']
for name in names_with_spaces:
    print(f'{repr(name)} in report: {name in report}')
    print(f'  spaces: {name.count(" ")}')

# Also check the actual names in the report
import re
lines = report.split('\n')
for line in lines:
    if '消费电子' in line or '光伏' in line or '芯片' in line:
        print(f'Line contains fund: {line}')