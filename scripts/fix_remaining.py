# Read the report
with open('报告/2026-03-06/2026-03-06_Qwen3.5-Plus_投资建议.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace using bytes to be precise
# From: 广发港股创新药 ETF 联接 (QDII)A (with spaces: 0x20)
# To: 广发港股创新药 ETF 联接 (QDII)A (no spaces)

replacements = [
    # 广发港股创新药 ETF 联接 (QDII)A -> 广发港股创新药 ETF 联接 (QDII)A
    ('药 ETF 联接 (QDII)A', '药 ETF 联接 (QDII)A'),
    # 广发纳斯达克 100ETF 联接 (QDII)C -> 广发纳斯达克 100ETF 联接 (QDII)C  
    ('克 100ETF 联接 (QDII)C', '克 100ETF 联接 (QDII)C'),
    # 广发港股创新药 ETF 联接 (QDII)C -> 广发港股创新药 ETF 联接 (QDII)C
    ('药 ETF 联接 (QDII)C', '药 ETF 联接 (QDII)C'),
]

for old, new in replacements:
    count = content.count(old)
    if count > 0:
        print(f'Replacing {count} occurrences')
        print(f'  From: {repr(old)}')
        print(f'  To: {repr(new)}')
        content = content.replace(old, new)
    else:
        print(f'Not found: {repr(old)}')

# Write back
with open('报告/2026-03-06/2026-03-06_Qwen3.5-Plus_投资建议.md', 'w', encoding='utf-8') as f:
    f.write(content)

print('\nDone!')
