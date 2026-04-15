import sys
from pathlib import Path
report_file = Path("报告/2026-04-10/2026-04-10_Gemini-3.1-Pro_投资建议.md")
print(f"File exists: {report_file.exists()}")
print(f"File size: {report_file.stat().st_size}")
with open(report_file, 'rb') as f:
    content = f.read()
    print("Contains '华夏':", "华夏".encode('utf-8') in content)
    idx = content.find("华夏".encode('utf-8'))
    if idx != -1:
        print(f"Found at byte {idx}")
