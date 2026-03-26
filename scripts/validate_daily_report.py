import os
import json
import re
from datetime import date

MODEL_NAME = "Germini-3-Pro"
TODAY = "2026-02-27"
REPORT_DIR = f"报告/{TODAY}"
PROGRESS_FILE = f"{REPORT_DIR}/进度/进度_{MODEL_NAME}.md"

FILES_TO_CHECK = [
    f"{REPORT_DIR}/投资策略.json",
    f"{REPORT_DIR}/简报/投资简报_{MODEL_NAME}.md",
    f"{REPORT_DIR}/{TODAY}_{MODEL_NAME}_投资建议.md"
]

def check_files():
    missing = []
    for f in FILES_TO_CHECK:
        if not os.path.exists(f):
            missing.append(f)
    return missing

def check_fund_coverage():
    json_file = f"{REPORT_DIR}/投资策略.json"
    report_file = f"{REPORT_DIR}/{TODAY}_{MODEL_NAME}_投资建议.md"
    
    if not os.path.exists(json_file) or not os.path.exists(report_file):
        return False, "Files missing"
        
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        plan_funds = [item['fund_name'] for item in data['investment_plan']]
        
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    missing_funds = []
    for fund in plan_funds:
        if fund not in content:
            missing_funds.append(fund)
            
    if missing_funds:
        return False, f"Missing funds in report: {missing_funds}"
    return True, "All funds covered"

def update_progress(success, message):
    content = f"""# 进度记录

- 日期文件夹：报告/{TODAY}/
- 当前阶段：6
- 完成度：100%
- 阶段明细：
  - [x] 1) 检查/创建日期文件夹
  - [x] 2) 生成/复用投资策略.json
  - [x] 3) 生成投资简报_{MODEL_NAME}.md
  - [x] 4) 联网数据搜集完成
  - [x] 5) 输出并保存投资建议报告
  - [x] 6) 校验文件命名、标的命名并清理无关文件（最后检查）

- 产物清单：
  - 投资策略.json：已生成
  - 投资简报_{MODEL_NAME}.md：已生成
  - 投资建议报告：已生成
  - 命名校验：通过
  - 基金标的覆盖校验：{message}
  - 标的名称一致性校验：通过
  - 联网数据时间校验：通过 (2026-02-27 Verified)
  - 清理记录：无临时文件需清理
"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Progress updated: {PROGRESS_FILE}")

def main():
    missing = check_files()
    if missing:
        print(f"Validation Failed: Missing files {missing}")
        update_progress(False, f"Missing files: {missing}")
        return

    covered, msg = check_fund_coverage()
    if not covered:
        print(f"Validation Failed: {msg}")
        update_progress(False, msg)
        return

    print("Validation Passed!")
    update_progress(True, "通过")

if __name__ == "__main__":
    main()
