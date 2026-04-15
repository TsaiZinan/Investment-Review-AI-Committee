import pandas as pd
import json

def convert_excel_to_json():
    # Read the Excel file
    excel_file = 'Data/投资策略.xlsx'
    df = pd.read_excel(excel_file, header=None)
    
    # Initialize the three main sections
    allocation_summary = []
    investment_plan = []
    non_investment_holdings = []
    
    # Process the data row by row
    current_section = None
    
    for idx, row in df.iterrows():
        row_values = [str(val) if pd.notna(val) else '' for val in row]
        
        # Identify section headers
        if '定投大板块比例' in str(row.iloc[1]) if pd.notna(row.iloc[1]) else False:
            current_section = 'allocation_summary'
            continue
        elif '定投计划' in str(row.iloc[1]) if pd.notna(row.iloc[1]) else False:
            current_section = 'investment_plan'
            continue
        elif '非定投持仓' in str(row.iloc[1]) if pd.notna(row.iloc[1]) else False:
            current_section = 'non_investment_holdings'
            continue
        
        # Skip empty rows
        if all(not val.strip() for val in row_values):
            continue
            
        # Process headers
        if current_section == 'allocation_summary':
            if '大板块' in str(row.iloc[1]) and '比例' in str(row.iloc[2]):
                continue  # This is the header row, skip it
            elif pd.notna(row.iloc[1]) and pd.notna(row.iloc[2]):  # Has category and ratio
                category = row.iloc[1]
                ratio = float(row.iloc[2])
                weekly_amount = int(row.iloc[4]) if pd.notna(row.iloc[4]) and str(row.iloc[4]).isdigit() else None
                
                allocation_summary.append({
                    "category": str(category),
                    "ratio": ratio,
                    "weekly_amount_target": weekly_amount
                })
        
        elif current_section == 'investment_plan':
            if '大板块' in str(row.iloc[1]) and '小板块' in str(row.iloc[2]):
                continue  # This is the header row, skip it
            elif pd.notna(row.iloc[1]) and pd.notna(row.iloc[2]) and pd.notna(row.iloc[4]) and pd.notna(row.iloc[5]):
                # Check if this is an actual data row (not empty)
                if str(row.iloc[1]).strip() != '' and str(row.iloc[2]).strip() != '' and str(row.iloc[5]).strip() != '':
                    category = row.iloc[1]
                    sub_category = row.iloc[2]
                    ratio_in_category = float(row.iloc[3])
                    fund_code = str(int(row.iloc[4])) if pd.notna(row.iloc[4]) and str(row.iloc[4]).replace('.', '').isdigit() else None
                    fund_name = row.iloc[5]
                    weekly_amount = float(row.iloc[6]) if pd.notna(row.iloc[6]) and str(row.iloc[6]).replace('.', '').replace('-', '').isdigit() else None
                    day_of_week = row.iloc[7]
                    long_term_assessment = row.iloc[8]
                    mid_term_assessment = row.iloc[9]
                    short_term_assessment = row.iloc[10]
                    current_holding = float(row.iloc[11]) if pd.notna(row.iloc[11]) and str(row.iloc[11]).replace('.', '').replace('-', '').isdigit() else None
                    
                    investment_plan.append({
                        "category": str(category),
                        "sub_category": str(sub_category),
                        "ratio_in_category": ratio_in_category,
                        "fund_code": fund_code,
                        "fund_name": str(fund_name),
                        "weekly_amount": weekly_amount,
                        "day_of_week": str(day_of_week),
                        "long_term_assessment": str(long_term_assessment) if pd.notna(long_term_assessment) else None,
                        "mid_term_assessment": str(mid_term_assessment) if pd.notna(mid_term_assessment) else None,
                        "short_term_assessment": str(short_term_assessment) if pd.notna(short_term_assessment) else None,
                        "current_holding": current_holding
                    })
    
    # Create the final JSON structure
    result = {
        "allocation_summary": allocation_summary,
        "investment_plan": investment_plan,
        "non_investment_holdings": non_investment_holdings
    }
    
    return result

# Convert and save to JSON file
result = convert_excel_to_json()

# Save to the required location
output_path = '报告/2026-01-28/投资策略.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"Successfully converted Excel to JSON: {output_path}")
print(json.dumps(result, ensure_ascii=False, indent=2))