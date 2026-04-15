import json
import os

MODEL_NAME = "Qwen3.5-Plus"
TODAY = "2026-04-02"
json_file = f"报告/{TODAY}/投资策略.json"
report_file = f"报告/{TODAY}/{TODAY}_{MODEL_NAME}_投资建议.md"

print(f"Checking files:")
print(f"  JSON: {json_file} - Exists: {os.path.exists(json_file)}")
print(f"  Report: {report_file} - Exists: {os.path.exists(report_file)}")

if os.path.exists(json_file) and os.path.exists(report_file):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        plan_funds = [item["fund_name"] for item in data["investment_plan"]]
        
    with open(report_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    missing = [f for f in plan_funds if f not in content]
    
    if missing:
        print(f"\nMissing funds: {missing}")
    else:
        print(f"\n✓ All {len(plan_funds)} funds are covered!")
else:
    print("\nFiles missing!")
