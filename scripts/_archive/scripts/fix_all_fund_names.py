import json

# Read JSON to get correct fund names
with open("报告/2026-04-02/投资策略.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    correct_fund_names = [item["fund_name"] for item in data["investment_plan"]]

# Read report
with open("报告/2026-04-02/2026-04-02_Qwen3.5-Plus_投资建议.md", "r", encoding="utf-8") as f:
    content = f.read()

# Create mapping from fund names with spaces to without spaces
# We'll search for each fund in the report and replace with the correct name
for correct_name in correct_fund_names:
    # Try to find variations with spaces
    # Simple approach: if the fund name without spaces is in the content, but the correct name is not, replace it
    name_no_spaces = correct_name.replace(" ", "")
    
    if correct_name not in content and name_no_spaces in content:
        # This shouldn't happen, but just in case
        content = content.replace(name_no_spaces, correct_name)
        print(f"Fixed: '{name_no_spaces}' -> '{correct_name}'")
    elif correct_name not in content:
        # Try to find a similar string with spaces
        import re
        # Create pattern that matches the fund name with optional spaces between each character
        pattern = ""
        for char in correct_name:
            if char.isalnum() or '\u4e00' <= char <= '\u9fff':  # Chinese character or alphanumeric
                pattern += char + r"\s*"  # Allow optional spaces after
            else:
                pattern += re.escape(char)
        
        match = re.search(pattern, content)
        if match:
            found_text = match.group(0)
            content = content.replace(found_text, correct_name)
            print(f"Replaced: '{found_text}' -> '{correct_name}'")

# Write back
with open("报告/2026-04-02/2026-04-02_Qwen3.5-Plus_投资建议.md", "w", encoding="utf-8") as f:
    f.write(content)

print("\nDone!")

# Verify
print("\nVerification:")
with open("报告/2026-04-02/2026-04-02_Qwen3.5-Plus_投资建议.md", "r", encoding="utf-8") as f:
    content = f.read()
    
missing = [f for f in correct_fund_names if f not in content]
if missing:
    print(f"Still missing: {missing}")
else:
    print("✓ All funds are now covered!")
