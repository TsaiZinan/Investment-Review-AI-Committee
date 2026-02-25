import argparse
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
 
 
ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "每日最终报告"
OUTPUT_DIR = ROOT / "每周分析报告"
 
FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_最终投资总结\.md$")
 
 
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
 
 
def parse_markdown_table(table_lines: List[str]) -> List[List[str]]:
    rows: List[List[str]] = []
    for ln in table_lines:
        if not ln.strip().startswith("|"):
            continue
        parts = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(parts) <= 1:
            continue
        rows.append(parts)
    return rows
 
 
def is_separator_row(row: List[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) is not None for c in row)
 
 
def find_table_after_heading(text: str, heading_substring: str) -> Optional[List[List[str]]]:
    lines = text.splitlines()
    start_idx = None
    for i, ln in enumerate(lines):
        if heading_substring in ln:
            start_idx = i
            break
    if start_idx is None:
        return None
 
    post_lines = lines[start_idx + 1 :]
    first_table_line = None
    for j, ln in enumerate(post_lines):
        if ln.strip().startswith("|") and "|" in ln.strip()[1:]:
            first_table_line = start_idx + 1 + j
            break
        if ln.strip().startswith("#") and j > 0:
            break
    if first_table_line is None:
        return None
 
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
    return parsed if parsed else None
 
 
def normalize_text(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip()
 
 
def parse_cell(cell: str) -> Tuple[Optional[float], Optional[str], str]:
    raw = normalize_text(cell)
    if not raw or raw == "—":
        return None, None, "—"
 
    pct = parse_float_from_text(raw)
    inner = None
    m = re.search(r"[（(]\s*([^）)]+?)\s*[）)]", raw)
    if m:
        inner = m.group(1).strip() or None
    disp = "—"
    if pct is None and inner is None:
        disp = "—"
    elif pct is None and inner is not None:
        disp = f"—（{inner}）"
    else:
        pct_s = format_pct(pct if pct is not None else 0.0) if pct is not None else "—"
        disp = f"{pct_s}（{inner or '—'}）"
    return pct, inner, disp
 
 
def direction_to_stat(direction: Optional[str], *, is_category: bool) -> Optional[str]:
    if not direction:
        return None
    d = direction.strip()
    if any(x in d for x in ["维持", "不变", "保持"]):
        return "不变"
    if is_category:
        if "小幅增配" in d:
            return "增"
        if "大幅增配" in d:
            return "增"
        if "小幅减配" in d:
            return "减"
        if "大幅减配" in d:
            return "减"
        if "增配" in d:
            return "增"
        if "减配" in d:
            return "减"
    else:
        if "暂停" in d:
            return "减"
        if "清仓" in d:
            return "减"
        if "增持" in d:
            return "增"
        if "减持" in d:
            return "减"
    if "增" in d:
        return "增"
    if "减" in d:
        return "减"
    return "不变"
 
 
def _choose_cell(candidates: List[Tuple[str, str]]) -> str:
    if not candidates:
        return "—"
    non_missing = [(v, raw_model) for v, raw_model in candidates if normalize_text(v) not in ("", "—")]
    if non_missing:
        non_missing.sort(key=lambda x: (len(normalize_text(x[0])), x[1]))
        return non_missing[-1][0]
    candidates.sort(key=lambda x: x[1])
    return candidates[-1][0]
 
 
def dedupe_models(header: List[str], model_indices: List[int]) -> Tuple[List[str], Dict[str, List[int]]]:
    canonical_to_indices: Dict[str, List[int]] = {}
    for idx in model_indices:
        raw = header[idx].strip()
        can = canonicalize_model(raw)
        canonical_to_indices.setdefault(can, []).append(idx)
    models = sorted(canonical_to_indices.keys())
    return models, canonical_to_indices
 
 
@dataclass(frozen=True)
class RowDaily:
    pct_by_model: Dict[str, Optional[float]]
    dir_raw_by_model: Dict[str, Optional[str]]
    disp_by_model: Dict[str, str]
 
 
def extract_wide_table(
    table: List[List[str]],
    *,
    key_header: str,
    tail_headers: Sequence[str],
) -> Tuple[List[str], List[str], Dict[str, Dict[str, str]]]:
    header = table[0]
    body = table[1:]
    if body and is_separator_row(body[0]):
        body = body[1:]
 
    key_col = None
    for i, h in enumerate(header):
        if key_header in h:
            key_col = i
            break
    if key_col is None:
        return [], [], {}
 
    tail_start = len(header)
    for i, h in enumerate(header):
        if any(x in h for x in tail_headers):
            tail_start = min(tail_start, i)
    model_indices = [i for i in range(len(header)) if i != key_col and i < tail_start]
    models, canonical_to_indices = dedupe_models(header, model_indices)
 
    keys: List[str] = []
    cells: Dict[str, Dict[str, str]] = {}
    for row in body:
        if len(row) <= key_col:
            continue
        key = row[key_col].strip()
        if not key:
            continue
        keys.append(key)
        per_model: Dict[str, str] = {}
        for can_model, idxs in canonical_to_indices.items():
            cands: List[Tuple[str, str]] = []
            for idx in idxs:
                if idx < len(row):
                    cands.append((row[idx], header[idx].strip()))
            per_model[can_model] = _choose_cell(cands)
        cells[key] = per_model
    return keys, models, cells
 
 
def calc_main_direction(
    dir_stats: Iterable[Optional[str]],
    *,
    label_inc: str,
    label_dec: str,
) -> Optional[str]:
    counts = {"增": 0, "减": 0, "不变": 0}
    for d in dir_stats:
        if d in counts:
            counts[d] += 1
    total = sum(counts.values())
    if total == 0:
        return None
    max_v = max(counts.values())
    winners = [k for k, v in counts.items() if v == max_v]
    if len(winners) != 1:
        return "无明显偏向"
    if winners[0] == "增":
        return label_inc
    if winners[0] == "减":
        return label_dec
    return "不变"
 
 
def pct_range(pcts: List[float]) -> str:
    if not pcts:
        return "—"
    return f"范围 {format_pct(min(pcts))}–{format_pct(max(pcts))}"
 
 
def fmt_delta(delta: Optional[float]) -> str:
    if delta is None:
        return "—"
    return f"Δ {delta:+.2f}%"
 

def signal_score_from_main_dirs(main_dirs: List[Optional[str]], *, label_inc: str, label_dec: str) -> Optional[float]:
    inc_days = sum(1 for x in main_dirs if x == label_inc)
    dec_days = sum(1 for x in main_dirs if x == label_dec)
    flat_days = sum(1 for x in main_dirs if x == "不变")
    total = inc_days + dec_days + flat_days
    if total <= 0:
        return None
    return (inc_days - dec_days) / total


def signal_action(score: Optional[float], *, is_category: bool) -> str:
    if score is None:
        return "—"
    if score >= 0.20:
        return "增配" if is_category else "增持"
    if score <= -0.20:
        return "减配" if is_category else "减持"
    return "维持"


def signal_strength(score: Optional[float]) -> str:
    if score is None:
        return "—"
    return f"{abs(score) * 100:.2f}%"


def signal_trend(early_score: Optional[float], late_score: Optional[float], *, is_category: bool) -> str:
    if early_score is None or late_score is None:
        return "—"
    early_action = signal_action(early_score, is_category=is_category)
    late_action = signal_action(late_score, is_category=is_category)
    if early_action != late_action and early_action != "维持" and late_action != "维持":
        return f"反转：{early_action}→{late_action}"
    early_strength = abs(early_score)
    late_strength = abs(late_score)
    if late_strength - early_strength >= 0.20:
        return "变强"
    if early_strength - late_strength >= 0.20:
        return "变弱"
    return "稳定"


def signal_trend_metric(early_score: Optional[float], late_score: Optional[float], *, is_category: bool) -> Optional[float]:
    if early_score is None or late_score is None:
        return None
    early_action = signal_action(early_score, is_category=is_category)
    late_action = signal_action(late_score, is_category=is_category)
    if early_action != late_action and early_action != "维持" and late_action != "维持":
        return 1.0
    return abs(abs(late_score) - abs(early_score))

 
def trend_label(
    start_med: Optional[float],
    end_med: Optional[float],
    main_dir_series: List[Optional[str]],
) -> Tuple[str, Optional[float]]:
    if start_med is None or end_med is None:
        return "数据不足", None
    delta = end_med - start_med
    if abs(delta) < 0.5:
        label = "稳定"
    elif delta >= 0.5:
        label = "上行"
    else:
        label = "下行"
 
    cleaned = [x for x in main_dir_series if x is not None]
    changes = 0
    for a, b in zip(cleaned, cleaned[1:]):
        if a != b:
            changes += 1
    if changes >= 2:
        label = f"{label}；震荡"
    return label, delta
 
 
def direction_week_counts(
    main_dirs: List[Optional[str]],
    *,
    label_inc: str,
    label_dec: str,
) -> str:
    inc = sum(1 for x in main_dirs if x == label_inc)
    dec = sum(1 for x in main_dirs if x == label_dec)
    flat = sum(1 for x in main_dirs if x == "不变")
    nop = sum(1 for x in main_dirs if x == "无明显偏向")
    return f"增{inc}天/减{dec}天/不变{flat}天/无偏{nop}天"


def direction_arrows(
    main_dirs: List[Optional[str]],
    *,
    label_inc: str,
    label_dec: str,
) -> str:
    out = []
    for x in main_dirs:
        if x == label_inc:
            out.append("↑")
        elif x == label_dec:
            out.append("↓")
        else:
            out.append("-")
    return "".join(out) if out else "—"
 
 
def safe_median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return float(median(values))
 
 
def normalize_topic_name(topic: str) -> str:
    s = normalize_text(topic)
    s = s.lower()
    s = s.replace("（", "(").replace("）", ")")
    for w in ["etf", "指数", "基金", "定投", "主题", "方向", "板块", "赛道", "相关", "概念"]:
        s = s.replace(w, "")
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[·•、，。,;；/\\|]+", "", s)
    return s
 
 
def _topic_tokens(norm: str) -> Set[str]:
    norm = normalize_text(norm)
    tokens: Set[str] = set()
    for m in re.finditer(r"[a-z0-9]+", norm.lower()):
        if m.group(0):
            tokens.add(m.group(0))
    for m in re.finditer(r"[\u4e00-\u9fff]+", norm):
        seg = m.group(0)
        if len(seg) >= 2:
            for i in range(len(seg) - 1):
                tokens.add(seg[i : i + 2])
    return tokens
 
 
def topics_similar(a_norm: str, b_norm: str) -> bool:
    if not a_norm or not b_norm:
        return False
    if a_norm == b_norm:
        return True
    if a_norm in b_norm or b_norm in a_norm:
        return True
    a_t = _topic_tokens(a_norm)
    b_t = _topic_tokens(b_norm)
    return len(a_t & b_t) >= 2
 
 
def md_table(headers: List[str], rows: List[List[str]]) -> str:
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)
 
 
def iter_dates(start: date, end: date) -> List[date]:
    cur = start
    out = []
    while cur <= end:
        out.append(cur)
        cur += timedelta(days=1)
    return out
 
 
@dataclass
class ThemeCell:
    topic: str
    topic_norm: str
    canonical_model: str
    display: str
    day: str
    diff_text: str
 
 
def _similarity_score(topic_norm: str, main_norm: str) -> int:
    if not topic_norm or not main_norm:
        return 0
    if topic_norm == main_norm:
        return 3
    if topic_norm in main_norm or main_norm in topic_norm:
        return 2
    if len(_topic_tokens(topic_norm) & _topic_tokens(main_norm)) >= 2:
        return 1
    return 0
 
 
def compute_weekly(
    week_start: date,
    week_end: date,
) -> Tuple[str, List[Path], List[date], str]:
    files: List[Tuple[date, Path]] = []
    for p in INPUT_DIR.iterdir():
        m = FILE_RE.match(p.name)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if week_start <= d <= week_end:
            files.append((d, p))
    files.sort(key=lambda x: x[0])
    input_paths = [p for _, p in files]
    input_dates = [d for d, _ in files]
 
    missing_dates = [d for d in iter_dates(week_start, week_end) if d not in set(input_dates)]
 
    category_days: Dict[str, Dict[date, RowDaily]] = {}
    item_days: Dict[str, Dict[date, RowDaily]] = {}
    theme_cells: List[ThemeCell] = []
    theme_models: Set[str] = set()
 
    for d, p in files:
        text = p.read_text(encoding="utf-8")
 
        cat_table = find_table_after_heading(text, "大板块比例调整建议")
        if cat_table:
            keys, models, cells = extract_wide_table(cat_table, key_header="大板块", tail_headers=["一致性", "分歧", "异同"])
            for k in keys:
                per = cells.get(k, {})
                pct_by_model: Dict[str, Optional[float]] = {}
                dir_raw_by_model: Dict[str, Optional[str]] = {}
                disp_by_model: Dict[str, str] = {}
                for mname in models:
                    pct, inner, disp = parse_cell(per.get(mname, "—"))
                    pct_by_model[mname] = pct
                    dir_raw_by_model[mname] = inner
                    disp_by_model[mname] = disp
                category_days.setdefault(k, {})[d] = RowDaily(pct_by_model=pct_by_model, dir_raw_by_model=dir_raw_by_model, disp_by_model=disp_by_model)
 
        item_table = find_table_after_heading(text, "定投计划逐项建议")
        if item_table:
            keys, models, cells = extract_wide_table(item_table, key_header="标的", tail_headers=["一致性", "分歧", "异同"])
            for k in keys:
                per = cells.get(k, {})
                pct_by_model = {}
                dir_raw_by_model = {}
                disp_by_model = {}
                for mname in models:
                    pct, inner, disp = parse_cell(per.get(mname, "—"))
                    pct_by_model[mname] = pct
                    dir_raw_by_model[mname] = inner
                    disp_by_model[mname] = disp
                item_days.setdefault(k, {})[d] = RowDaily(pct_by_model=pct_by_model, dir_raw_by_model=dir_raw_by_model, disp_by_model=disp_by_model)
 
        theme_table = find_table_after_heading(text, "新的定投方向建议")
        if theme_table:
            header = theme_table[0]
            body = theme_table[1:]
            if body and is_separator_row(body[0]):
                body = body[1:]
            key_col = None
            for i, h in enumerate(header):
                if "主题" in h or "方向" in h:
                    key_col = i
                    break
            if key_col is not None:
                tail_start = len(header)
                diff_col = None
                for i, h in enumerate(header):
                    if "异同" in h:
                        tail_start = min(tail_start, i)
                        diff_col = i
                model_indices = [i for i in range(len(header)) if i != key_col and i < tail_start]
                models, canonical_to_indices = dedupe_models(header, model_indices)
                for mname in models:
                    theme_models.add(mname)
                for row in body:
                    if len(row) <= key_col:
                        continue
                    topic = row[key_col].strip()
                    if not topic:
                        continue
                    diff_text = "—"
                    if diff_col is not None and diff_col < len(row):
                        diff_text = normalize_text(row[diff_col]) or "—"
                    topic_norm = normalize_topic_name(topic)
                    for can_model, idxs in canonical_to_indices.items():
                        cands: List[Tuple[str, str]] = []
                        for idx in idxs:
                            if idx < len(row):
                                cands.append((row[idx], header[idx].strip()))
                        chosen = _choose_cell(cands)
                        if normalize_text(chosen) in ("", "—"):
                            continue
                        pct, inner, disp = parse_cell(chosen)
                        if pct is None and inner is None:
                            continue
                        theme_cells.append(
                            ThemeCell(
                                topic=topic,
                                topic_norm=topic_norm,
                                canonical_model=can_model,
                                display=disp,
                                day=d.isoformat(),
                                diff_text=diff_text,
                            )
                        )
 
    cat_order_fixed = ["债券", "中股", "期货", "美股"]
    categories = sorted(category_days.keys())
    categories.sort(key=lambda x: (cat_order_fixed.index(x) if x in cat_order_fixed else 999, x))
 
    items = sorted(item_days.keys())
 
    report_day_first = input_dates[0] if input_dates else week_start
    report_day_last = input_dates[-1] if input_dates else week_end
 
    n_days = len(input_dates)
    k_half = max(1, n_days // 2) if n_days else 0

    cat_rows: List[List[str]] = []
    cat_signal_metrics: Dict[str, Dict[str, object]] = {}
    for cat in categories:
        per_day = category_days.get(cat, {})
        main_dirs: List[Optional[str]] = []
        missing_in_inputs = 0
        for d in input_dates:
            rd = per_day.get(d)
            if not rd:
                main_dirs.append(None)
                missing_in_inputs += 1
                continue
            dir_stats = [direction_to_stat(rd.dir_raw_by_model.get(m), is_category=True) for m in rd.dir_raw_by_model.keys()]
            main_dirs.append(calc_main_direction(dir_stats, label_inc="增配", label_dec="减配"))
        week_score = signal_score_from_main_dirs(main_dirs, label_inc="增配", label_dec="减配")
        early_score = signal_score_from_main_dirs(main_dirs[:k_half], label_inc="增配", label_dec="减配") if k_half else None
        late_score = signal_score_from_main_dirs(main_dirs[-k_half:], label_inc="增配", label_dec="减配") if k_half else None
        action = signal_action(week_score, is_category=True)
        strength = signal_strength(week_score)
        s_trend = signal_trend(early_score, late_score, is_category=True)
        remark_parts = []
        if missing_in_inputs:
            remark_parts.append(f"该行在纳入日报中缺失 {missing_in_inputs} 天")
        if input_dates and per_day.get(report_day_first) is None:
            remark_parts.append("周初数据缺失")
        if input_dates and per_day.get(report_day_last) is None:
            remark_parts.append("周末数据缺失")
        remark = "；".join(remark_parts) if remark_parts else ""
 
        row = [
            cat,
            direction_week_counts(main_dirs, label_inc="增配", label_dec="减配"),
            direction_arrows(main_dirs, label_inc="增配", label_dec="减配"),
            action,
            strength,
            s_trend,
            remark or "—",
        ]
        cat_rows.append(row)
        cat_signal_metrics[cat] = {
            "dirs": direction_week_counts(main_dirs, label_inc="增配", label_dec="减配"),
            "action": action,
            "strength": strength,
            "strength_value": abs(week_score) if week_score is not None else None,
            "trend": s_trend,
            "trend_value": signal_trend_metric(early_score, late_score, is_category=True),
        }
 
    item_rows: List[List[str]] = []
    item_signal_metrics: Dict[str, Dict[str, object]] = {}
    for it in items:
        per_day = item_days.get(it, {})
        main_dirs = []
        missing_in_inputs = 0
        for d in input_dates:
            rd = per_day.get(d)
            if not rd:
                main_dirs.append(None)
                missing_in_inputs += 1
                continue
            dir_stats = [direction_to_stat(rd.dir_raw_by_model.get(m), is_category=False) for m in rd.dir_raw_by_model.keys()]
            main_dirs.append(calc_main_direction(dir_stats, label_inc="增持", label_dec="减持"))
        week_score = signal_score_from_main_dirs(main_dirs, label_inc="增持", label_dec="减持")
        early_score = signal_score_from_main_dirs(main_dirs[:k_half], label_inc="增持", label_dec="减持") if k_half else None
        late_score = signal_score_from_main_dirs(main_dirs[-k_half:], label_inc="增持", label_dec="减持") if k_half else None
        action = signal_action(week_score, is_category=False)
        strength = signal_strength(week_score)
        s_trend = signal_trend(early_score, late_score, is_category=False)
        remark_parts = []
        if missing_in_inputs:
            remark_parts.append(f"该行在纳入日报中缺失 {missing_in_inputs} 天")
        if input_dates and per_day.get(report_day_first) is None:
            remark_parts.append("周初数据缺失")
        if input_dates and per_day.get(report_day_last) is None:
            remark_parts.append("周末数据缺失")
        remark = "；".join(remark_parts) if remark_parts else ""
 
        row = [
            it,
            direction_week_counts(main_dirs, label_inc="增持", label_dec="减持"),
            direction_arrows(main_dirs, label_inc="增持", label_dec="减持"),
            action,
            strength,
            s_trend,
            remark or "—",
        ]
        item_rows.append(row)
        item_signal_metrics[it] = {
            "dirs": direction_week_counts(main_dirs, label_inc="增持", label_dec="减持"),
            "action": action,
            "strength": strength,
            "strength_value": abs(week_score) if week_score is not None else None,
            "trend": s_trend,
            "trend_value": signal_trend_metric(early_score, late_score, is_category=False),
        }
 
    focus_candidates: List[Tuple[str, str, str, str, str, Optional[float], Optional[float]]] = []
    for name, met in cat_signal_metrics.items():
        focus_candidates.append(
            (
                name,
                str(met["dirs"]),
                str(met["action"]),
                str(met["strength"]),
                str(met["trend"]),
                met.get("strength_value") if isinstance(met.get("strength_value"), float) else None,
                met.get("trend_value") if isinstance(met.get("trend_value"), float) else None,
            )
        )
    for name, met in item_signal_metrics.items():
        focus_candidates.append(
            (
                name,
                str(met["dirs"]),
                str(met["action"]),
                str(met["strength"]),
                str(met["trend"]),
                met.get("strength_value") if isinstance(met.get("strength_value"), float) else None,
                met.get("trend_value") if isinstance(met.get("trend_value"), float) else None,
            )
        )

    focus_strong = sorted(focus_candidates, key=lambda x: (x[5] is None, -(x[5] or 0.0), x[0]))[:10]
    focus_change = sorted(focus_candidates, key=lambda x: (x[6] is None, -(x[6] or 0.0), x[0]))[:10]

    def _focus_rows(xs: List[Tuple[str, str, str, str, str, Optional[float], Optional[float]]]) -> List[List[str]]:
        return [[n, ds, act, stg, tr] for n, ds, act, stg, tr, _, _ in xs]
 
    theme_groups: List[List[ThemeCell]] = []
    for cell in theme_cells:
        placed = False
        for g in theme_groups:
            if topics_similar(cell.topic_norm, g[0].topic_norm):
                g.append(cell)
                placed = True
                break
        if not placed:
            theme_groups.append([cell])
 
    group_meta: List[Tuple[str, str, List[ThemeCell]]] = []
    for g in theme_groups:
        freq: Dict[str, int] = {}
        for c in g:
            freq[c.topic] = freq.get(c.topic, 0) + 1
        main_topic = sorted(freq.items(), key=lambda x: (-x[1], len(x[0]), x[0]))[0][0]
        main_norm = normalize_topic_name(main_topic)
        group_meta.append((main_topic, main_norm, g))
 
    def _group_appear_days(g: List[ThemeCell]) -> Set[str]:
        return set(c.day for c in g)
 
    group_meta.sort(key=lambda x: (-len(_group_appear_days(x[2])), x[0]))
 
    theme_model_list = sorted(theme_models)
 
    theme_rows: List[List[str]] = []
    for main_topic, main_norm, g in group_meta:
        by_model: Dict[str, List[ThemeCell]] = {}
        for c in g:
            by_model.setdefault(c.canonical_model, []).append(c)
 
        model_cells: Dict[str, str] = {m: "—" for m in theme_model_list}
        extra_notes: List[str] = []
        for m in theme_model_list:
            cs = by_model.get(m, [])
            if not cs:
                continue
            cs_sorted = sorted(
                cs,
                key=lambda c: (
                    c.day,
                    _similarity_score(c.topic_norm, main_norm),
                    len(c.display),
                    c.topic,
                ),
            )
            chosen = cs_sorted[-1]
            model_cells[m] = f"{chosen.display}@{chosen.day}"
 
            same_day = [c for c in cs if c.day == chosen.day and c.topic != chosen.topic]
            if same_day:
                alt_sorted = sorted(
                    same_day,
                    key=lambda c: (
                        _similarity_score(c.topic_norm, main_norm),
                        len(c.display),
                        c.topic,
                    ),
                )
                for alt in alt_sorted:
                    extra_notes.append(f"该模型另提：{m} {alt.topic} {alt.display}@{alt.day}")
 
        appear_days = sorted(_group_appear_days(g))
        k = len(appear_days)
        n = len(input_dates)
        first_day = appear_days[0] if appear_days else "—"
        last_day = appear_days[-1] if appear_days else "—"
        tags = []
        if input_dates and first_day != report_day_first.isoformat():
            tags.append("本周新增")
        if input_dates and last_day == report_day_last.isoformat():
            tags.append("持续")
        if input_dates and last_day != report_day_last.isoformat():
            tags.append("消失")
 
        merged_sources = sorted(set(c.topic for c in g if c.topic != main_topic))
        diffs = sorted(set(c.diff_text for c in g if c.diff_text and c.diff_text != "—"))
        note_parts = []
        if merged_sources:
            note_parts.append("合并：" + " / ".join([main_topic] + merged_sources))
        if diffs:
            note_parts.append("异同：" + " / ".join(diffs))
        note_parts.extend(extra_notes)
        note_parts.extend(tags)
        note = "；".join(note_parts) if note_parts else "—"
 
        row = [main_topic]
        row.extend([model_cells[m] for m in theme_model_list])
        row.extend([f"{k}/{n}天" if n else f"{k}/0天", first_day, last_day, note])
        theme_rows.append(row)
 
    md_parts: List[str] = []
    md_parts.append(f"# 每周投资总结（{week_start.isoformat()}_to_{week_end.isoformat()}）")
    md_parts.append("")
    md_parts.append("## 0. 数据覆盖")
    md_parts.append(f"- 纳入统计日报：{len(input_dates)} 份：{', '.join([d.isoformat() for d in input_dates]) if input_dates else '—'}")
    md_parts.append(f"- 缺失日期：{', '.join([d.isoformat() for d in missing_dates]) if missing_dates else '—'}")
    md_parts.append("")
 
    md_parts.append("## 1. 大板块比例调整建议（周内趋势）")
    md_parts.append(
        md_table(
            [
                "大板块",
                "周内方向统计（按天）",
                "方向序列(↑↓-)",
                "本周动作建议（信号汇总）",
                "信号强度（全周）",
                "信号变化",
                "备注",
            ],
            cat_rows,
        )
    )
    md_parts.append("")
 
    md_parts.append("## 2. 定投计划逐项建议（周内趋势）")
    md_parts.append(
        md_table(
            [
                "标的",
                "周内方向统计（按天）",
                "方向序列(↑↓-)",
                "本周动作建议（信号汇总）",
                "信号强度（全周）",
                "信号变化",
                "备注",
            ],
            item_rows,
        )
    )
    md_parts.append("")
 
    md_parts.append("### 信号聚焦")
    md_parts.append("")
    md_parts.append("#### 信号最强 TOP10")
    md_parts.append("")
    md_parts.append(
        md_table(
            ["标的/大板块", "周内方向统计（按天）", "本周动作建议（信号汇总）", "信号强度（全周）", "信号变化"],
            _focus_rows(focus_strong),
        )
    )
    md_parts.append("")
    md_parts.append("#### 信号变化最大 TOP10")
    md_parts.append("")
    md_parts.append(
        md_table(
            ["标的/大板块", "周内方向统计（按天）", "本周动作建议（信号汇总）", "信号强度（全周）", "信号变化"],
            _focus_rows(focus_change),
        )
    )
    md_parts.append("")
 
    md_parts.append("## 3. 新的定投方向建议（周内趋势）")
    theme_headers = ["主题/方向"] + theme_model_list + ["出现", "首次出现", "最近出现", "异同/趋势"]
    md_parts.append(md_table(theme_headers, theme_rows))
    md_parts.append("")
 
    out_text = "\n".join(md_parts).rstrip() + "\n"
    out_path = OUTPUT_DIR / f"{week_start.isoformat()}_to_{week_end.isoformat()}_每周投资总结.md"
    return out_text, input_paths, missing_dates, str(out_path)
 
 
def latest_n_days_range(n: int = 7) -> Tuple[date, date]:
    latest: Optional[date] = None
    for p in INPUT_DIR.iterdir():
        m = FILE_RE.match(p.name)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if latest is None or d > latest:
            latest = d
    end = latest or date.today()
    start = end - timedelta(days=max(1, n) - 1)
    return start, end
 
 
REPORT_RE_TO = re.compile(r"^(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})_每周投资总结\.md$")
REPORT_RE_TILDE = re.compile(r"^(\d{4}-\d{2}-\d{2})~(\d{4}-\d{2}-\d{2})_每周投资总结\.md$")


def _parse_report_range(name: str) -> Optional[Tuple[date, date]]:
    m = REPORT_RE_TO.match(name) or REPORT_RE_TILDE.match(name)
    if not m:
        return None
    start_s, end_s = m.group(1), m.group(2)
    try:
        return (
            datetime.strptime(start_s, "%Y-%m-%d").date(),
            datetime.strptime(end_s, "%Y-%m-%d").date(),
        )
    except ValueError:
        return None


def rewrite_existing_reports(report_dir: Path) -> Tuple[int, int]:
    updated = 0
    skipped = 0
    for p in sorted(report_dir.iterdir()):
        if not p.is_file() or p.suffix.lower() != ".md":
            continue
        rng = _parse_report_range(p.name)
        if rng is None:
            skipped += 1
            continue
        week_start, week_end = rng
        out_text, _, _, _ = compute_weekly(week_start, week_end)
        p.write_text(out_text, encoding="utf-8")
        updated += 1
    return updated, skipped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--week-start", type=str, default="")
    parser.add_argument("--week-end", type=str, default="")
    parser.add_argument("--rewrite-existing-reports", action="store_true")
    parser.add_argument("--report-dir", type=str, default=str(OUTPUT_DIR))
    args = parser.parse_args()
 
    if args.rewrite_existing_reports:
        report_dir = Path(args.report_dir)
        updated, skipped = rewrite_existing_reports(report_dir)
        print(f"updated={updated}")
        print(f"skipped={skipped}")
        return 0

    if args.week_start and args.week_end:
        week_start = datetime.strptime(args.week_start, "%Y-%m-%d").date()
        week_end = datetime.strptime(args.week_end, "%Y-%m-%d").date()
    else:
        week_start, week_end = latest_n_days_range(7)
 
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_text, input_paths, _, out_path_str = compute_weekly(week_start, week_end)
    out_path = Path(out_path_str)
    out_path.write_text(out_text, encoding="utf-8")
 
    print(out_path.as_posix())
    print(f"inputs={len(input_paths)}")
    return 0
 
 
if __name__ == "__main__":
    raise SystemExit(main())
