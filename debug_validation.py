
import json
from pathlib import Path

report_path = Path("/Users/cai/SynologyDrive/Project/#ProjectLife-000000-理财/报告/2026-03-14/2026-03-14_Gemini-3-Pro_投资建议.md")
report_text = report_path.read_text(encoding="utf-8")

names = [
    "富国上证综指联接C",
    "华夏国证半导体芯片ETF联接C",
    "易方达北证50指数C",
    "广发北证50成份指数C",
    "广发创新药产业ETF联接C",
    "广发港股创新药ETF联接(QDII)C",
    "天弘余额宝货币市场基金"
]

lines = report_text.splitlines()
for i, line in enumerate(lines):
    if "其他非定投持仓" in line:
        print(f"Line {i+1}: {repr(line)}")
        for n in names:
             if n in line:
                 print(f"Found '{n}' in line")
             else:
                 print(f"Not found '{n}' in line")
