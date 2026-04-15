#!/usr/bin/env python3
import json

TODAY = "2026-03-16"
ROOT_DIR = "/Users/cai/SynologyDrive/Project/#ProjectLife-000000-理财"
JSON_FILE = f"{ROOT_DIR}/报告/{TODAY}/投资策略.json"

with open(JSON_FILE, 'r', encoding='utf-8') as f:
    strategy = json.load(f)

# Check GPT-5.2 report
REPORT_FILE = f"{ROOT_DIR}/报告/{TODAY}/2026-03-16_GPT-5.2_投资建议.md"
with open(REPORT_FILE, 'r', encoding='utf-8') as f:
    report_gpt = f.read()

# Check Qwen3.5-Plus report
REPORT_FILE_QWEN = f"{ROOT_DIR}/报告/{TODAY}/2026-03-16_Qwen3.5-Plus_投资建议.md"
with open(REPORT_FILE_QWEN, 'r', encoding='utf-8') as f:
    report_qwen = f.read()

fund_name = strategy['investment_plan'][0]['fund_name']
print(f'JSON fund_name: "{fund_name}" (len={len(fund_name)})')

# Check if in GPT report
print(f'\nIn GPT-5.2 report: {fund_name in report_gpt}')
print(f'In Qwen3.5-Plus report: {fund_name in report_qwen}')

# Find the line in both reports
import re
gpt_matches = re.findall(f'.*上银中债.*', report_gpt)
qwen_matches = re.findall(f'.*上银中债.*', report_qwen)

print(f'\nGPT-5.2 matches:')
for m in gpt_matches:
    line = m.strip()
    # Extract fund name from table
    parts = line.split('|')
    if len(parts) > 3:
        fund_in_table = parts[3].strip()
        print(f'  Table fund: "{fund_in_table}" (len={len(fund_in_table)})')
        print(f'  Match: {fund_in_table == fund_name}')

print(f'\nQwen3.5-Plus matches:')
for m in qwen_matches:
    line = m.strip()
    parts = line.split('|')
    if len(parts) > 3:
        fund_in_table = parts[3].strip()
        print(f'  Table fund: "{fund_in_table}" (len={len(fund_in_table)})')
        print(f'  Match: {fund_in_table == fund_name}')
