import json
from pathlib import Path
import os
files = list(Path('报告/2026-04-12/').glob('*.md'))
for f in files:
    if 'Gemini-3.1-Pro' in f.name:
        print(f"Reading {f.name}")
        text = f.read_text(encoding='utf-8')
        print("华夏国证半导体芯片ETF联接C" in text)
        for line in text.split('\n'):
            if "华夏国" in line:
                print(repr(line))
