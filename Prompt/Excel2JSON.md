# Excel → JSON 提示词（用于生成投资策略.json）

你是一个数据抽取与结构化专家。请把我提供的 Excel 文件内容（`Data/投资策略.xlsx`，工作表通常为“工作表1”）转换成一个严格合法的 JSON，并且 JSON 结构必须与示例 `投资策略.json` 一致。

## 输入
- 我会提供 Excel 的可读内容（例如：按行导出的单元格文本、或我粘贴出来的表格）。
- 你需要从中识别 3 个板块：`定投大板块比例`、`定投计划`、`非定投持仓`。

## 输出（必须遵守）
- 只输出 JSON 本体，不要输出解释、不要输出 Markdown、不要输出代码块围栏。
- JSON 顶层必须是对象，且只包含以下三个键：
  - `allocation_summary`: 数组
  - `investment_plan`: 数组
  - `non_investment_holdings`: 数组
- 数值字段用 JSON number（不要带引号）；空白/缺失用 `null`。
- `fund_code` 必须是字符串或 `null`（即使看起来是数字，也必须保留前导 0）。
- 记录顺序按 Excel 从上到下原始顺序输出，不要自行排序。

## 板块识别规则

### 1) allocation_summary（定投大板块比例）
在 Excel 中通常表现为：
- 标题行包含：`定投大板块比例：`
- 表头行包含：`大板块`、`比例`、`周定投额`
- 数据行示例：`债券 | 0.25 | 1000`

字段映射：
- `category` ← 列“大板块”
- `ratio` ← 列“比例”（转换为 number，例如 0.25）
- `weekly_amount_target` ← 列“周定投额”（转换为 number；若为空则为 null）

输出项示例（结构示意，值以 Excel 为准）：
```json
{
  "category": "债券",
  "ratio": 0.25,
  "weekly_amount_target": 1000
}
```

停止条件：
- 遇到空行/下一个板块标题（例如 `定投计划：`）即停止采集该表。

### 2) investment_plan（定投计划）
在 Excel 中通常表现为：
- 标题行包含：`定投计划：`
- 表头行包含（可能略有差异，但含义一致）：
  - `大板块`
  - `小板块`
  - `占对应大板块比例`
  - `基金代码`
  - `基金名`
  - `周定投额`
  - `定投日期`
  - `长期评估 (5年)`
  - `中期评估 (1年)`
  - `短期评估 (1季度)`
  - `YYYYMMDD持仓`（日期可能变化，例如 `20251227持仓`）

字段映射（按语义，不依赖具体列字母）：
- `category` ← “大板块”
- `sub_category` ← “小板块”
- `ratio_in_category` ← “占对应大板块比例”（number）
- `fund_code` ← “基金代码”（string；空则 null）
- `fund_name` ← “基金名”（string）
- `weekly_amount` ← “周定投额”（number；空则 null）
- `day_of_week` ← “定投日期”（例如 `周一/周二/周三/周四/周五/周六/周日`）
- `long_term_assessment` ← “长期评估 (5年)”
- `mid_term_assessment` ← “中期评估 (1年)”
- `short_term_assessment` ← “短期评估 (1季度)”
- `current_holding` ← 表头形如 `YYYYMMDD持仓` 的那一列（number；空则 null）

输出项示例（结构示意，值以 Excel 为准）：
```json
{
  "category": "中股",
  "sub_category": "汽车",
  "ratio_in_category": 0.2,
  "fund_code": "004854",
  "fund_name": "广发汽车指数A",
  "weekly_amount": null,
  "day_of_week": "周一",
  "long_term_assessment": "汽车出海有成长空间",
  "mid_term_assessment": "汽车出海，新增长点",
  "short_term_assessment": "26汽车补贴预期",
  "current_holding": 1365.83
}
```

清洗与容错：
- 如果某行关键字段（如“大板块/小板块/基金名”）都为空，跳过该行。
- `ratio_in_category`、`weekly_amount`、`current_holding` 必须是 number 或 null。
- `fund_code` 如果像 `004854` 这种有前导 0，必须保留前导 0，且输出为字符串。

停止条件：
- 遇到空行/下一个板块标题（例如 `非定投持仓：`）即停止采集该表。

### 3) non_investment_holdings（非定投持仓）
在 Excel 中通常表现为：
- 标题行包含：`非定投持仓：`
- 表头行包含：`大板块`、`小板块`、`基金`、`YYYYMMDD持仓`

字段映射：
- `category` ← “大板块”
- `sub_category` ← “小板块”
- `fund_name` ← “基金”
- `current_holding` ← 表头形如 `YYYYMMDD持仓` 的那一列（number；空则 null）

输出项示例（结构示意，值以 Excel 为准）：
```json
{
  "category": "中股",
  "sub_category": "北证",
  "fund_name": "易方达北证50指数C",
  "current_holding": 2787.55
}
```

## 最终校验清单（生成 JSON 前自检）
- 顶层键名完全匹配：`allocation_summary` / `investment_plan` / `non_investment_holdings`
- 每个数组元素都包含该板块规定的字段，字段名不多不少
- JSON 可被标准解析器解析（无尾逗号、无注释、无 NaN/Infinity）
- 数字字段没有被输出成字符串
- `fund_code` 没有丢失前导 0
