with open("报告/2026-04-02/2026-04-02_Qwen3.5-Plus_投资建议.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}\n")

# Check lines 41-46 (0-indexed: 40-45)
for i in range(40, 46):
    if i < len(lines):
        line = lines[i].strip()
        parts = line.split("|")
        if len(parts) >= 4:
            fund_part = parts[3].strip()
            print(f"Line {i+1}: {repr(fund_part)}")
        else:
            print(f"Line {i+1}: {repr(line[:100])}")
