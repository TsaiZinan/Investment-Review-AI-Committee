import pandas as pd
import json

# Read the Excel file
excel_file = 'Data/投资策略.xlsx'
xls = pd.ExcelFile(excel_file)

# Get the sheet name (usually 'Sheet1' or similar)
sheet_name = xls.sheet_names[0]  # Get the first sheet
df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)

# Convert the DataFrame to a list of lists to see the raw structure
data = df.values.tolist()

# Print the raw data to understand the structure
for i, row in enumerate(data[:20]):  # Print first 20 rows
    print(f"Row {i}: {row}")