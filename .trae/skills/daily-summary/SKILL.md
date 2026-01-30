---
name: "daily-summary"
description: "触发语：每日总结 / 开始每日总结聚合。聚合当日各模型投资建议，输出每日最终报告。"
---

# 每日总结聚合器

当用户输入“每日总结”（或表达要开始每日总结聚合）时，执行本技能。

本技能会读取 `报告/YYYY-MM-DD/` 下所有 `YYYY-MM-DD_{ModelName}_投资建议.md`，横向对比并生成 `每日最终报告/YYYY-MM-DD_最终投资总结.md`。
输出报告将包含一段“定投增减要点综述”（1000字以内，单段落），用于汇总当天各模型的 Top SIP Changes。

## 执行流程

### 步骤0：确认日期与模型
- 向用户提问：`🤔即将对日期 {YYYY-MM-DD} 进行每日总结聚合。请确认今日已运行的模型是否完整？`
- 提供备选列表供用户参考：`DeepSeek, Gemini, GPT-5.2, Grok-4, GLM-4.7, Kimi, MiniMax-M2.1, TraeAI`
- 若用户未提供日期，默认使用今天的本地日期（`YYYY-MM-DD`）
- 必须等待用户回复确认（如“确认”、“ok”或补充说明）

### 步骤1：检查输入文件
- 输入目录：`报告/{YYYY-MM-DD}/`
- 必须至少存在 1 份当日的 `*_投资建议.md` 文件；若不存在则直接提示用户先完成“每日分析”

### 步骤2：标的与数据源一致性校验（开始时必须执行）
- 数据源：`报告/{YYYY-MM-DD}/投资策略.json` 的 `investment_plan[*].fund_name`
- 运行命令（必须在项目根目录执行）：
  - `python scripts/generate_daily_summary.py --date "{YYYY-MM-DD}" --validate-only`
- 若输出提示“标的校验：发现与数据源不一致”（或命令非 0 退出）：
  - 必须向用户清晰列出每份报告的差异（报告多出 / 报告缺失 / 名称不一致但已匹配）
  - 必须等待用户决定下一步（修正报告/更新数据源/确认忽略差异继续）

### 步骤3：生成每日最终报告
- 仅在用户确认继续后运行：
  - `python scripts/generate_daily_summary.py --date "{YYYY-MM-DD}" --force --publish`

### 步骤4：校验输出
- 输出文件必须存在：
  - `每日最终报告/{YYYY-MM-DD}_最终投资总结.md`
- 若命令输出提示 “No files matching pattern” 或输入目录不存在：返回清晰的缺失清单（缺哪一天、缺哪些模型文件）

### 步骤5：上传 GitHub
- 若步骤3使用了 `--publish`，脚本会对当日生成的最终报告执行 `git add/commit/push`
