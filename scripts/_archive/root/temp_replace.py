import os

f_path = "报告/2026-04-13/2026-04-13_Gemini-3.1-Pro_投资建议.md"
with open(f_path, "r", encoding="utf-8") as f:
    content = f.read()

old_str = """### 6. 现有持仓建议（最多 5 点）(Holdings Notes)
* 天弘余额宝货币市场基金：保持不动 — 提供充足流动性缓冲
* 富国上证综指联接C：暂停定投 — 避免宽基重复暴露
* 易方达北证50指数C：逢高减仓 — 波动过大，落袋为安
* 华夏国证半导体芯片ETF联接C：暂停定投 — 芯片估值偏高，控制仓位
* 华安黄金：停止手动加仓 — 降息推迟，规避回调风险"""

new_str = """### 6. 现有持仓建议（最多 5 点）(Holdings Notes)
* 天弘余额宝货币市场基金：保持不动 — 提供充足流动性缓冲
* 富国上证综指联接C：暂停定投 — 避免宽基重复暴露
* 易方达北证50指数C / 广发北证50成份指数C：逢高减仓 — 波动过大，落袋为安
* 华夏国证半导体芯片ETF联接C：暂停定投 — 芯片估值偏高，控制仓位
* 广发创新药产业ETF联接C / 广发港股创新药ETF联接(QDII)C：保持观望 — 非定投底仓跟随市场波动"""

if old_str in content:
    content = content.replace(old_str, new_str)
    with open(f_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Replace success!")
else:
    print("Old string not found! Here is the content:")
    print(repr(content[-300:]))
