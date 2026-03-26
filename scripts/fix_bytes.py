# Read file as bytes
with open('报告/2026-03-06/2026-03-06_Qwen3.5-Plus_投资建议.md', 'rb') as f:
    content = f.read()

# Replace ETF 联接 -> ETF 联接 (remove space between F and 联)
# ETF = 0x45 0x54 0x46, 联 = 0xe8 0x81 0x94
content = content.replace(b'ETF \xe8\x81\x94', b'ETF\xe8\x81\x94')

# Write back
with open('报告/2026-03-06/2026-03-06_Qwen3.5-Plus_投资建议.md', 'wb') as f:
    f.write(content)

print('Done!')
