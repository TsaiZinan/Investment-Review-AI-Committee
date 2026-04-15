with open('报告/2026-03-25/2026-03-25_Qwen3.5-Plus_投资建议.md', 'rb') as f:
    content = f.read()
    
# Find line 61
lines = content.split(b'\n')
print(f"Line 60 (0-indexed 59): {lines[59]}")
print(f"Line 61 (0-indexed 60): {lines[60]}")
print(f"Line 62 (0-indexed 61): {lines[61]}")
print(f"Line 63 (0-indexed 62): {lines[62]}")
print(f"Line 64 (0-indexed 63): {lines[63]}")

# Check bytes for fund names
fund1 = '富国上证综指联接 C'
fund2 = '广发北证 50 成份指数 C'
print(f"\nFund1 bytes: {fund1.encode('utf-8')}")
print(f"Fund2 bytes: {fund2.encode('utf-8')}")
