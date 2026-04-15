from pathlib import Path

report_file = Path('报告/2026-04-12/2026-04-12_Gemini-3.1-Pro_投资建议.md')
text = report_file.read_text(encoding='utf-8', errors='replace')

names = [
    "华夏国证半导体芯片ETF联接C",
    "易方达北证50指数C",
    "广发北证50成份指数C",
    "广发创新药产业ETF联接C",
    "广发港股创新药ETF联接(QDII)C"
]

for n in names:
    print(f"Checking {n}: {n in text}")

print("--- LAST 20 LINES ---")
lines = text.split('\n')
for line in lines[-20:]:
    print(line)

