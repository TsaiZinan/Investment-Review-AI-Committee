import json

with open('报告/2026-03-25/投资策略.json', 'r', encoding='utf-8') as f:
    strategy = json.load(f)

with open('报告/2026-03-25/2026-03-25_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    report = f.read()

json_fund = strategy['investment_plan'][0]['fund_name']
print(f"JSON fund: {repr(json_fund)}")
print(f"JSON fund bytes: {[hex(ord(c)) for c in json_fund]}")

# Extract from report line 29
lines = report.split('\n')
line29 = lines[28]  # 0-indexed
print(f"\nReport line 29: {repr(line29)}")

# Parse the table row
parts = line29.split('|')
if len(parts) >= 4:
    report_fund = parts[3].strip()
    print(f"Report fund: {repr(report_fund)}")
    print(f"Report fund bytes: {[hex(ord(c)) for c in report_fund]}")
    
    print(f"\nMatch: {json_fund == report_fund}")
    print(f"Match (no space): {json_fund.replace(' ', '') == report_fund.replace(' ', '')}")
