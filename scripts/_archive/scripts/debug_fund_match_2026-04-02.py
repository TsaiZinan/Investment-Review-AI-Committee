import json

# Read JSON
with open("报告/2026-04-02/投资策略.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    fund_from_json = data["investment_plan"][0]["fund_name"]

# Read Report
with open("报告/2026-04-02/2026-04-02_Qwen3.5-Plus_投资建议.md", "r", encoding="utf-8") as f:
    content = f.read()

print(f"Fund from JSON: {repr(fund_from_json)}")
print(f"Fund length: {len(fund_from_json)}")
print(f"Fund bytes: {fund_from_json.encode('utf-8')}")

# Search in content
found = fund_from_json in content
print(f"\nFound in report: {found}")

# Try to find similar string
import re
pattern = r"上银.*国开行.*指数 A"
matches = re.findall(pattern, content)
print(f"\nRegex matches for '{pattern}': {matches}")
if matches:
    print(f"Match repr: {repr(matches[0])}")
    print(f"Match bytes: {matches[0].encode('utf-8')}")

# Compare byte by byte
if matches:
    match = matches[0]
    print(f"\nComparison:")
    print(f"JSON fund:  {fund_from_json}")
    print(f"Report fund: {match}")
    print(f"Equal: {fund_from_json == match}")
    
    # Check character by character
    for i, (c1, c2) in enumerate(zip(fund_from_json, match)):
        if c1 != c2:
            print(f"  Diff at pos {i}: '{c1}' (ord={ord(c1)}) vs '{c2}' (ord={ord(c2)})")
