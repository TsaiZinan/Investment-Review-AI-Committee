import json

# Load strategy
with open('报告/2026-03-18/投资策略.json', 'r', encoding='utf-8') as f:
    strategy = json.load(f)

# Create mapping from simplified to exact names
fund_mapping = {}
for x in strategy.get('investment_plan', []):
    name = (x.get('fund_name') or '').strip()
    if name:
        # Create key without spaces
        key = name.replace(' ', '')
        fund_mapping[key] = name
        
for x in strategy.get('non_investment_holdings', []):
    name = (x.get('fund_name') or '').strip()
    if name:
        key = name.replace(' ', '')
        fund_mapping[key] = name

# Read current report
with open('报告/2026-03-18/2026-03-18_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    report = f.read()

# Replace fund names line by line
lines = report.split('\n')
new_lines = []

for line in lines:
    new_line = line
    # Check if this line contains any fund-like pattern
    for key, exact_name in fund_mapping.items():
        # Try to find variations of this fund name in the line
        if key[:6] in line.replace(' ', ''):  # Partial match without spaces
            # Try to replace the spaced version with exact name
            # First, find the actual text in the line that matches this fund
            import re
            # Build a pattern that allows spaces between chars
            pattern = ''
            for char in key:
                pattern += re.escape(char) + r'\s*'
            
            matches = re.findall(pattern, line)
            for match in matches:
                if match.strip():
                    new_line = new_line.replace(match, exact_name)
    
    new_lines.append(new_line)

report = '\n'.join(new_lines)

# Write back
with open('报告/2026-03-18/2026-03-18_Qwen3.5-Plus_投资建议.md', 'w', encoding='utf-8') as f:
    f.write(report)

print("Replaced fund names with exact matches from JSON")
