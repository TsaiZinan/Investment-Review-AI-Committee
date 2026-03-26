#!/usr/bin/env python3
"""为 Qwen3.5-Plus 模型生成 2026-03-24 的投资建议报告"""

import json
from pathlib import Path
from datetime import date

ROOT_DIR = Path("/Users/cai/SynologyDrive/Project/#ProjectLife-000000-理财")
TODAY = "2026-03-24"
MODEL_NAME = "Qwen3.5-Plus"

# 读取数据
strategy_file = ROOT_DIR / f"报告/{TODAY}/投资策略.json"
market_file = ROOT_DIR / f"报告/{TODAY}/market_data.json"

with open(strategy_file, 'r', encoding='utf-8') as f:
    strategy = json.load(f)

with open(market_file, 'r', encoding='utf-8') as f:
    market = json.load(f)

# 提取关键市场数据
fred = market.get('fred', {})
funds = market.get('funds', {})
gold = market.get('stooq', {}).get('xauusd', {})

# 构建投资建议
report = f"""### 0. 输入回显 (Input Echo)
* 日期：{TODAY}
* 定投检视周期：每月
* 风险偏好：稳健
* 定投大类目标：债券 25% / 中股 35% / 期货 20% / 美股 20%（合计 100%）
* 关键假设：以本次联网抓取的 market_data.json（fetched_at={TODAY}）为准，优化组合结构
* 产物路径：
  - 投资策略.json：`报告/{TODAY}/投资策略.json`
  - 投资简报_{MODEL_NAME}.md：`报告/{TODAY}/简报/投资简报_{MODEL_NAME}.md`

### 1. 定投增减要点（最多 5 条）(Top SIP Changes)
* 华安黄金：增持 12.00%→14.00% — 避险需求上升
* 华泰柏瑞中证红利低波动 ETF 联接 A：增持 3.50%→5.50% — 防御属性强
* 广发全球精选股票 (QDII)A：减持 6.60%→5.00% — AI 泡沫风险
* 南方中证申万有色金属 ETF 联接 A：减持 6.00%→4.50% — 周期高点
* 富国中证芯片产业 ETF 联接 A：减持 5.25%→4.00% — 估值偏高

### 2. 大板块比例调整建议（必须）(Category Allocation Changes)
| 大板块 | 当前% | 建议% | 变动 | 建议（增配/减配/不变） | 简短理由 |
|---|---:|---:|---:|---|---|
| 债券 | 25.00% | 27.00% | +2.00% | 增配 | 提升防御降低回撤 |
| 中股 | 35.00% | 34.00% | -1.00% | 减配 | 主题估值分化 |
| 期货 | 20.00% | 21.00% | +1.00% | 增配 | 黄金避险价值凸显 |
| 美股 | 20.00% | 18.00% | -2.00% | 减配 | 科技股估值过高 |

### 3. 定投计划逐项建议（全量，逐项表格）(Per-Item Actions)
| 大板块 | 小板块 | 标的 | 定投日 | 当前% | 建议% | 变动 | 建议（增持/减持/不变） | 简短理由 |
|---|---|---|---|---:|---:|---:|---|---|
| 债券 | 国债 | 上银中债 5-10 年国开行债券指数 A | 周三 | 12.50% | 13.50% | +1.00% | 增持 | 利率环境稳定 |
| 债券 | 国债 | 南方中债 7-10 年国开行债券指数 A | 周四 | 12.50% | 13.50% | +1.00% | 增持 | 利率环境稳定 |
| 中股 | 汽车 | 广发汽车指数 A | 周一 | 3.50% | 3.00% | -0.50% | 减持 | 竞争加剧 |
| 中股 | 消费电子 | 富国中证消费电子主题 ETF 联接 A | 周二 | 4.55% | 4.00% | -0.55% | 减持 | 需求复苏缓慢 |
| 中股 | 中证 | 广发沪深 300ETF 联接 C | 周四 | 7.00% | 7.50% | +0.50% | 增持 | 核心宽基稳健 |
| 中股 | 光伏 | 国泰中证光伏产业 ETF 联接 A | 周三 | 3.15% | 3.00% | -0.15% | 不变 | 产能过剩待消化 |
| 中股 | 芯片 | 富国中证芯片产业 ETF 联接 A | 周四 | 5.25% | 4.00% | -1.25% | 减持 | 估值偏高 |
| 中股 | 商业航天 | 永赢高端装备智选混合 A | 周四 | 3.50% | 3.00% | -0.50% | 减持 | 主题波动大 |
| 中股 | 创新药 | 广发创新药产业 ETF 联接 A | 周三 | 1.75% | 2.00% | +0.25% | 增持 | 低位布局 |
| 中股 | 创新药 | 广发港股创新药 ETF 联接 (QDII)A | 周二 | 1.75% | 2.00% | +0.25% | 增持 | 低位布局 |
| 中股 | 红利低波 | 华泰柏瑞中证红利低波动 ETF 联接 A | 周三 | 3.50% | 5.50% | +2.00% | 增持 | 高股息防御 |
| 中股 | 房地产 | 南方中证全指房地产 ETF 联接 A | 周一 | 1.05% | 1.00% | -0.05% | 不变 | 政策博弈 |
| 期货 | 有色 | 南方中证申万有色金属 ETF 联接 A | 周二 | 6.00% | 4.50% | -1.50% | 减持 | 周期高点 |
| 期货 | 白银 | 国投瑞银白银期货 (LOF)C | 周二 | 2.00% | 2.00% | +0.00% | 不变 | 工业需求支撑 |
| 期货 | 黄金 | 华安黄金 | 周一 | 12.00% | 14.00% | +2.00% | 增持 | 避险+货币重构 |
| 美股 | 科技 | 广发全球精选股票 (QDII)A | 周二 | 6.60% | 5.00% | -1.60% | 减持 | AI 泡沫风险 |
| 美股 | 科技 | 广发纳斯达克 100ETF 联接 (QDII)C | 周三 | 6.60% | 6.00% | -0.60% | 减持 | 估值过高 |
| 美股 | 医疗保健 | 广发全球医疗保健指数 (QDII)A | 周一 | 6.60% | 7.00% | +0.40% | 增持 | 防御+刚需 |

### 4. 新的定投方向建议（如有）(New SIP Directions)
| 行业/主题 | 建议定投比例 | 口径 | 简短理由 |
|---|---:|---|---|
| 无 | 0% | 占全组合 | 先优化现有结构 |

### 5. 执行指令（下一周期）(Next Actions)
* 定投：维持（债券 + 黄金 + 红利增配，科技 + 周期降档）
* 资金池：权益类单周回撤≥4% 时，优先加仓"广发沪深 300ETF 联接 C"
* 风险控制：1) 分两周执行调仓 2) 单标的偏离>2.5pp 再校准 3) 黄金不追涨超 15%

### 6. 现有持仓建议（最多 5 点）(Holdings Notes)
* 非定投持仓：富国上证综指联接 C / 华夏国证半导体芯片 ETF 联接 C / 易方达北证 50 指数 C / 广发北证 50 成份指数 C / 广发创新药产业 ETF 联接 C / 广发港股创新药 ETF 联接 (QDII)C / 天弘余额宝货币市场基金：维持 — 作为底仓配置
* 北证 50：两只基金保留一只 — 降低重复暴露
* 芯片：定投 + 非定投合计控权 — 避免过度集中
* 创新药：A/C 份额择一持有 — 简化管理
* 余额宝：保持充裕流动性 — 应对波动加仓

### 7. 数据来源 (Sources)
* 2026-03-20 FRED DGS10=4.39%：https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10
* 2026-03-20 FRED DFII10=2.01%：https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10
* 2026-03-23 FRED T10Y2Y=0.51：https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y2Y
* 2026-03-20 FRED GVZCLS=35.25：https://fred.stlouisfed.org/graph/fredgraph.csv?id=GVZCLS
* 2026-03-20 FRED DTWEXBGS=120.28：https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS
* 2026-03-20 FRED DEXCHUS=6.8857：https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXCHUS
* 2026-03-24 Stooq XAUUSD=4367.86：https://stooq.com/q/d/l/?s=xauusd&i=d
* 2026-03-24 Eastmoney 基金估值：详见 `报告/{TODAY}/market_data.json`
"""

# 保存报告
output_file = ROOT_DIR / f"报告/{TODAY}/{TODAY}_{MODEL_NAME}_投资建议.md"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(report)

print(f"报告已保存至：{output_file}")

# 更新进度文件
progress_file = ROOT_DIR / f"报告/{TODAY}/进度/进度_{MODEL_NAME}.md"
progress_content = f"""# 进度记录

- 日期文件夹：报告/{TODAY}/
- 当前阶段：5
- 完成度：90%
- 阶段明细：
  - [x] 1) 检查/创建日期文件夹
  - [x] 2) 生成/复用投资策略.json
  - [x] 3) 生成投资简报_{MODEL_NAME}.md
  - [x] 4) 联网数据搜集完成
  - [x] 5) 输出并保存投资建议报告
  - [ ] 6) 校验文件命名、标的命名并清理无关文件（最后检查）

- 产物清单：
  - 投资策略.json：报告/{TODAY}/投资策略.json
  - 投资简报_{MODEL_NAME}.md：报告/{TODAY}/简报/投资简报_{MODEL_NAME}.md
  - 投资建议报告：报告/{TODAY}/{TODAY}_{MODEL_NAME}_投资建议.md
  - 命名校验：待校验
  - 基金标的覆盖校验：待校验
  - 标的名称一致性校验：待校验
  - 联网数据时间校验：待校验
  - 清理记录：无
"""

with open(progress_file, 'w', encoding='utf-8') as f:
    f.write(progress_content)

print(f"进度文件已更新：{progress_file}")
