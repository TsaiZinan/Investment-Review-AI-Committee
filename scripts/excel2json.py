import pandas as pd
import json
import sys
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "Data/投资策略.xlsx"
REPORTS_DIR = PROJECT_ROOT / "报告"

def get_today_str():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def convert_excel_to_json(input_path, output_path):
    print(f"Reading {input_path}...")
    try:
        # 读取整个 sheet
        df = pd.read_excel(input_path, sheet_name=0, header=None)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    data = {
        "allocation_summary": [],
        "investment_plan": [],
        "non_investment_holdings": []
    }

    # 辅助函数：查找标题所在的行索引
    def find_row_index(keyword):
        for idx, row in df.iterrows():
            # 检查该行所有单元格，看是否包含关键字
            row_str = row.astype(str).str.cat(sep=' ')
            if keyword in row_str:
                return idx
        return -1

    # 1. 解析 allocation_summary
    start_idx = find_row_index("定投大板块比例")
    if start_idx != -1:
        # 假设下一行是表头
        header_row_idx = start_idx + 1
        headers = df.iloc[header_row_idx].astype(str).tolist()
        
        # 找到列索引
        try:
            col_category = next(i for i, h in enumerate(headers) if "大板块" in h)
            col_ratio = next(i for i, h in enumerate(headers) if "比例" in h)
            col_amount = next(i for i, h in enumerate(headers) if "周定投额" in h)
        except StopIteration:
            print("Error: Could not find required columns for allocation_summary")
            return

        # 遍历数据行
        current_row = header_row_idx + 1
        while current_row < len(df):
            row = df.iloc[current_row]
            # 停止条件：遇到空行或下一个板块标题
            first_cell = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
            if "定投计划" in str(df.iloc[current_row].values): # 检查整行是否包含下一个标题
                 break
            if pd.isna(row.iloc[col_category]) or str(row.iloc[col_category]).strip() == "":
                 # 可能是空行，检查后面是否还有数据，或者直接假设结束
                 # 但有时候空行只是分隔。更安全的做法是看是否碰到下一个标题
                 # 这里简化处理：如果大板块为空，且整行基本为空，则认为是空行
                 if row.isnull().all():
                     break
            
            # 提取数据
            category = row.iloc[col_category]
            if pd.notna(category):
                ratio = row.iloc[col_ratio]
                amount = row.iloc[col_amount]
                
                item = {
                    "category": category,
                    "ratio": float(ratio) if pd.notna(ratio) else 0.0,
                    "weekly_amount_target": float(amount) if pd.notna(amount) else None
                }
                data["allocation_summary"].append(item)
            current_row += 1

    # 2. 解析 investment_plan
    start_idx = find_row_index("定投计划")
    if start_idx != -1:
        header_row_idx = start_idx + 1
        headers = df.iloc[header_row_idx].astype(str).tolist()
        
        # 映射列名到索引
        col_map = {}
        mapping = {
            "大板块": "category",
            "小板块": "sub_category",
            "占对应大板块比例": "ratio_in_category",
            "基金代码": "fund_code",
            "基金名": "fund_name",
            "基金名称": "fund_name",
            "周定投额": "weekly_amount",
            "定投日期": "day_of_week",
            "长期评估": "long_term_assessment",
            "中期评估": "mid_term_assessment",
            "短期评估": "short_term_assessment",
            "持仓": "current_holding" # 模糊匹配
        }
        
        for col_name, field in mapping.items():
            for i, h in enumerate(headers):
                if col_name in h:
                    col_map[field] = i
                    break
        
        current_row = header_row_idx + 1
        while current_row < len(df):
            row = df.iloc[current_row]
            if "非定投持仓" in str(df.iloc[current_row].values):
                break
            
            # 必须有基金名
            if "fund_name" in col_map and pd.notna(row.iloc[col_map["fund_name"]]):
                item = {}
                for field, col_idx in col_map.items():
                    val = row.iloc[col_idx]
                    if field == "fund_code":
                        if not pd.notna(val) or str(val).strip() == "":
                            item[field] = None
                        else:
                            code = str(val).strip()
                            if code.endswith(".0"):
                                code = code[:-2]
                            if code.isdigit() and len(code) < 6:
                                code = code.zfill(6)
                            item[field] = code
                    elif field in ["ratio_in_category", "weekly_amount", "current_holding"]:
                        try:
                            item[field] = float(val) if pd.notna(val) else None
                        except:
                            item[field] = None
                    else:
                        item[field] = str(val) if pd.notna(val) else None
                
                data["investment_plan"].append(item)
            current_row += 1

    # 3. 解析 non_investment_holdings
    start_idx = find_row_index("非定投持仓")
    if start_idx != -1:
        header_row_idx = start_idx + 1
        headers = df.iloc[header_row_idx].astype(str).tolist()
        
        col_map = {}
        mapping = {
            "大板块": "category",
            "小板块": "sub_category",
            "基金": "fund_name",
            "持仓": "current_holding"
        }
        
        for col_name, field in mapping.items():
            for i, h in enumerate(headers):
                if col_name in h:
                    col_map[field] = i
                    break
                    
        current_row = header_row_idx + 1
        while current_row < len(df):
            row = df.iloc[current_row]
            # 简单判断结束：连续空行或者文件结束
            if row.isnull().all():
                current_row += 1 # 尝试再读一行，如果是结束通常后面全是空
                if current_row >= len(df) or df.iloc[current_row].isnull().all():
                    break
                else:
                    continue # 可能是中间空行

            if "fund_name" in col_map and pd.notna(row.iloc[col_map["fund_name"]]):
                item = {}
                for field, col_idx in col_map.items():
                    val = row.iloc[col_idx]
                    if field == "current_holding":
                        try:
                            item[field] = float(val) if pd.notna(val) else None
                        except:
                            item[field] = None
                    else:
                        item[field] = str(val) if pd.notna(val) else None
                data["non_investment_holdings"].append(item)
            current_row += 1

    # 输出 JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Successfully converted to {output_path}")

if __name__ == "__main__":
    date_str = sys.argv[1] if len(sys.argv) >= 2 else get_today_str()
    input_path = DATA_FILE
    output_path = REPORTS_DIR / date_str / "投资策略.json"
    convert_excel_to_json(input_path, output_path)
