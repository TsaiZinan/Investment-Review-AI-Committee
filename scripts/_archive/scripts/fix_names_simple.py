import json

# Load strategy to get exact fund names
with open('报告/2026-03-18/投资策略.json', 'r', encoding='utf-8') as f:
    strategy = json.load(f)

# Get all fund names
fund_names = []
for x in strategy.get('investment_plan', []):
    n = (x.get('fund_name') or '').strip()
    if n:
        fund_names.append(n)
for x in strategy.get('non_investment_holdings', []):
    n = (x.get('fund_name') or '').strip()
    if n:
        fund_names.append(n)

# Read report
with open('报告/2026-03-18/2026-03-18_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    report = f.read()

# Replace all spaced versions with exact names
for fund_name in fund_names:
    # Create spaced version (add space between each character)
    spaced = ' '.join(fund_name)
    # Remove spaces between Chinese characters but keep around English/numbers
    import re
    # Pattern: remove spaces between Chinese chars, keep spaces around Latin chars
    # Just directly replace common patterns
    patterns_to_try = [
        fund_name.replace('ETF', ' ETF ').replace('联接', ' 联接 ').replace('发起式', ' 发起式 '),
        fund_name.replace('ETF', ' ETF  ').replace('联接', '  联接  '),
        fund_name.replace('(', ' (').replace(')', ') '),
    ]
    
    for pattern in patterns_to_try:
        if pattern in report and pattern != fund_name:
            report = report.replace(pattern, fund_name)
    
    # Also try direct replacement of common issues
    # Remove double spaces
    report = report.replace('  ', ' ')
    
    # Specific fixes for this fund
    if 'ETF' in fund_name:
        # Look for ETF with extra spaces
        import re
        # Find "ETF" followed by spaces and Chinese
        pattern = r'ETF\s+([\u4e00-\u9fff])'
        replacement = r'ETF\1'
        report = re.sub(pattern, replacement, report)
        
    if '(QDII)' in fund_name or '(LOF)' in fund_name:
        # Fix spacing around parentheses
        pattern = r'\(([A-Z]+)\)\s*([A-Z])'
        replacement = r'(\1)\2'
        report = re.sub(pattern, replacement, report)

# Final pass: remove all double spaces
report = report.replace('  ', ' ')

# Write back
with open('报告/2026-03-18/2026-03-18_Qwen3.5-Plus_投资建议.md', 'w', encoding='utf-8') as f:
    f.write(report)

print("Fixed fund names")
