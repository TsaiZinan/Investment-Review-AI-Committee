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

# Replace all fund names in report with exact names from JSON
for fund_name in fund_names:
    # Look for common variations of the fund name in the report
    # We'll use a more flexible approach: find similar names and replace them
    
    # Escape special regex characters in fund name
    escaped_name = re.escape(fund_name)
    
    # Create pattern that allows for extra spaces between words/characters
    # Replace spaces with \s+ to match one or more whitespace
    spaced_pattern = escaped_name.replace(r'\ ', r'\s*')
    
    # Also try to match names that have extra spaces inserted
    # Split the fund name and allow variable spacing between parts
    parts = []
    current_part = ''
    for char in fund_name:
        if char.isalnum() or char in '()-':
            current_part += char
        else:  # space or other separator
            if current_part:
                parts.append(current_part)
                current_part = ''
            parts.append(char)
    if current_part:
        parts.append(current_part)
    
    # Build regex pattern allowing variable spacing
    pattern_parts = []
    for part in parts:
        if part.strip():  # If it's alphanumeric part
            pattern_parts.append(re.escape(part))
        else:  # If it's a space
            pattern_parts.append(r'\s*')
    
    pattern = ''.join(pattern_parts)
    
    # Find and replace all matches
    matches = re.findall(pattern, report)
    for match in matches:
        if match.strip():  # Only replace non-empty matches
            report = report.replace(match, fund_name)

# Additional fix: some fund names might have different spacing patterns
# Let's do a more comprehensive replacement by identifying the exact mismatches
for fund_name in fund_names:
    # Direct replacement (should work for most cases now)
    # But also look for common variations
    
    # Try to find variants in the report by looking for close matches
    import difflib
    
    # Look through the entire report to find anything that looks like this fund name
    lines = report.split('\n')
    for i, line in enumerate(lines):
        for fund in fund_names:
            # If we find something similar to the fund name in the line, replace it
            if fund[:5] in line and fund not in line:  # Fund not found but partial match
                # Look for similar patterns in this line
                import re
                # Find anything that looks like a fund name containing the base name
                possible_matches = re.findall(r'[^\n|]*' + fund[:4] + r'[^\n|]*', line)
                for possible_match in possible_matches:
                    if fund not in possible_match and fund[:4] in possible_match:
                        # Replace the similar name with the exact fund name
                        report = report.replace(possible_match, possible_match.replace(possible_match.strip(), fund))

# More precise fix: iterate through the original fund names and replace variations
original_report = report
for fund_name in fund_names:
    # Find all possible variations in the report
    # First, create a loose pattern
    loose_pattern = fund_name[0]
    for char in fund_name[1:]:
        loose_pattern += r'\s*' + re.escape(char)
    
    matches = re.findall(loose_pattern, report, re.IGNORECASE)
    for match in matches:
        if len(match) >= len(fund_name) * 0.8:  # At least 80% match
            report = report.replace(match, fund_name)

# Even more direct approach: find fund-like strings in report and match with JSON
report_lines = report.split('\n')
for i, line in enumerate(report_lines):
    for fund_name in fund_names:
        # Look for fund names in table rows and other contexts
        # Create flexible pattern that allows for spacing differences
        pattern = fund_name.replace('ETF', r'\s*ETF\s*').replace('联接', r'\s*联接\s*').replace('发起', r'\s*发起\s*')
        pattern = pattern.replace('混合', r'\s*混合\s*').replace('股票', r'\s*股票\s*').replace('指数', r'\s*指数\s*')
        pattern = pattern.replace('QDII', r'\s*QDII\s*').replace('LOF', r'\s*LOF\s*')
        pattern = pattern.replace('(', r'\s*\(\s*').replace(')', r'\s*\)\s*')
        pattern = pattern.replace('-', r'\s*-\s*')
        
        matches = re.findall(pattern, line)
        for match in matches:
            if match.strip() != fund_name:
                report_lines[i] = report_lines[i].replace(match, fund_name)

report = '\n'.join(report_lines)

# Write back
with open('报告/2026-03-18/2026-03-18_Qwen3.5-Plus_投资建议.md', 'w', encoding='utf-8') as f:
    f.write(report)

print("Fixed fund name spacing with exact matches")