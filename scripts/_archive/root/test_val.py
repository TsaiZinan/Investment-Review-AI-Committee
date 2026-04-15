from pathlib import Path
report_file = Path("报告/2026-04-10/2026-04-10_Gemini-3.1-Pro_投资建议.md")
report_text = report_file.read_text(encoding="utf-8", errors="replace")
print("Length of text:", len(report_text))
print("Contains '华夏':", "华夏" in report_text)
print("Contains '半导体':", "半导体" in report_text)
print("Contains '华夏国证半导体芯片ETF联接C':", "华夏国证半导体芯片ETF联接C" in report_text)
import re
match = re.search(r'华夏.*联接C', report_text)
if match:
    print("Match:", match.group(0))
    print("Match repr:", repr(match.group(0)))
    print("Target repr:", repr('华夏国证半导体芯片ETF联接C'))
