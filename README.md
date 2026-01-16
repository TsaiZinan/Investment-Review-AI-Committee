# Investment Review AI Committee

An automated system for aggregating, comparing, and analyzing investment advice from multiple AI models to form a robust decision-making framework.

## Overview

This project uses a multi-stage pipeline to generate investment insights:

1.  **Single AI Analysis**: Individual AI models generate specific investment advice based on a core strategy.
2.  **Daily Consensus**: A "Committee" aggregator compares advice from all models for a given day to find consensus and divergence.
3.  **Weekly Trends**: A trend analyzer looks at daily summaries over a week to identify stable trends and changes.

## Workflow

### 1. Daily Single AI Analysis
**Prompt:** `1每日单AI投资分析prompt.md`

-   **Role**: Global Macro Asset Allocation Consultant.
-   **Input**: `Data/投资策略.xlsx` (converted to `投资策略.json`).
-   **Process**:
    1.  Convert Excel strategy to JSON.
    2.  Generate an investment brief.
    3.  Produce a structured investment advice report.
-   **Output**: `报告/YYYY-MM-DD/YYYY-MM-DD_{ModelName}_投资建议.md`

### 2. Daily Summary Aggregation
**Prompt:** `2每日总结分析prompt.md`

-   **Role**: Investment Suggestion Aggregator.
-   **Input**: All `*_投资建议.md` files in `报告/YYYY-MM-DD/`.
-   **Process**:
    -   Normalizes model names.
    -   Compares "Category Allocation" and "Per-Item Plan".
    -   Identifies "New Directions".
    -   Calculates consensus (Consistent/Divergent).
-   **Output**: `每日最终报告/YYYY-MM-DD_最终投资总结.md`

### 3. Weekly Trend Analysis
**Prompt:** `3每周总结分析prompt.md`

-   **Role**: Investment Suggestion Weekly Reporter.
-   **Input**: `每日最终报告/YYYY-MM-DD_最终投资总结.md` files for the target week.
-   **Process**:
    -   Analyzes trends (Up/Down/Stable) for allocations and items.
    -   Tracks consensus changes from start to end of the week.
    -   Merges "New Directions" to see persistence.
-   **Output**: `每周分析报告/START~END_每周投资总结.md`

## Directory Structure

-   `Data/`: Contains the source investment strategy (`投资策略.xlsx`).
-   `Prompt/`: Helper prompts for data conversion and brief generation.
-   `报告/`: Stores daily outputs from individual models, organized by date.
-   `每日最终报告/`: Stores the aggregated daily summaries.
-   `每周分析报告/`: Stores the weekly trend analysis reports.
-   `*.md`: Root level prompt files defining the core logic.

## Usage

1.  **Prepare Data**: Ensure `Data/投资策略.xlsx` is up to date.
2.  **Run Models**: Use an AI client (capable of reading/writing files) with `1每日单AI投资分析prompt.md` to generate advice for a specific model (e.g., GPT-4, Claude 3, etc.). Repeat for multiple models.
3.  **Generate Daily Summary**: Use an AI client with `2每日总结分析prompt.md` to aggregate that day's reports.
4.  **Generate Weekly Summary**: At the end of the week, use an AI client with `3每周总结分析prompt.md` to analyze the week's trends.

## Features

-   **Standardized Workflow**: Strict file naming and folder structure ensure automation reliability.
-   **Consensus Engine**: Statistically determines if models agree or disagree on specific assets.
-   **Trend Tracking**: Visualizes how advice changes over time (e.g., "Increasing", "Stable", "Oscillating").
-   **Model Normalization**: Handles various model naming conventions (e.g., "DeepSeek-V3" -> "DeepSeek") for clean reporting.

---

# 投资审查 AI 委员会 (Investment Review AI Committee)

这是一个自动化系统，用于聚合、比较和分析来自多个 AI 模型的投资建议，从而构建一个稳健的决策框架。

## 项目概述

本项目采用多阶段流程来生成投资洞察：

1.  **单 AI 分析 (Single AI Analysis)**：单体 AI 模型基于核心策略生成具体的投资建议。
2.  **每日共识 (Daily Consensus)**：“委员会”聚合器对比当日所有模型的建议，找出共识与分歧点。
3.  **每周趋势 (Weekly Trends)**：趋势分析器回顾一周内的每日总结，识别稳定的趋势与变化。

## 工作流

### 1. 每日单 AI 分析
**提示词 (Prompt):** `1每日单AI投资分析prompt.md`

-   **角色**: 全球宏观资产配置顾问。
-   **输入**: `Data/投资策略.xlsx` (转换为 `投资策略.json`)。
-   **流程**:
    1.  将 Excel 策略转换为 JSON。
    2.  生成投资简报。
    3.  产出结构化的投资建议报告。
-   **输出**: `报告/YYYY-MM-DD/YYYY-MM-DD_{ModelName}_投资建议.md`

### 2. 每日总结聚合
**提示词 (Prompt):** `2每日总结分析prompt.md`

-   **角色**: 投资建议汇总器。
-   **输入**: `报告/YYYY-MM-DD/` 目录下的所有 `*_投资建议.md` 文件。
-   **流程**:
    -   归一化模型名称。
    -   对比“大板块比例”与“逐项定投计划”。
    -   识别“新增定投方向”。
    -   计算共识情况（一致/分歧）。
-   **输出**: `每日最终报告/YYYY-MM-DD_最终投资总结.md`

### 3. 每周趋势分析
**提示词 (Prompt):** `3每周总结分析prompt.md`

-   **角色**: 投资建议周报汇总器。
-   **输入**: 目标周内的 `每日最终报告/YYYY-MM-DD_最终投资总结.md` 文件。
-   **流程**:
    -   分析大板块与标的的趋势（上行/下行/稳定）。
    -   追踪周初至周末的共识变化。
    -   合并“新增方向”以观察持续性。
-   **输出**: `每周分析报告/START~END_每周投资总结.md`

## 目录结构

-   `Data/`: 存放源投资策略文件 (`投资策略.xlsx`)。
-   `Prompt/`: 存放用于数据转换和简报生成的辅助提示词。
-   `报告/`: 按日期存放各 AI 模型生成的每日输出。
-   `每日最终报告/`: 存放聚合后的每日最终总结。
-   `每周分析报告/`: 存放每周趋势分析报告。
-   `*.md`: 根目录下的提示词文件，定义了核心逻辑。

## 使用说明

1.  **准备数据**: 确保 `Data/投资策略.xlsx` 是最新的。
2.  **运行模型**: 使用支持读写文件的 AI 客户端，配合 `1每日单AI投资分析prompt.md` 为特定模型（如 GPT-4, Claude 3 等）生成建议。对多个模型重复此步骤。
3.  **生成日总结**: 使用 AI 客户端配合 `2每日总结分析prompt.md` 聚合当天的所有报告。
4.  **生成周总结**: 在周末，使用 AI 客户端配合 `3每周总结分析prompt.md` 分析本周趋势。

## 功能特性

-   **标准化工作流**: 严格的文件命名与文件夹结构保证了自动化的可靠性。
-   **共识引擎**: 统计判断模型在具体资产上是否达成一致或存在分歧。
-   **趋势追踪**: 可视化建议随时间的变化（例如：“上行”、“稳定”、“震荡”）。
-   **模型归一化**: 处理多样的模型命名习惯（例如将 "DeepSeek-V3" 统一为 "DeepSeek"）以生成整洁的报告。
