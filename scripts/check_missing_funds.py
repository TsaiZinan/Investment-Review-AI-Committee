with open('报告/2026-03-25/2026-03-25_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    content = f.read()
    
# Check for the fund names
fund1 = '富国上证综指联接 C'
fund2 = '广发北证 50 成份指数 C'

print(f"Fund1 '{fund1}' in content: {fund1 in content}")
print(f"Fund2 '{fund2}' in content: {fund2 in content}")

# Check with no spaces
content_no_spaces = content.replace(' ', '')
print(f"Fund1 (no space) in content (no space): {fund1.replace(' ', '') in content_no_spaces}")
print(f"Fund2 (no space) in content (no space): {fund2.replace(' ', '') in content_no_spaces}")

# Find the lines
lines = content.split('\n')
for i, line in enumerate(lines):
    if '富国' in line or '广发北证' in line:
        print(f"Line {i}: {repr(line)}")
