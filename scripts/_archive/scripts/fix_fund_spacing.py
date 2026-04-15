import json
import re

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

# Replace spaced versions with exact names
for name in fund_names:
    # Create a pattern that matches the name with optional spaces between Chinese chars and letters/numbers
    # But we need to be careful not to change the actual name structure
    
    # Common patterns to fix:
    # "ETF  联接" -> "ETF 联接"
    # "ETF  发起式联接" -> "ETF 发起式联接"
    # "(QDII)A" -> "(QDII)A"
    
    # Try to find and replace variations
    name_no_spaces = name.replace(' ', '')
    name_with_spaces = ' '.join(name)  # Add space between every char
    
    # Just normalize multiple spaces to single space first
    report = re.sub(r'  +', ' ', report)
    
    # Now try to match with spaces around ETF, QDII, LOF, etc.
    # For each fund name, create a regex that allows spaces
    parts = re.split(r'([A-Z]+|\([^)]+\))', name)
    # Remove empty parts
    parts = [p for p in parts if p]
    
    # Build pattern that allows spaces between parts
    pattern = r'\s*'.join(re.escape(p) for p in parts)
    
    # Find matches
    matches = re.findall(pattern, report)
    for match in matches:
        # Replace with exact name
        report = report.replace(match, name, 1)

# Also fix common spacing issues
report = re.sub(r'ETF  +', 'ETF ', report)
report = re.sub(r'ETF +([A-Z])', r'ETF\1', report)
report = re.sub(r'\(QDII\) +', '(QDII)', report)
report = re.sub(r'\(QDII\)+', '(QDII)', report)
report = re.sub(r' +联接', ' 联接', report)
report = re.sub(r'联接 +', '联接 ', report)
report = re.sub(r' +指数 +', ' 指数 ', report)
report = re.sub(r' +混合 +', ' 混合 ', report)
report = re.sub(r' +股票 +', ' 股票 ', report)
report = re.sub(r' +期货 +', ' 期货 ', report)
report = re.sub(r'\(LOF\) +', '(LOF)', report)

# Write back
with open('报告/2026-03-18/2026-03-18_Qwen3.5-Plus_投资建议.md', 'w', encoding='utf-8') as f:
    f.write(report)

print("Fixed fund name spacing")
