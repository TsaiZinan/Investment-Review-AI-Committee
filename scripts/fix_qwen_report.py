import re
import sys

file_path = sys.argv[1]

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove spaces between Chinese characters
content = re.sub(r'([\u4e00-\u9fa5]) +([\u4e00-\u9fa5])', r'\1\2', content)

# Remove spaces between Chinese and numbers/letters
content = re.sub(r'([\u4e00-\u9fa5]) +([0-9A-Za-z()])', r'\1\2', content)
content = re.sub(r'([0-9A-Za-z()]) +([\u4e00-\u9fa5])', r'\1\2', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')
