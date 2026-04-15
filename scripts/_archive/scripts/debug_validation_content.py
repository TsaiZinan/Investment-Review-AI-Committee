
import json
from pathlib import Path

report_file = Path("/Users/cai/SynologyDrive/Project/#ProjectLife-000000-理财/报告/2026-03-13/2026-03-13_Gemini-3-Pro_投资建议.md")

report_text = report_file.read_text(encoding="utf-8", errors="replace")
print("--- LAST 500 CHARS REPR ---")
print(repr(report_text[-500:]))
print("--- END ---")

target = "富国上证综指联接C"
if target in report_text:
    print(f"FOUND: {target}")
else:
    print(f"NOT FOUND: {target}")
    for line in report_text.splitlines():
        if "富国" in line:
            print(f"Line with '富国': {repr(line)}")
