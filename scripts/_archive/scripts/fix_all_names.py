import json
import re

# Load strategy to get exact fund names
with open('报告/2026-03-18/投资策略.json', 'r', encoding='utf-8') as f:
    strategy = json.load(f)

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

# For each fund name, find variations with spaces and replace with exact name
for exact_name in fund_names:
    # Remove all spaces from the exact name to create a pattern
    name_no_spaces = exact_name.replace(' ', '')
    
    # Find all occurrences in report that match this pattern (with variable spaces)
    # Build a regex that allows spaces between any characters
    pattern = ''
    for char in exact_name:
        if char == ' ':
            pattern += r'\s*'
        else:
            pattern += re.escape(char) + r'\s*'
    
    # Find matches
    matches = re.findall(pattern, report)
    for match in matches:
        # Only replace if removing spaces gives us the target name
        if match.replace(' ', '') == name_no_spaces:
            report = report.replace(match, exact_name)

# Write back
with open('报告/2026-03-18/2026-03-18_Qwen3.5-Plus_投资建议.md', 'w', encoding='utf-8') as f:
    f.write(report)

print("Fixed all fund names to match JSON exactly")
