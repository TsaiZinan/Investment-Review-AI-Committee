with open("报告/2026-04-02/2026-04-02_Qwen3.5-Plus_投资建议.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Check lines 42-46 (0-indexed: 41-45)
for i in [41, 42, 43, 44, 45]:
    if i < len(lines):
        line = lines[i]
        print(f"Line {i+1}:")
        print(f"  Raw: {repr(line)}")
        # Extract fund name portion (between second and third |)
        parts = line.split("|")
        if len(parts) >= 4:
            fund_part = parts[3].strip()
            print(f"  Fund: {repr(fund_part)}")
            print(f"  Fund bytes: {fund_part.encode('utf-8')}")
        print()
