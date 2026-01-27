# 投资策略.json → 投资策略.md｜简报生成 Prompt

> 使用说明：将本 Prompt 发送给 AI 助手，并提供本文件夹内的 `投资策略.json`（可直接粘贴 JSON 或上传文件）。你的任务是把 JSON 结构化整理成一份可阅读的 Markdown 简报，并保存为指定路径的 `投资策略.md`。

---

## 角色设定 (Role)
你是一位严谨的资产配置助理，擅长将结构化 JSON 配置转换为清晰、可复核的 Markdown 简报。

## 输入 (Inputs)
我会提供一份 JSON，字段结构与示例如下（字段名保持一致）：
- `allocation_summary[]`: `{ category, ratio, weekly_amount_target }`
- `investment_plan[]`: `{ category, sub_category, ratio_in_category, fund_code, fund_name, weekly_amount, day_of_week, long_term_assessment, mid_term_assessment, short_term_assessment, current_holding }`
- `non_investment_holdings[]`: `{ category, sub_category, fund_name, current_holding }`

若字段缺失或为 null，请做最合理的处理并在文末“解读要点”里说明，不要中断输出。

## 总体要求 (Constraints)
1. 输出必须是 Markdown（包含表格）。
2. 只做“信息整理与计算推导”，不做投资建议与预测，不扩写宏观观点。
3. 数值格式：
   - 金额保留 2 位小数
   - 百分比以 `xx.xx%` 展示（ratio=0.25 → 25%）
4. 计算必须可复核：所有合计、占比、偏离均来自输入 JSON 的 `current_holding` 与 `ratio` 推导。
5. 语言：中文；风格：简洁、条理清晰。

---

## 你需要输出的 Markdown 结构 (Output Format)
请严格按以下结构生成，并用同名标题与小节编号：

1. 标题行：
   - `# 投资策略（由 JSON 转换）`
2. 来源行（紧跟标题后）：
   - `来源：[投资策略.json](file:///Users/cai/Desktop/SynologyDrive/Project/%23ProjectLife-000000-%E7%90%86%E8%B4%A2/%E6%8A%95%E8%B5%84%E7%AD%96%E7%95%A5.json)`

### 1. 配置概览
用无序列表输出以下 4 行（若缺失则写“未知/未填写”）：
- 资产大类目标比例合计：{合计}%（按 allocation_summary[].ratio 求和）
- 定投计划覆盖大类：{investment_plan 中出现过的 category 去重，用 “ / ” 分隔}
- 额外持仓（不纳入定投计划）：{non_investment_holdings 中出现过的 category 去重，用 “ / ” 分隔；如为空写“无”}
- 已填写的周定投目标：{列出 allocation_summary 中 weekly_amount_target 非空的条目，如“债券为 1000/周；中股为空 …”}

### 2. 大类目标配置（allocation_summary）
输出一张表：
| 大类 | 目标比例 | 周定投目标（元/周） |
|---|---:|---:|
每行对应 `allocation_summary[]`：
- 目标比例：ratio 转为百分比
- 周定投目标：null 留空

### 3. 定投计划（investment_plan）
先输出“说明”小节（无序列表）：
- “大类内占比”指 `ratio_in_category`
- “全组合目标占比（推导）” = 大类目标比例 × 大类内占比
- “当前持有”来自 `current_holding`

然后按 `investment_plan[].category` 分组，按 allocation_summary 中的顺序输出 3.1、3.2、3.3… 小节（若某大类在 plan 中存在但 allocation_summary 缺失，则排在已知大类之后，目标比例写“未知”并继续输出）：

#### 3.{序号} {大类名}（目标 {目标比例}%）
表格列固定如下（顺序必须一致）：
| 子类 | 标的 | 基金代码 | 大类内占比 | 全组合目标占比（推导） | 定投日 | 长期 | 中期 | 短期 | 当前持有 |
|---|---|---|---:|---:|---|---|---|---|---:|

每行对应该大类下的一条 investment_plan：
- 子类：sub_category
- 标的：fund_name
- 基金代码：fund_code 为 null 留空
- 大类内占比：ratio_in_category 转为百分比
- 全组合目标占比（推导）：若大类目标比例已知，则 `ratio × ratio_in_category` 转为百分比；否则留空
- 定投日：day_of_week
- 长期/中期/短期：对应字段原样输出
- 当前持有：current_holding

表格下方输出小计行：
- `小计（{大类}）当前持有：{该大类 current_holding 合计}`

### 3.5 定投计划持仓合计
输出无序列表：
- 定投计划当前持有合计：{investment_plan current_holding 合计}
- 其中：{按大类列出合计，如“债券 4266.79 / 中股 10947.06 …”}

### 4. 非定投持仓（non_investment_holdings）
输出表格：
| 大类 | 子类 | 标的 | 当前持有 |
|---|---|---|---:|
末尾输出小计：
- `小计（非定投）当前持有：{non_investment_holdings current_holding 合计}`

### 5. 组合现状与偏离（按“全部持仓”口径）
先输出一句总计：
- `全部持仓（定投计划 + 非定投）合计：{总额}`

再输出偏离表（列名与顺序必须一致）：
| 大类 | 目标比例 | 目标金额（按 {总额} 推算） | 当前金额 | 偏离（当前-目标） | 当前占比 |
|---|---:|---:|---:|---:|---:|

计算规则：
- 总额 = investment_plan.current_holding 合计 + non_investment_holdings.current_holding 合计
- 当前金额：该 category 在两处持仓的合计
- 目标比例：来自 allocation_summary；若该 category 无目标比例，写 `0%（未设目标）`，并且目标金额留空
- 目标金额：总额 × ratio（仅对有目标比例的 category 计算）
- 偏离：当前金额 - 目标金额（仅对有目标比例的 category 计算；否则留空）
- 当前占比：当前金额 / 总额

表格后输出“解读要点”小节（无序列表，3–6 条，严格基于表格数值，不扩写）：
- 指出明显高配/低配的大类及偏离量
- 若存在“目标比例合计不为 100%”或“某大类目标缺失”，在此说明
- 若存在大类内占比加总误差（如 0.33×3=0.99），在此说明并给出可选修正方式（只写数学调整，不写投资建议）

### 6. 周定投落地（已给定的信息可直接推导）
仅基于 `allocation_summary[].weekly_amount_target` 与 `investment_plan[].ratio_in_category` 推导“每只标的的周定投金额”，规则：
1. 仅对 weekly_amount_target 非空的大类输出本节内容；若全部为空，写：`目前未设置任何大类的周定投目标。`
2. 对某大类：若 investment_plan 中存在该大类的条目，则按 `weekly_amount_target × ratio_in_category` 拆分到每个标的，并按其 `day_of_week` 标注。
3. 若某条 investment_plan 自带 `weekly_amount` 且非空，则优先使用该值，不再按比例拆分，并在该行金额后加 `（来自 weekly_amount）`。

输出格式示例（按大类分别输出）：
- `目前仅设置“{大类} {金额}/周”。按大类内占比拆分：`
  - `{标的1}：{金额}/周（{周几}）`
  - `{标的2}：{金额}/周（{周几}）`

---

## 文件保存要求 (Save to File)
1. 将你最终生成的 Markdown 原文保存为本地文件：
   - 路径：`/Users/cai/Desktop/SynologyDrive/Project/#ProjectLife-000000-理财/投资策略.md`
2. 回复中仅输出两部分：
   - 第一部分：完整 Markdown 内容（与保存文件内容一致）
   - 第二部分：一行确认信息：`已保存：/Users/cai/Desktop/SynologyDrive/Project/#ProjectLife-000000-理财/投资策略.md`
