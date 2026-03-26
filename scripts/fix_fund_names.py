import json

# Read JSON
with open('报告/2026-03-06/投资策略.json', 'r', encoding='utf-8') as f:
    strategy = json.load(f)

# Read current report
with open('报告/2026-03-06/2026-03-06_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    report = f.read()

# Get all fund names from JSON
fund_names = []
for x in strategy.get('investment_plan', []) or []:
    n = (x.get('fund_name') or '').strip()
    if n:
        fund_names.append(n)
for x in strategy.get('non_investment_holdings', []) or []:
    n = (x.get('fund_name') or '').strip()
    if n:
        fund_names.append(n)

# Replace all fund names - remove spaces between Chinese chars and Latin chars
for fund in fund_names:
    # Create pattern: Chinese char + space + Latin char
    # Remove spaces between Chinese and Latin characters
    import re
    
    # Build a pattern from the fund name
    # E.g., "广发港股创新药 ETF 联接 (QDII)A" should match "广发港股创新药 ETF 联接 (QDII) A"
    pattern_parts = []
    i = 0
    while i < len(fund):
        char = fund[i]
        pattern_parts.append(re.escape(char))
        # If current char is Chinese and next is Latin/space, allow optional space
        if '\u4e00-\u9fa5' in char and i + 1 < len(fund):
            next_char = fund[i + 1]
            if next_char.isascii():
                pattern_parts.append(r' ?')
        # If current char is Latin and next is Chinese, allow optional space
        elif char.isascii() and i + 1 < len(fund):
            next_char = fund[i + 1]
            if '\u4e00-\u9fa5' in next_char:
                pattern_parts.append(r' ?')
        i += 1
    
    pattern = ''.join(pattern_parts)
    matches = re.findall(pattern, report)
    for match in matches:
        if match != fund:
            print(f'Replacing: {repr(match)} -> {repr(fund)}')
            report = report.replace(match, fund)

# Check again
missing_after = []
for fund in fund_names:
    if fund not in report:
        missing_after.append(fund)
        
print(f'\nMissing after fix: {len(missing_after)}')
for m in missing_after:
    print(f'  - {repr(m)}')

# Write back
with open('报告/2026-03-06/2026-03-06_Qwen3.5-Plus_投资建议.md', 'w', encoding='utf-8') as f:
    f.write(report)

print('\nDone!')
