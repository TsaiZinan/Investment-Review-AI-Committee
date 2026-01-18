import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parent
DATE = date.today().isoformat()
INPUT_DIR = ROOT / "报告" / DATE
OUTPUT_PATH = ROOT / "每日最终报告" / f"{DATE}_最终投资总结.md"


FILE_RE = re.compile(rf"^{re.escape(DATE)}_(.+)_投资建议\.md$")

MODEL_ORDER_FIXED = [
    "DeepSeek",
    "Gemini",
    "GPT-5.2",
    "Grok-4",
    "GLM-4.7",
    "Kimi",
    "MiniMax-M2.1",
    "TraeAI",
]

CATEGORY_ORDER_FIXED = ["债券", "中股", "期货", "美股"]


def canonicalize_model(raw_model: str) -> str:
    s = raw_model.strip()
    low = s.lower()
    if low.startswith("gemini"):
        return "Gemini"
    if low.startswith("kimi"):
        return "Kimi"
    if low.startswith("minimax"):
        return "MiniMax-M2.1"
    if low.startswith("traeai"):
        return "TraeAI"
    if low.startswith("deepseek"):
        return "DeepSeek"
    if low.startswith("grok"):
        return "Grok-4"
    if low.startswith("glm"):
        return "GLM-4.7"
    return s


def model_columns(models_present: List[str]) -> List[str]:
    fixed = [m for m in MODEL_ORDER_FIXED if m in models_present]
    others = sorted([m for m in models_present if m not in MODEL_ORDER_FIXED])
    return fixed + others


def parse_float_from_text(s: str) -> Optional[float]:
    if not s:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", s.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def format_pct(x: float) -> str:
    return f"{x:.2f}%"


def parse_markdown_table(lines: List[str]) -> List[List[str]]:
    rows: List[List[str]] = []
    for ln in lines:
        if not ln.strip().startswith("|"):
            continue
        parts = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(parts) <= 1:
            continue
        rows.append(parts)
    return rows


def is_separator_row(row: List[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) is not None for c in row)


def find_table_after_heading(text: str, heading_substring: str) -> Tuple[Optional[List[List[str]]], str]:
    lines = text.splitlines()
    start_idx = None
    for i, ln in enumerate(lines):
        if heading_substring in ln:
            start_idx = i
            break
    if start_idx is None:
        return None, ""

    post_lines = lines[start_idx + 1 :]
    first_table_line = None
    for j, ln in enumerate(post_lines):
        if ln.strip().startswith("|") and "|" in ln.strip()[1:]:
            first_table_line = start_idx + 1 + j
            break
        if ln.strip().startswith("#") and j > 0:
            break

    if first_table_line is None:
        return None, "\n".join(post_lines)

    table_lines: List[str] = []
    k = first_table_line
    while k < len(lines):
        ln = lines[k]
        if ln.strip().startswith("|"):
            table_lines.append(ln)
            k += 1
            continue
        break

    parsed = parse_markdown_table(table_lines)
    remaining = "\n".join(lines[k : min(len(lines), k + 80)])
    return (parsed if parsed else None), remaining


def find_col(header: List[str], includes: List[str], excludes: List[str] = []) -> Optional[int]:
    for i, h in enumerate(header):
        hh = h.strip()
        if any(ex in hh for ex in excludes):
            continue
        if all(inc in hh for inc in includes):
            return i
    return None


@dataclass
class CellCandidate:
    display: str
    pct: Optional[float]
    direction_raw: Optional[str]
    direction_stat: Optional[str]
    raw_model: str


@dataclass
class ThemeEntry:
    topic: str
    topic_norm: str
    pct: Optional[float]
    caliber: str
    display: str
    raw_model: str


def direction_to_stat(direction: Optional[str], *, is_category: bool) -> Optional[str]:
    if not direction:
        return None
    d = direction.strip()

    if "维持" in d or "不变" in d or "保持" in d:
        return "不变"

    if is_category:
        if "小幅增配" in d:
            return "增"
        if "小幅减配" in d:
            return "减"
        if "增配" in d:
            return "增"
        if "减配" in d:
            return "减"
    else:
        if "增持" in d:
            return "增"
        if "减持" in d:
            return "减"

    if "增" in d:
        return "增"
    if "减" in d or "暂停" in d or "停止" in d:
        return "减"
    return "不变"


def cell_display(pct: Optional[float], direction: Optional[str]) -> str:
    if pct is None and direction is None:
        return "—"
    if pct is None and direction is not None:
        return f"—（{direction}）"
    pct_s = format_pct(pct) if pct is not None else "—"
    d_s = direction if direction is not None else "—"
    return f"{pct_s}（{d_s}）"


def parse_categories(text: str, raw_model: str) -> Tuple[List[str], Dict[str, CellCandidate]]:
    table, _ = find_table_after_heading(text, "大板块比例调整建议")
    if not table or len(table) < 2:
        return [], {}
    header = table[0]
    body = table[1:]
    if body and is_separator_row(body[0]):
        body = body[1:]

    key_col = find_col(header, ["大板块"])
    pct_col = find_col(header, ["建议%"])
    dir_col = find_col(header, ["建议"], excludes=["建议%"])
    if key_col is None or pct_col is None or dir_col is None:
        return [], {}

    order: List[str] = []
    out: Dict[str, CellCandidate] = {}
    for row in body:
        if len(row) <= max(key_col, pct_col, dir_col):
            continue
        key = row[key_col].strip()
        if not key:
            continue
        pct = parse_float_from_text(row[pct_col])
        direction = row[dir_col].strip() or None
        out[key] = CellCandidate(
            display=cell_display(pct, direction),
            pct=pct,
            direction_raw=direction,
            direction_stat=direction_to_stat(direction, is_category=True),
            raw_model=raw_model,
        )
        order.append(key)
    return order, out


def parse_items(text: str, raw_model: str) -> Tuple[List[str], Dict[str, CellCandidate]]:
    table, _ = find_table_after_heading(text, "定投计划逐项建议")
    if not table or len(table) < 2:
        return [], {}
    header = table[0]
    body = table[1:]
    if body and is_separator_row(body[0]):
        body = body[1:]

    key_col = find_col(header, ["标的"])
    pct_col = find_col(header, ["建议%"])
    dir_col = find_col(header, ["建议"], excludes=["建议%"])
    if key_col is None or pct_col is None or dir_col is None:
        return [], {}

    order: List[str] = []
    out: Dict[str, CellCandidate] = {}
    for row in body:
        if len(row) <= max(key_col, pct_col, dir_col):
            continue
        key = row[key_col].strip()
        if not key:
            continue
        pct = parse_float_from_text(row[pct_col])
        direction = row[dir_col].strip() or None
        out[key] = CellCandidate(
            display=cell_display(pct, direction),
            pct=pct,
            direction_raw=direction,
            direction_stat=direction_to_stat(direction, is_category=False),
            raw_model=raw_model,
        )
        order.append(key)
    return order, out


def normalize_topic_name(s: str) -> str:
    if not s:
        return ""
    t = unicodedata.normalize("NFKC", s)
    t = t.strip().lower()
    t = t.replace("（", "(").replace("）", ")")
    t = re.sub(r"\s+", "", t)
    for w in ["etf", "指数", "基金", "定投", "主题", "方向", "板块", "赛道", "相关", "概念"]:
        t = t.replace(w, "")
    t = re.sub(r'[\[\]{}<>《》“”"\'`]', "", t)
    t = t.replace("(", "").replace(")", "")
    return t


def topic_tokens(norm: str) -> List[str]:
    if not norm:
        return []
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9]{2,}", norm)
    if len(tokens) >= 2:
        return tokens
    if len(norm) >= 2:
        return [norm[i : i + 2] for i in range(len(norm) - 1)]
    return [norm]


def parse_themes(text: str, raw_model: str) -> Tuple[List[ThemeEntry], bool]:
    table, remaining = find_table_after_heading(text, "新的定投方向建议")
    explicitly_no_new = bool(re.search(r"本周期不新增|不新增|无新增|无需新增", remaining))
    if not table:
        return [], explicitly_no_new

    header = table[0]
    body = table[1:]
    if body and is_separator_row(body[0]):
        body = body[1:]

    topic_col = None
    for key in ["主题/方向", "行业/主题", "行业", "主题", "方向"]:
        for i, h in enumerate(header):
            if key in h:
                topic_col = i
                break
        if topic_col is not None:
            break

    pct_col = None
    for i, h in enumerate(header):
        if "比例" in h:
            pct_col = i
            break

    caliber_col = None
    for i, h in enumerate(header):
        if "口径" in h:
            caliber_col = i
            break

    if topic_col is None or pct_col is None or caliber_col is None:
        return [], explicitly_no_new

    entries: List[ThemeEntry] = []
    for row in body:
        if len(row) <= max(topic_col, pct_col, caliber_col):
            continue
        topic = row[topic_col].strip()
        if not topic or topic in ["无", "—", "-"]:
            continue
        pct = parse_float_from_text(row[pct_col])
        caliber = row[caliber_col].strip() or "—"
        display = "—"
        if pct is not None:
            display = f"{format_pct(pct)}（{caliber}）"
        entries.append(
            ThemeEntry(
                topic=topic,
                topic_norm=normalize_topic_name(topic),
                pct=pct,
                caliber=caliber,
                display=display,
                raw_model=raw_model,
            )
        )

    return entries, explicitly_no_new


def select_best_candidate(cands: List[CellCandidate]) -> Optional[CellCandidate]:
    if not cands:
        return None

    non_missing = [c for c in cands if c.display.strip() != "—"]
    pool = non_missing if non_missing else cands
    max_len = max(len(c.display or "") for c in pool)
    longest = [c for c in pool if len(c.display or "") == max_len]
    longest.sort(key=lambda c: c.raw_model, reverse=True)
    return longest[0]


def summarize_consensus(candidates: List[Optional[CellCandidate]]) -> Tuple[str, str]:
    usable = [c for c in candidates if c and c.direction_stat]
    if not usable:
        return "分歧（无明显偏向）", "数据不足；范围 —–—"

    counts = {"增": 0, "减": 0, "不变": 0}
    pcts: List[float] = []
    for c in usable:
        if c.direction_stat in counts:
            counts[c.direction_stat] += 1
        if c.pct is not None:
            pcts.append(c.pct)

    n = len(usable)
    max_vote = max(counts.values())
    top_dirs = [k for k, v in counts.items() if v == max_vote]

    if len(top_dirs) == 1:
        bias = {"增": "偏增", "减": "偏减", "不变": "偏不变"}[top_dirs[0]]
        bias_for_consensus = {"增": "增", "减": "减", "不变": "不变"}[top_dirs[0]]
    else:
        bias = "无明显偏向"
        bias_for_consensus = "无明显偏向"

    if n == 1:
        consistency = f"分歧（{bias}）"
    elif max_vote == n:
        consistency = f"一致（{bias_for_consensus}）"
    elif max_vote / n >= 0.75:
        consistency = f"基本一致（{bias}）"
    else:
        consistency = f"分歧（{bias}）"

    if pcts:
        lo, hi = min(pcts), max(pcts)
        range_part = f"范围 {format_pct(lo)}–{format_pct(hi)}"
    else:
        range_part = "范围 —–—"

    if n == 1 and pcts:
        summary = f"数据不足；范围 {format_pct(pcts[0])}–{format_pct(pcts[0])}"
    elif n == 1:
        summary = f"数据不足；{range_part}"
    else:
        summary = f"{counts['增']}增/{counts['减']}减/{counts['不变']}不变；{range_part}"

    return consistency, summary


def render_table(headers: List[str], rows: List[List[str]]) -> str:
    def esc(s: str) -> str:
        return (s or "—").replace("\n", " ").strip()

    out = []
    out.append("| " + " | ".join(esc(h) for h in headers) + " |")
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        out.append("| " + " | ".join(esc(c) for c in r) + " |")
    return "\n".join(out)


@dataclass
class ThemeGroup:
    names: List[str]
    norms: List[str]
    tokens: set
    per_model: Dict[str, List[ThemeEntry]]


def is_similar_topic(entry: ThemeEntry, group: ThemeGroup) -> bool:
    if not entry.topic_norm:
        return False
    if entry.topic_norm in group.norms:
        return True
    for gn in group.norms:
        if gn and (entry.topic_norm in gn or gn in entry.topic_norm):
            return True
    common = set(topic_tokens(entry.topic_norm)) & group.tokens
    return len(common) >= 2


def pick_main_name(names: List[str]) -> str:
    freq: Dict[str, int] = {}
    for n in names:
        freq[n] = freq.get(n, 0) + 1
    return sorted(freq.items(), key=lambda kv: (-kv[1], len(kv[0]), kv[0]))[0][0]


def closeness(entry: ThemeEntry, main_norm: str) -> Tuple[int, int, str]:
    en = entry.topic_norm
    if en == main_norm:
        return (0, -len(entry.display), entry.topic)
    if en and main_norm and (en in main_norm or main_norm in en):
        return (1, -len(entry.display), entry.topic)
    common = len(set(topic_tokens(en)) & set(topic_tokens(main_norm)))
    return (2, -common, entry.topic)


def collect_files() -> List[Tuple[Path, str]]:
    if not INPUT_DIR.exists():
        raise SystemExit(f"Input dir not found: {INPUT_DIR}")
    found: List[Tuple[Path, str]] = []
    for p in INPUT_DIR.iterdir():
        if not p.is_file():
            continue
        m = FILE_RE.match(p.name)
        if not m:
            continue
        found.append((p, m.group(1)))
    found.sort(key=lambda x: x[0].name)
    return found


def main() -> None:
    files = collect_files()
    if not files:
        raise SystemExit(f"No input files matched in {INPUT_DIR}")

    models_present: List[str] = []
    parsed: List[Tuple[str, str, str]] = []
    for path, raw_model in files:
        parsed.append((path.read_text(encoding="utf-8"), raw_model, canonicalize_model(raw_model)))
        models_present.append(canonicalize_model(raw_model))

    model_cols = model_columns(sorted(set(models_present)))

    cat_cands: Dict[str, Dict[str, List[CellCandidate]]] = {m: {} for m in model_cols}
    item_cands: Dict[str, Dict[str, List[CellCandidate]]] = {m: {} for m in model_cols}

    first_seen_item: Dict[str, int] = {}
    all_cats: set = set()
    all_items: set = set()

    model_theme_entries: Dict[str, List[ThemeEntry]] = {m: [] for m in model_cols}
    model_no_new: Dict[str, bool] = {m: False for m in model_cols}

    for text, raw_model, canon in parsed:
        cat_order, cats = parse_categories(text, raw_model)
        for key in cat_order:
            all_cats.add(key)
        for key, cand in cats.items():
            cat_cands.setdefault(canon, {}).setdefault(key, []).append(cand)

        item_order, items = parse_items(text, raw_model)
        for key in item_order:
            if key not in first_seen_item:
                first_seen_item[key] = len(first_seen_item)
        for key, cand in items.items():
            all_items.add(key)
            item_cands.setdefault(canon, {}).setdefault(key, []).append(cand)

        themes, explicitly_no_new = parse_themes(text, raw_model)
        model_no_new[canon] = model_no_new.get(canon, False) or explicitly_no_new
        for te in themes:
            model_theme_entries.setdefault(canon, []).append(te)

    cats = list(all_cats)
    cat_priority = {name: i for i, name in enumerate(CATEGORY_ORDER_FIXED)}
    cats.sort(key=lambda k: (0, cat_priority[k]) if k in cat_priority else (1, k))

    items = list(all_items)
    items.sort(key=lambda k: (first_seen_item.get(k, 10**9), k))

    cat_headers = ["大板块"] + model_cols + ["一致性", "分歧摘要"]
    cat_rows: List[List[str]] = []
    cat_rows_consensus: List[List[str]] = []
    for cat in cats:
        row_cells = [cat]
        merged_candidates: List[Optional[CellCandidate]] = []
        for model in model_cols:
            best = select_best_candidate(cat_cands.get(model, {}).get(cat, []))
            merged_candidates.append(best)
            row_cells.append(best.display if best else "—")
        consistency, summary = summarize_consensus(merged_candidates)
        row_cells += [consistency, summary]
        cat_rows.append(row_cells)
        if consistency.startswith("一致") or consistency.startswith("基本一致"):
            cat_rows_consensus.append(row_cells)

    item_headers = ["标的"] + model_cols + ["一致性", "分歧摘要"]
    item_rows: List[List[str]] = []
    item_rows_consensus: List[List[str]] = []
    for item in items:
        row_cells = [item]
        merged_candidates = []
        for model in model_cols:
            best = select_best_candidate(item_cands.get(model, {}).get(item, []))
            merged_candidates.append(best)
            row_cells.append(best.display if best else "—")
        consistency, summary = summarize_consensus(merged_candidates)
        row_cells += [consistency, summary]
        item_rows.append(row_cells)
        if consistency.startswith("一致") or consistency.startswith("基本一致"):
            item_rows_consensus.append(row_cells)

    groups: List[ThemeGroup] = []
    for model in model_cols:
        for te in model_theme_entries.get(model, []):
            placed = False
            for g in groups:
                if is_similar_topic(te, g):
                    g.names.append(te.topic)
                    g.norms.append(te.topic_norm)
                    g.tokens |= set(topic_tokens(te.topic_norm))
                    g.per_model.setdefault(model, []).append(te)
                    placed = True
                    break
            if not placed:
                groups.append(
                    ThemeGroup(
                        names=[te.topic],
                        norms=[te.topic_norm],
                        tokens=set(topic_tokens(te.topic_norm)),
                        per_model={model: [te]},
                    )
                )

    theme_headers = ["主题/方向"] + model_cols + ["异同"]
    theme_rows: List[List[str]] = []

    group_meta = []
    for g in groups:
        main = pick_main_name(g.names)
        proposers = [m for m in model_cols if m in g.per_model]
        group_meta.append((g, main, proposers))
    group_meta.sort(key=lambda x: (-len(x[2]), x[1]))

    for g, main, proposers in group_meta:
        main_norm = normalize_topic_name(main)
        row = [main]
        diff_parts: List[str] = []

        distinct_names = sorted(set(g.names), key=lambda s: (len(s), s))
        if len(distinct_names) > 1:
            diff_parts.append("合并：" + " / ".join(distinct_names))

        for model in model_cols:
            entries = g.per_model.get(model, [])
            if not entries:
                row.append("—")
                continue
            best = sorted(entries, key=lambda e: closeness(e, main_norm))[0]
            row.append(best.display)
            others = [e for e in entries if e is not best]
            if others:
                other_names = sorted({o.topic for o in others})
                diff_parts.append(f"{model} 另提：" + " / ".join(other_names))

        if len(proposers) == 1:
            diff_parts.append(f"仅 {proposers[0]} 提出")

        no_new_models = [m for m in model_cols if model_no_new.get(m) and m not in proposers]
        if no_new_models:
            diff_parts.append("其中 " + " / ".join(no_new_models) + " 明确不新增")

        row.append("；".join(diff_parts) if diff_parts else "—")
        theme_rows.append(row)

    md_parts: List[str] = []
    md_parts.append(f"# 投资总结（{DATE}）")
    md_parts.append("")
    md_parts.append("## 1. 大板块比例调整建议（按大类横向对比）")
    md_parts.append(render_table(cat_headers, cat_rows))
    md_parts.append("")
    md_parts.append("### 一致建议")
    md_parts.append(render_table(cat_headers, cat_rows_consensus))
    md_parts.append("")
    md_parts.append("## 2. 定投计划逐项建议（按标的横向对比）")
    md_parts.append(render_table(item_headers, item_rows))
    md_parts.append("")
    md_parts.append("### 一致建议")
    md_parts.append(render_table(item_headers, item_rows_consensus))
    md_parts.append("")
    md_parts.append("## 3. 新的定投方向建议（按主题横向对比）")
    md_parts.append(render_table(theme_headers, theme_rows))
    md_parts.append("")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(md_parts), encoding="utf-8")


if __name__ == "__main__":
    main()

