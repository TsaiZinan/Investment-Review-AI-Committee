import argparse
import json
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

# Configuration
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATE = date.today().isoformat()
OUTPUT_DIR = ROOT / '每日最终报告'

MODEL_PREFIX_ORDER = [
    'deepseek',
    'gemini',
    'gpt',
    'grok',
    'glm',
    'kimi',
    'minimax',
    'traeai',
    'qwen',
]

CATEGORY_ORDER_FIXED = ['债券', '中股', '期货', '美股']

# --- Helper Functions ---

def canonicalize_model(raw_model: str) -> str:
    return (raw_model or '').strip()

def model_sort_key(model: str) -> Tuple[int, int, str]:
    s = (model or '').strip()
    low = s.lower()
    for i, prefix in enumerate(MODEL_PREFIX_ORDER):
        if low.startswith(prefix):
            return (0, i, s)
    return (1, len(MODEL_PREFIX_ORDER), s)

def format_pct(x: float) -> str:
    return f'{x:.2f}%'

def parse_float_from_text(s: str) -> Optional[float]:
    if not s: return None
    m = re.search(r'-?\d+(?:\.\d+)?', s.replace(',', ''))
    if not m: return None
    try:
        return float(m.group(0))
    except ValueError:
        return None

def parse_markdown_table(table_lines: List[str]) -> List[List[str]]:
    rows = []
    for line in table_lines:
        if not line.strip().startswith('|'): continue
        parts = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(parts) <= 1: continue
        rows.append(parts)
    return rows

def find_table_after_heading(text: str, heading_substring: str) -> Tuple[Optional[List[List[str]]], str]:
    lines = text.splitlines()
    start_idx = None
    for i, ln in enumerate(lines):
        if heading_substring in ln:
            start_idx = i
            break
    if start_idx is None:
        return None, ''

    post_lines = lines[start_idx + 1 :]
    first_table_line = None
    for j, ln in enumerate(post_lines):
        if ln.strip().startswith('|') and '|' in ln.strip()[1:]:
            first_table_line = start_idx + 1 + j
            break
        if ln.strip().startswith('#') and j > 0:
            break

    if first_table_line is None:
        return None, '\n'.join(post_lines)

    table_lines = []
    k = first_table_line
    while k < len(lines):
        ln = lines[k]
        if ln.strip().startswith('|'):
            table_lines.append(ln)
            k += 1
            continue
        break
    
    remaining = '\n'.join(lines[k:])
    parsed = parse_markdown_table(table_lines)
    return (parsed if parsed else None), remaining

def is_separator_row(row: List[str]) -> bool:
    return all(re.fullmatch(r':?-{3,}:?', c.replace(' ', '')) is not None for c in row)

def find_col(header: List[str], includes: List[str], excludes: List[str] = []) -> Optional[int]:
    for i, h in enumerate(header):
        hh = h.strip()
        if any(ex in hh for ex in excludes): continue
        if all(inc in hh for inc in includes): return i
    return None

# --- Data Structures ---

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

@dataclass
class ItemEntry:
    name: str
    name_norm: str
    candidate: CellCandidate
    canonical_model: str

@dataclass
class ModelParsed:
    raw_model: str
    canonical_model: str
    categories: Dict[str, CellCandidate]
    items: Dict[str, CellCandidate]
    top_changes: List['TopChangeEntry']
    themes: List[ThemeEntry]
    explicitly_no_new: bool
    cat_order: List[str]
    item_order: List[str]

@dataclass
class TopChangeEntry:
    item: str
    item_norm: str
    direction_raw: Optional[str]
    direction_stat: Optional[str]
    from_pct: Optional[float]
    to_pct: Optional[float]
    reason: str
    raw_model: str
    canonical_model: str

# --- Logic ---

def direction_to_stat(direction: Optional[str], *, is_category: bool) -> Optional[str]:
    if not direction: return None
    d = direction.strip()
    if any(x in d for x in ['维持', '不变', '保持']): return '不变'
    
    if is_category:
        if '小幅增配' in d: return '增'
        if '小幅减配' in d: return '减'
        if '增配' in d: return '增'
        if '减配' in d: return '减'
    else:
        if '增持' in d: return '增'
        if '减持' in d: return '减'

    if '增' in d: return '增'
    if '减' in d or '暂停' in d or '停止' in d: return '减'
    return '不变'

def parse_categories(text: str, raw_model: str) -> Tuple[List[str], Dict[str, CellCandidate]]:
    table, _ = find_table_after_heading(text, '大板块比例调整建议')
    if not table or len(table) < 2:
        lines = text.splitlines()
        tables: List[List[List[str]]] = []
        i = 0
        while i < len(lines):
            if not lines[i].strip().startswith('|'):
                i += 1
                continue
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            parsed = parse_markdown_table(table_lines)
            if parsed:
                tables.append(parsed)

        order: List[str] = []
        out: Dict[str, CellCandidate] = {}
        amounts_after: Dict[str, float] = {}
        directions: Dict[str, str] = {}

        def try_parse_kimi_summary(t: List[List[str]]) -> None:
            nonlocal order, out, amounts_after, directions
            if not t or len(t) < 2:
                return
            header = t[0]
            body = t[1:]
            if body and is_separator_row(body[0]):
                body = body[1:]

            key_col = find_col(header, ['大类'])
            if key_col is None:
                key_col = find_col(header, ['大板块'])
            before_col = find_col(header, ['调整前', '周定投'])
            after_col = find_col(header, ['调整后', '周定投'])
            if after_col is None:
                after_col = find_col(header, ['调整后'])

            if key_col is None or before_col is None or after_col is None:
                return

            for row in body:
                if len(row) <= max(key_col, before_col, after_col):
                    continue
                key = row[key_col].strip()
                key_plain = re.sub(r'[*_`\\s]+', '', key)
                if not key_plain or key_plain in ('合计', '总计'):
                    continue
                key = key_plain
                before_amt = parse_float_from_text(row[before_col])
                after_amt = parse_float_from_text(row[after_col])
                if after_amt is None:
                    continue

                if before_amt is None:
                    direction = None
                else:
                    delta = after_amt - before_amt
                    if abs(delta) < 1e-9:
                        direction = '不变'
                    elif delta > 0:
                        direction = '增配'
                    else:
                        direction = '减配'

                if key not in out:
                    order.append(key)
                amounts_after[key] = after_amt
                if direction:
                    directions[key] = direction
                out[key] = CellCandidate(
                    display='—',
                    pct=None,
                    direction_raw=direction,
                    direction_stat=direction_to_stat(direction, is_category=True) if direction else None,
                    raw_model=raw_model
                )

        for t in tables:
            try_parse_kimi_summary(t)

        if amounts_after:
            total = sum(amounts_after.values())
            if total > 0:
                for key, amt in amounts_after.items():
                    cand = out.get(key)
                    if not cand:
                        continue
                    pct = (amt / total) * 100.0
                    cand.pct = pct
                    dir_disp = cand.direction_raw if cand.direction_raw else '—'
                    cand.display = f'{format_pct(pct)}（{dir_disp}）'
            return order, out
        return [], {}

    header = table[0]
    body = table[1:]
    if body and is_separator_row(body[0]): body = body[1:]

    key_col = find_col(header, ['大板块'])
    pct_col = find_col(header, ['建议%'])
    dir_col = find_col(header, ['建议'], excludes=['建议%'])

    if key_col is None or pct_col is None or dir_col is None:
        key_col2 = find_col(header, ['大类'])
        if key_col2 is None:
            key_col2 = key_col

        before_col2 = find_col(header, ['当前目标'])
        if before_col2 is None:
            before_col2 = find_col(header, ['当前'])

        after_col2 = find_col(header, ['调整后'])
        adjust_col2 = find_col(header, ['建议调整'])

        if key_col2 is None or after_col2 is None:
            return [], {}

        order2: List[str] = []
        out2: Dict[str, CellCandidate] = {}
        for row in body:
            if len(row) <= max(key_col2, after_col2):
                continue
            key = row[key_col2].strip()
            key_plain = re.sub(r'[*_`\\s]+', '', key)
            if not key_plain or key_plain in ('合计', '总计'):
                continue
            key = key_plain

            before_pct = parse_float_from_text(row[before_col2]) if (before_col2 is not None and len(row) > before_col2) else None
            after_pct = parse_float_from_text(row[after_col2])
            if after_pct is None:
                continue

            direction = None
            if adjust_col2 is not None and len(row) > adjust_col2:
                adjust_text = (row[adjust_col2] or '').strip()
                if '↑' in adjust_text:
                    direction = '增配'
                elif '↓' in adjust_text:
                    direction = '减配'
                elif '→' in adjust_text:
                    direction = '不变'

            if direction is None and before_pct is not None:
                delta = after_pct - before_pct
                if abs(delta) < 1e-9:
                    direction = '不变'
                elif delta > 0:
                    direction = '增配'
                else:
                    direction = '减配'

            pct_disp = format_pct(after_pct)
            dir_disp = direction if direction else '—'
            display = f'{pct_disp}（{dir_disp}）'

            order2.append(key)
            out2[key] = CellCandidate(
                display=display,
                pct=after_pct,
                direction_raw=direction,
                direction_stat=direction_to_stat(direction, is_category=True) if direction else None,
                raw_model=raw_model
            )
        return order2, out2

    order = []
    out = {}
    for row in body:
        if len(row) <= max(key_col, pct_col, dir_col): continue
        key = row[key_col].strip()
        if not key: continue
        
        pct = parse_float_from_text(row[pct_col])
        direction = row[dir_col].strip() or None
        
        pct_disp = format_pct(pct) if pct is not None else '—'
        dir_disp = direction if direction else '—'
        
        if pct is None and not direction:
            display = '—'
        elif pct is not None:
            display = f'{pct_disp}（{dir_disp}）'
        else:
            display = f'—（{dir_disp}）'

        order.append(key)
        out[key] = CellCandidate(
            display=display,
            pct=pct,
            direction_raw=direction,
            direction_stat=direction_to_stat(direction, is_category=True),
            raw_model=raw_model
        )
    return order, out

def parse_items(text: str, raw_model: str) -> Tuple[List[str], Dict[str, CellCandidate]]:
    def scan_tables_all() -> Tuple[List[str], Dict[str, CellCandidate]]:
        lines = text.splitlines()
        tables: List[List[List[str]]] = []
        i = 0
        while i < len(lines):
            if not lines[i].strip().startswith('|'):
                i += 1
                continue
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            parsed = parse_markdown_table(table_lines)
            if parsed:
                tables.append(parsed)

        merged_order: List[str] = []
        merged_items: Dict[str, CellCandidate] = {}
        merged_amounts: Dict[str, float] = {}

        def upsert_item(key: str, cand: CellCandidate, *, amount_value: Optional[float]) -> None:
            nonlocal merged_order, merged_items, merged_amounts
            if not key:
                return
            if not normalize_item_name(key):
                return
            existing = merged_items.get(key)
            if existing:
                if existing.pct is None and cand.pct is not None:
                    merged_items[key] = cand
                    if amount_value is not None:
                        merged_amounts[key] = amount_value
                return
            merged_order.append(key)
            merged_items[key] = cand
            if amount_value is not None:
                merged_amounts[key] = amount_value

        def has_word(h: str, w: str) -> bool:
            return w in (h or '').strip()

        def try_parse_table(t: List[List[str]]) -> None:
            if not t or len(t) < 2:
                return
            header = t[0]
            body = t[1:]
            if body and is_separator_row(body[0]):
                body = body[1:]
            if not body:
                return

            key_col = find_col(header, ['标的'])
            if key_col is None:
                key_col = find_col(header, ['基金'])
            if key_col is None:
                return

            current_pct_col = find_col(header, ['当前占比'])
            if current_pct_col is None:
                current_pct_col = find_col(header, ['当前', '占比'])
            if current_pct_col is None:
                current_pct_col = find_col(header, ['当前比例'])
            adjust_col = find_col(header, ['建议调整'])
            if adjust_col is None:
                adjust_col = find_col(header, ['建议', '调整'])

            if current_pct_col is not None and adjust_col is not None:
                for row in body:
                    if len(row) <= max(key_col, current_pct_col, adjust_col):
                        continue
                    key = row[key_col].strip()
                    cur = parse_float_from_text(row[current_pct_col])
                    delta = parse_float_from_text(row[adjust_col])
                    if cur is None or delta is None:
                        continue

                    to_pct = cur + delta
                    if abs(delta) < 1e-9:
                        direction = '维持'
                    elif delta > 0:
                        direction = '增持'
                    else:
                        direction = '减持'
                    dir_disp = direction if direction else '—'
                    display = f'{format_pct(to_pct)}（{dir_disp}）'
                    upsert_item(
                        key,
                        CellCandidate(
                            display=display,
                            pct=to_pct,
                            direction_raw=direction,
                            direction_stat=direction_to_stat(direction, is_category=False) if direction else None,
                            raw_model=raw_model,
                        ),
                        amount_value=None,
                    )
                return

            current_col = find_col(header, ['当前周定投'])
            if current_col is None:
                current_col = find_col(header, ['当前', '定投'])
            if current_col is None:
                current_col = find_col(header, ['当前金额'])

            after_col = find_col(header, ['调整后', '周定投'])
            if after_col is None:
                after_col = find_col(header, ['调整后'])

            value_col = find_col(header, ['建议金额'])
            if value_col is None:
                value_col = find_col(header, ['建议周定投'])
            if value_col is None:
                value_col = find_col(header, ['建议定投额'])
            if value_col is None:
                value_col = find_col(header, ['建议', '定投'])
            if value_col is None:
                value_col = find_col(header, ['定投金额'])
            if value_col is None:
                value_col = find_col(header, ['定投额'])
            if value_col is None:
                value_col = find_col(header, ['建议调整'])
            if value_col is None:
                value_col = find_col(header, ['建议', '调整'])

            if value_col is not None and after_col is not None:
                value_header_probe = (header[value_col] or '').strip()
                if '建议调整' in value_header_probe:
                    value_col = after_col

            explicit_direction_col = None
            for i, h in enumerate(header):
                hh = (h or '').strip()
                if not hh or '建议' not in hh:
                    continue
                if any(x in hh for x in ['增持', '减持', '不变', '维持', '暂停', '停止', '增配', '减配']):
                    if any(x in hh for x in ['建议%', '金额', '周定投', '定投', '调整']):
                        continue
                    explicit_direction_col = i
                    break

            direction_only_col = None
            if value_col is None:
                direction_only_col = find_col(header, ['建议'], excludes=['建议%', '建议金额', '建议调整'])
                if direction_only_col is None and find_col(header, ['当前状态']) is not None:
                    direction_only_col = find_col(header, ['建议'])

            if value_col is None and direction_only_col is None:
                return

            value_header = (header[value_col] or '').strip() if value_col is not None else ''
            is_percent = ('%' in value_header) or ('比例' in value_header)

            for row in body:
                if len(row) <= key_col:
                    continue
                key = row[key_col].strip()

                if direction_only_col is not None:
                    if len(row) <= direction_only_col:
                        continue
                    direction_raw = row[direction_only_col].strip() or None
                    if not direction_raw:
                        continue
                    display = f'—（{direction_raw}）'
                    upsert_item(
                        key,
                        CellCandidate(
                            display=display,
                            pct=None,
                            direction_raw=direction_raw,
                            direction_stat=direction_to_stat(direction_raw, is_category=False),
                            raw_model=raw_model,
                        ),
                        amount_value=None,
                    )
                    continue

                if len(row) <= value_col:
                    continue
                value = parse_float_from_text(row[value_col])
                if value is None:
                    if explicit_direction_col is not None and len(row) > explicit_direction_col:
                        direction_raw = row[explicit_direction_col].strip() or None
                        if direction_raw:
                            display = f'—（{direction_raw}）'
                            upsert_item(
                                key,
                                CellCandidate(
                                    display=display,
                                    pct=None,
                                    direction_raw=direction_raw,
                                    direction_stat=direction_to_stat(direction_raw, is_category=False),
                                    raw_model=raw_model,
                                ),
                                amount_value=None,
                            )
                    continue

                direction_from_col = None
                if explicit_direction_col is not None and len(row) > explicit_direction_col:
                    direction_from_col = row[explicit_direction_col].strip() or None

                direction = direction_from_col
                current_value = None
                if current_col is not None and len(row) > current_col:
                    current_header = (header[current_col] or '').strip()
                    if has_word(current_header, '定投') or has_word(current_header, '周'):
                        current_value = parse_float_from_text(row[current_col])
                if direction is None and current_value is not None:
                    if abs(value - current_value) < 1e-9:
                        direction = '维持'
                    elif value > current_value:
                        direction = '增持'
                    else:
                        direction = '减持'

                if is_percent:
                    value_disp = format_pct(value)
                    amount_value = None
                    pct_value = value
                else:
                    value_disp = f'{value:g}'
                    amount_value = value
                    pct_value = None
                dir_disp = direction if direction else '—'
                display = f'{value_disp}（{dir_disp}）'

                upsert_item(
                    key,
                    CellCandidate(
                        display=display,
                        pct=pct_value,
                        direction_raw=direction,
                        direction_stat=direction_to_stat(direction, is_category=False) if direction else None,
                        raw_model=raw_model,
                    ),
                    amount_value=amount_value,
                )

        for t in tables:
            try_parse_table(t)

        if merged_amounts:
            total = sum(merged_amounts.values())
            if total > 0:
                for k, amt in merged_amounts.items():
                    cand = merged_items.get(k)
                    if not cand:
                        continue
                    pct = (amt / total) * 100.0
                    cand.pct = pct
                    dir_disp = cand.direction_raw if cand.direction_raw else '—'
                    cand.display = f'{format_pct(pct)}（{dir_disp}）'

        if merged_items:
            return merged_order, merged_items
        return [], {}

    table, _ = find_table_after_heading(text, '定投计划逐项建议')
    if not table or len(table) < 2:
        return scan_tables_all()

    header = table[0]
    body = table[1:]
    if body and is_separator_row(body[0]): body = body[1:]

    key_col = find_col(header, ['标的'])
    pct_col = find_col(header, ['建议%'])
    amt_col = find_col(header, ['建议金额'])
    dir_col = find_col(header, ['建议'], excludes=['建议%', '建议金额'])

    if key_col is None or dir_col is None:
        return scan_tables_all()

    value_col = pct_col if pct_col is not None else amt_col
    if value_col is None:
        return scan_tables_all()
    is_percent = (pct_col is not None)

    order = []
    out = {}
    amounts = {}
    for row in body:
        if len(row) <= max(key_col, value_col, dir_col): continue
        key = row[key_col].strip()
        if not normalize_item_name(key):
            continue
        if not key: continue
        
        value = parse_float_from_text(row[value_col])
        direction = row[dir_col].strip() or None
        
        if is_percent:
            value_disp = format_pct(value) if value is not None else '—'
        else:
            value_disp = f'{value:g}' if value is not None else '—'
        dir_disp = direction if direction else '—'
        
        if value is None and not direction:
            display = '—'
        elif value is not None:
            display = f'{value_disp}（{dir_disp}）'
        else:
            display = f'—（{dir_disp}）'

        order.append(key)
        out[key] = CellCandidate(
            display=display,
            pct=value if is_percent else None,
            direction_raw=direction,
            direction_stat=direction_to_stat(direction, is_category=False),
            raw_model=raw_model
        )
        if (not is_percent) and (value is not None):
            amounts[key] = value

    if (not is_percent) and amounts:
        total = sum(amounts.values())
        if total > 0:
            for k, amt in amounts.items():
                cand = out.get(k)
                if not cand:
                    continue
                pct = (amt / total) * 100.0
                cand.pct = pct
                dir_disp = cand.direction_raw if cand.direction_raw else '—'
                cand.display = f'{format_pct(pct)}（{dir_disp}）'
    return order, out

def normalize_topic_name(s: str) -> str:
    if not s: return ''
    t = unicodedata.normalize('NFKC', s)
    t = t.strip().lower()
    t = t.replace('（', '(').replace('）', ')')
    t = re.sub(r'\s+', '', t)
    for w in ['etf', '指数', '基金', '定投', '主题', '方向', '板块', '赛道', '相关', '概念']:
        t = t.replace(w, '')
    t = re.sub(r'[\[\]{}<>《》“”"\'`]', '', t)
    t = t.replace('(', '').replace(')', '')
    return t

def topic_tokens(norm: str) -> List[str]:
    if not norm: return []
    tokens = re.findall(r'[\u4e00-\u9fff]{2,}|[a-z0-9]{2,}', norm)
    if len(tokens) >= 2: return tokens
    if len(norm) >= 2: return [norm[i:i+2] for i in range(len(norm)-1)]
    return [norm]

def normalize_item_name(s: str) -> str:
    if not s:
        return ''
    t = unicodedata.normalize('NFKC', s)
    t = t.strip().lower()
    if re.fullmatch(r'[\-—–—]+', t):
        return ''
    t = t.replace('（', '(').replace('）', ')')
    t = re.sub(r'\s+', '', t)
    if re.fullmatch(r'[\-—–—]+', t):
        return ''
    t = re.sub(r'(?<!\d)\d{6}(?!\d)', '', t)
    t = t.replace('创新药产业', '创新药')
    t = t.replace('人民币', '')
    t = t.replace('中证申万', '')
    t = t.replace('中证全指', '')
    t = t.replace('中证', '')
    t = t.replace('申万', '')
    t = t.replace('全指', '')
    t = t.replace('发起式', '').replace('发起', '')
    t = re.sub(r'[\[\]{}<>《》“”"\'`]', '', t)
    t = t.replace('(', '').replace(')', '')
    t = re.sub(r'^华安黄金(?:易)?etf联接[abc]?$', '华安黄金', t)
    t = re.sub(r'^华安黄金(?:易)?etf$', '华安黄金', t)
    return t

def item_tokens(norm: str) -> List[str]:
    if not norm:
        return []
    if len(norm) >= 2:
        return [norm[i:i+2] for i in range(len(norm) - 1)]
    return [norm]

def item_norm_similar(a: str, b: str) -> bool:
    if not a or not b:
        return False
    ma = re.match(r'[\u4e00-\u9fff]{2,4}', a)
    mb = re.match(r'[\u4e00-\u9fff]{2,4}', b)
    if ma and mb and ma.group(0) != mb.group(0):
        return False
    if a == b:
        return True
    if a in b or b in a:
        if min(len(a), len(b)) >= 6:
            return True
    ta = set(item_tokens(a))
    tb = set(item_tokens(b))
    inter = len(ta & tb)
    if inter < 10:
        return False
    union = len(ta | tb)
    if union == 0:
        return False
    return (inter / union) >= 0.60

def item_norm_variants(norm: str) -> Set[str]:
    if not norm:
        return set()
    out = {norm}
    out.add(re.sub(r'[abc]$', '', norm))
    out.add(re.sub(r'(?:联接)?[abc]$', '', norm))
    out = {x for x in out if x}
    return out

def jaccard_bigrams(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    ta = set(item_tokens(a))
    tb = set(item_tokens(b))
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    if union == 0:
        return 0.0
    return inter / union

def load_strategy_investment_plan_items(date_str: str) -> Tuple[Optional[Path], List[Dict]]:
    input_dir = ROOT / '报告' / date_str
    strategy_path = input_dir / '投资策略.json'
    if not strategy_path.exists():
        return None, []
    try:
        data = json.loads(strategy_path.read_text(encoding='utf-8'))
    except Exception:
        return strategy_path, []
    plan = data.get('investment_plan', [])
    if not isinstance(plan, list):
        return strategy_path, []
    cleaned = []
    for row in plan:
        if not isinstance(row, dict):
            continue
        name = (row.get('fund_name') or '').strip()
        code = (row.get('fund_code') or '').strip()
        if not name and not code:
            continue
        cleaned.append({'fund_name': name, 'fund_code': code})
    return strategy_path, cleaned

def map_report_item_to_source_name(
    item: str,
    *,
    source_names: List[str],
    source_names_set: Set[str],
    source_norm_to_names: Dict[str, List[str]],
) -> Optional[str]:
    if not item:
        return None
    if item in source_names_set:
        return item
    norm = normalize_item_name(item)
    if not norm:
        return None

    candidates: List[str] = []
    for v in item_norm_variants(norm):
        candidates.extend(source_norm_to_names.get(v, []))
    if candidates:
        return sorted(set(candidates), key=lambda x: (len(x), x))[0]

    best_match = None
    best_score = 0.0
    for src in source_names:
        src_norm = normalize_item_name(src)
        score = jaccard_bigrams(norm, src_norm)
        if score > best_score:
            best_score = score
            best_match = src
    if best_match and best_score >= 0.55:
        return best_match
    return None

@dataclass
class ItemValidationIssue:
    file_name: str
    raw_model: str
    extra_items: List[str]
    missing_items: List[str]
    mapped_name_mismatches: List[Tuple[str, str]]

def validate_report_items_against_strategy(date_str: str, files: List[Tuple[Path, str]]) -> Tuple[bool, List[ItemValidationIssue], str]:
    strategy_path, plan_items = load_strategy_investment_plan_items(date_str)
    if not strategy_path:
        return False, [], f'缺少数据源：报告/{date_str}/投资策略.json'
    if not plan_items:
        return False, [], f'数据源无法解析或 investment_plan 为空：报告/{date_str}/投资策略.json'

    source_names = [x['fund_name'] for x in plan_items if x.get('fund_name')]
    source_names_set = set(source_names)
    source_norm_to_names: Dict[str, List[str]] = {}
    for nm in source_names:
        n = normalize_item_name(nm)
        for v in item_norm_variants(n):
            source_norm_to_names.setdefault(v, []).append(nm)

    issues: List[ItemValidationIssue] = []
    any_fatal_issue = False

    for path, raw_model in files:
        text = path.read_text(encoding='utf-8')
        _, items = parse_items(text, raw_model)
        report_items = list(items.keys())
        report_items_set = set(report_items)

        mapped_name_mismatches: List[Tuple[str, str]] = []
        matched_source: Set[str] = set()
        extra_items: List[str] = []

        for item in report_items:
            if not normalize_item_name(item):
                continue
            if item in source_names_set:
                matched_source.add(item)
                continue

            norm = normalize_item_name(item)
            candidates = []
            for v in item_norm_variants(norm):
                candidates.extend(source_norm_to_names.get(v, []))

            if candidates:
                best = sorted(set(candidates), key=lambda x: (len(x), x))[0]
                mapped_name_mismatches.append((item, best))
                matched_source.add(best)
                continue

            best_match = None
            best_score = 0.0
            for src in source_names:
                src_norm = normalize_item_name(src)
                score = jaccard_bigrams(norm, src_norm)
                if score > best_score:
                    best_score = score
                    best_match = src

            if best_match and best_score >= 0.55:
                mapped_name_mismatches.append((item, best_match))
                matched_source.add(best_match)
                continue

            extra_items.append(item)

        missing_items = [nm for nm in source_names if nm not in matched_source and nm not in report_items_set]

        if missing_items:
            any_fatal_issue = True
        if extra_items or missing_items or mapped_name_mismatches:
            issues.append(ItemValidationIssue(
                file_name=path.name,
                raw_model=raw_model,
                extra_items=sorted(extra_items),
                missing_items=missing_items,
                mapped_name_mismatches=sorted(mapped_name_mismatches, key=lambda x: (x[1], x[0])),
            ))

    return (not any_fatal_issue), issues, f'数据源：报告/{date_str}/投资策略.json（investment_plan={len(source_names)}）'

def parse_themes(text: str, raw_model: str) -> Tuple[List[ThemeEntry], bool]:
    lines = text.splitlines()
    start_idx = None
    for i, ln in enumerate(lines):
        if '新的定投方向建议' in ln:
            start_idx = i
            break
    intro = ''
    if start_idx is not None:
        post_lines = lines[start_idx + 1 :]
        intro_lines = []
        for ln in post_lines:
            if ln.strip().startswith('|') and '|' in ln.strip()[1:]:
                break
            if ln.strip().startswith('#'):
                break
            intro_lines.append(ln)
        intro = '\n'.join(intro_lines)

    table, remaining = find_table_after_heading(text, '新的定投方向建议')
    explicitly_no_new = bool(re.search(r'本周期不新增|不新增|无新增|无需新增', (intro + '\n' + remaining)))

    if not table:
        return [], explicitly_no_new

    header = table[0]
    body = table[1:]
    if body and is_separator_row(body[0]): body = body[1:]

    topic_col = None
    for key in ['主题/方向', '行业/主题', '行业', '主题', '方向']:
        topic_col = find_col(header, [key])
        if topic_col is not None: break
    
    pct_col = find_col(header, ['比例'])
    caliber_col = find_col(header, ['口径'])

    if topic_col is None or pct_col is None or caliber_col is None:
        return [], explicitly_no_new

    entries = []
    for row in body:
        if len(row) <= max(topic_col, pct_col, caliber_col): continue
        topic = row[topic_col].strip()
        if not topic:
            continue

        topic_norm = normalize_topic_name(topic)
        if topic in ['无', '—', '-'] or topic_norm in ['', '无'] or re.fullmatch(r'[\(\（]无[\)\）]', topic.strip()):
            explicitly_no_new = True
            continue
        
        pct = parse_float_from_text(row[pct_col])
        caliber = row[caliber_col].strip() or '—'
        
        display = '—'
        if pct is not None:
            display = f'{format_pct(pct)}（{caliber}）'
            
        entries.append(ThemeEntry(
            topic=topic,
            topic_norm=topic_norm,
            pct=pct,
            caliber=caliber,
            display=display,
            raw_model=raw_model
        ))

    if not entries and bool(re.search(r'本周期不新增|不新增|无新增|无需新增', (intro + '\n' + remaining))):
        explicitly_no_new = True

    return entries, explicitly_no_new

def parse_top_changes(text: str, raw_model: str, canonical_model: str) -> List[TopChangeEntry]:
    lines = text.splitlines()
    start_idx = None
    for i, ln in enumerate(lines):
        if '定投增减要点' in ln:
            start_idx = i
            break
    if start_idx is None:
        return []

    bullet_lines = []
    for ln in lines[start_idx + 1:]:
        s = ln.strip()
        if s.startswith('#'):
            break
        if s.startswith(('*', '-')):
            bullet_lines.append(s)

    out: List[TopChangeEntry] = []
    for bl in bullet_lines:
        s = bl.lstrip('*-').strip()
        if '：' not in s:
            continue
        item, rest = s.split('：', 1)
        item = item.strip()
        rest = rest.strip()
        if not item or not rest:
            continue

        reason = ''
        if '—' in rest:
            rest_main, reason = rest.split('—', 1)
        elif ' - ' in rest:
            rest_main, reason = rest.split(' - ', 1)
        else:
            rest_main = rest
        reason = reason.strip()

        direction_raw = None
        for key in ['增持', '减持', '不变', '维持', '暂停', '停止']:
            if key in rest_main:
                direction_raw = key
                break

        nums = re.findall(r'-?\d+(?:\.\d+)?', rest_main.replace(',', ''))
        from_pct = None
        to_pct = None
        if len(nums) >= 2:
            try:
                from_pct = float(nums[0])
                to_pct = float(nums[1])
            except ValueError:
                from_pct = None
                to_pct = None

        out.append(TopChangeEntry(
            item=item,
            item_norm=normalize_item_name(item),
            direction_raw=direction_raw,
            direction_stat=direction_to_stat(direction_raw, is_category=False) if direction_raw else None,
            from_pct=from_pct,
            to_pct=to_pct,
            reason=reason,
            raw_model=raw_model,
            canonical_model=canonical_model,
        ))
    return out

def summarize_top_changes_paragraph(models: List[ModelParsed], *, max_chars: int = 1000) -> str:
    all_entries: List[TopChangeEntry] = []
    for m in models:
        all_entries.extend(m.top_changes)

    model_count = len({m.canonical_model for m in models})
    if not all_entries or model_count == 0:
        return '当日各报告未提供可解析的“定投增减要点”，因此无法基于该部分做横向综述。'

    @dataclass
    class ChangeGroup:
        names: List[str]
        norms: List[str]
        entries: List[TopChangeEntry]

    groups: List[ChangeGroup] = []
    for e in all_entries:
        placed = False
        for g in groups:
            if any(item_norm_similar(e.item_norm, gn) for gn in g.norms):
                g.names.append(e.item)
                g.norms.append(e.item_norm)
                g.entries.append(e)
                placed = True
                break
        if not placed:
            groups.append(ChangeGroup(names=[e.item], norms=[e.item_norm], entries=[e]))

    def main_name(g: ChangeGroup) -> str:
        freq: Dict[str, int] = {}
        for n in g.names:
            freq[n] = freq.get(n, 0) + 1
        return sorted(freq.items(), key=lambda x: (-x[1], len(x[0]), x[0]))[0][0]

    def uniq_models(g: ChangeGroup) -> Set[str]:
        return {e.canonical_model for e in g.entries}

    def dir_counts(g: ChangeGroup) -> Dict[str, int]:
        c = {'增': 0, '减': 0, '不变': 0, '未知': 0}
        for e in g.entries:
            if e.direction_stat in ('增', '减', '不变'):
                c[e.direction_stat] += 1
            else:
                c['未知'] += 1
        return c

    def avg_delta(g: ChangeGroup) -> Optional[float]:
        deltas = []
        for e in g.entries:
            if e.from_pct is not None and e.to_pct is not None:
                deltas.append(e.to_pct - e.from_pct)
        if not deltas:
            return None
        return sum(deltas) / len(deltas)

    def reason_snippet(g: ChangeGroup, limit: int = 2) -> str:
        reasons = [e.reason for e in g.entries if e.reason]
        if not reasons:
            return ''
        freq: Dict[str, int] = {}
        for r in reasons:
            rr = r.strip()
            if not rr:
                continue
            freq[rr] = freq.get(rr, 0) + 1
        picks = [x[0] for x in sorted(freq.items(), key=lambda x: (-x[1], len(x[0]), x[0]))[:limit]]
        return ' / '.join(picks)

    group_stats = []
    for g in groups:
        models_mentioned = uniq_models(g)
        dcnt = dir_counts(g)
        group_stats.append({
            'group': g,
            'name': main_name(g),
            'mentioned_models': models_mentioned,
            'mentioned_n': len(models_mentioned),
            'dir_counts': dcnt,
            'avg_delta': avg_delta(g),
            'reasons': reason_snippet(g),
        })

    inc = sorted(group_stats, key=lambda x: (-x['dir_counts']['增'], -x['mentioned_n'], x['name']))
    dec = sorted(group_stats, key=lambda x: (-x['dir_counts']['减'], -x['mentioned_n'], x['name']))
    mixed = [x for x in group_stats if x['dir_counts']['增'] and x['dir_counts']['减']]
    mixed.sort(key=lambda x: (-(x['dir_counts']['增'] + x['dir_counts']['减']), -x['mentioned_n'], x['name']))

    def pick_top(lst, *, key: str, n: int) -> List[Dict]:
        out = []
        for x in lst:
            if x['dir_counts'].get(key, 0) <= 0:
                continue
            out.append(x)
            if len(out) >= n:
                break
        return out

    def fmt_reason(s: str) -> str:
        t = (s or '').strip()
        if not t:
            return ''
        t = t.replace('\n', ' ')
        t = re.sub(r'\s+', ' ', t)
        if len(t) > 40:
            t = t[:40].rstrip()
        return t

    inc_top = pick_top(inc, key='增', n=3)
    dec_top = pick_top(dec, key='减', n=3)
    mixed_top = mixed[:2]

    parts: List[str] = []
    parts.append(f'综合当日{model_count}份报告的“定投增减要点”，可以概括为：')

    if inc_top:
        names = '、'.join(x['name'] for x in inc_top)
        reasons = [fmt_reason(x['reasons']) for x in inc_top if fmt_reason(x['reasons'])]
        if reasons:
            parts.append(f'多份报告倾向把定投多放在{names}，常见理由包括：' + '；'.join(reasons) + '。')
        else:
            parts.append(f'多份报告倾向把定投多放在{names}。')

    if dec_top:
        names = '、'.join(x['name'] for x in dec_top)
        reasons = [fmt_reason(x['reasons']) for x in dec_top if fmt_reason(x['reasons'])]
        if reasons:
            parts.append(f'同时，多份报告建议适当收缩{names}，常见理由包括：' + '；'.join(reasons) + '。')
        else:
            parts.append(f'同时，多份报告建议适当收缩{names}。')

    if mixed_top:
        seg = []
        for x in mixed_top:
            c = x['dir_counts']
            name = x['name']
            r = fmt_reason(x['reasons'])
            if r:
                seg.append(f'{name}分歧较大（{c["增"]}份建议加一点、{c["减"]}份建议减一点），原因多提到：{r}')
            else:
                seg.append(f'{name}分歧较大（{c["增"]}份建议加一点、{c["减"]}份建议减一点）')
        parts.append('在分歧方面，' + '；'.join(seg) + '。')

    paragraph = ''.join(parts).replace('\n', '').strip()
    if len(paragraph) > max_chars:
        paragraph = paragraph[:max_chars].rstrip()
    return paragraph

def select_best_candidate(cands: List[CellCandidate]) -> Optional[CellCandidate]:
    if not cands: return None
    # Priority: 
    # 1. Not missing (display != '—')
    # 2. Longer display text
    # 3. raw_model dictionary order (later is better)
    
    def score(c: CellCandidate):
        missing = (c.display.strip() == '—')
        return (
            1 if missing else 0,
            -len(c.display or ''),
            c.raw_model # We want MAX raw_model, so when sorting ASC, we want it at the end.
                        # But here we want to return the BEST at index 0.
                        # So we sort by "Badness".
                        # Missing=1 is bad.
                        # Short len (high negative) is bad.
                        # Low raw_model is bad.
                        # Wait, "按 raw_model 字典序取更靠后者" -> Z is better than A.
                        # If we sort ASC: A...Z. Z is last.
                        # If we want Z at index 0, we need to sort DESC or invert.
                        # Let's simply sort normally and take [-1]? No, mixed criteria.
        )
    
    # Let's sort such that BEST is at index 0.
    # Badness: 
    # 1. Missing (True > False). So missing=True is worse.
    # 2. Length (Shorter is worse).
    # 3. raw_model (Smaller is worse).
    
    sorted_cands = sorted(cands, key=lambda c: (
        1 if c.display.strip() == '—' else 0, # 0 is better
        -len(c.display or ''), # Smaller (more negative) is better (longer)
        # We want Z (larger) to be better (smaller index).
        # We can't negate string. 
        # So let's use Reverse Sort.
    ))
    
    # If we use Reverse Sort (DESC):
    # 1. Missing: False (0) > True (1). Wait, we want False to be first. 
    #    If we sort DESC, 1 comes before 0. That puts Missing first. BAD.
    
    # Let's implement custom comparator or just do multi-pass.
    
    # Pass 1: Filter non-missing
    non_missing = [c for c in cands if c.display.strip() != '—']
    if not non_missing:
        # All missing. Return the one with largest raw_model.
        return sorted(cands, key=lambda c: c.raw_model, reverse=True)[0]
    
    # Pass 2: Find max length
    max_len = max(len(c.display) for c in non_missing)
    longest = [c for c in non_missing if len(c.display) == max_len]
    
    # Pass 3: Largest raw_model
    longest.sort(key=lambda c: c.raw_model, reverse=True)
    return longest[0]

def summarize_consensus(candidates: List[Optional[CellCandidate]]) -> Tuple[str, str]:
    usable = [c for c in candidates if c and c.direction_stat]
    
    if not usable:
        return '分歧（无明显偏向）', '数据不足；范围 —–—'

    counts = {'增': 0, '减': 0, '不变': 0}
    pcts = []
    for c in usable:
        counts[c.direction_stat] += 1
        if c.pct is not None:
            pcts.append(c.pct)

    n = len(usable)
    max_vote = max(counts.values())
    top_dirs = [k for k, v in counts.items() if v == max_vote]
    
    if len(top_dirs) == 1:
        bias_dir = top_dirs[0]
        bias_str = f'偏{bias_dir}'
    else:
        bias_dir = None
        bias_str = '无明显偏向'
    
    ratio = max_vote / n
    if ratio == 1.0:
        cons = f'一致（{bias_dir}）' if bias_dir else '一致（无明显偏向）' # Should be bias_dir
    elif ratio >= 0.75:
        cons = f'基本一致（{bias_str}）'
    else:
        cons = f'分歧（{bias_str}）'
        
    if n == 1:
        cons = f'分歧（{bias_str}）'

    range_str = f'{format_pct(min(pcts))}–{format_pct(max(pcts))}' if pcts else '—–—'
    
    if n == 1:
        summ = f'数据不足；范围 {range_str}'
    else:
        summ = f"{counts['增']}增/{counts['减']}减/{counts['不变']}不变；范围 {range_str}"
        
    return cons, summ

def render_table(headers: List[str], rows: List[List[str]]) -> str:
    def esc(s): return (s or '—').replace('\n', ' ').strip()
    lines = []
    lines.append('| ' + ' | '.join(map(esc, headers)) + ' |')
    lines.append('|' + '|'.join(['---'] * len(headers)) + '|')
    for r in rows:
        lines.append('| ' + ' | '.join(map(esc, r)) + ' |')
    return '\n'.join(lines)

def _run_git(args: List[str]) -> Tuple[int, str, str]:
    p = subprocess.run(
        ['git', '-c', 'core.quotepath=false'] + args,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
    )
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()

def publish_to_github(paths: List[Path], message: str, *, dry_run: bool) -> bool:
    code, out, err = _run_git(['rev-parse', '--is-inside-work-tree'])
    if code != 0 or out.lower() != 'true':
        print('GitHub 上传失败：当前目录不是 Git 仓库')
        if err:
            print(err)
        return False

    code, out, err = _run_git(['diff', '--cached', '--name-only'])
    if code != 0:
        print('GitHub 上传失败：无法读取暂存区状态')
        if err:
            print(err)
        return False
    if out.strip():
        print('GitHub 上传已跳过：暂存区已有变更，请先处理暂存区后再上传')
        return False

    rels: List[str] = []
    for p in paths:
        try:
            rels.append(str(p.relative_to(ROOT)))
        except Exception:
            rels.append(str(p))

    if dry_run:
        print('GitHub 上传（dry-run）：')
        print('  git add -- ' + ' '.join(rels))
        print(f'  git commit -m "{message}" -- ' + ' '.join(rels))
        print('  git push')
        return True

    code, out, err = _run_git(['add', '--'] + rels)
    if code != 0:
        print('GitHub 上传失败：git add 失败')
        if err:
            print(err)
        return False

    code, out, err = _run_git(['diff', '--cached', '--name-only'])
    if code != 0:
        print('GitHub 上传失败：无法读取暂存区变更')
        if err:
            print(err)
        return False
    staged = [x.strip() for x in out.splitlines() if x.strip()]
    if not staged:
        print('GitHub 上传：无变更，跳过提交与推送')
        return True

    allow = set(rels)
    if any(x not in allow for x in staged):
        print('GitHub 上传已停止：暂存区包含非目标文件')
        print('暂存区文件：' + ' / '.join(staged))
        return False

    code, out, err = _run_git(['commit', '-m', message, '--'] + rels)
    if code != 0:
        print('GitHub 上传失败：git commit 失败')
        if err:
            print(err)
        return False

    code, out, err = _run_git(['push'])
    if code != 0:
        print('GitHub 上传失败：git push 失败')
        if err:
            print(err)
        return False

    print('GitHub 上传：已提交并推送')
    return True

# --- Main Execution ---

def main(date_str: str, *, force: bool, validate_only: bool, publish: bool, publish_dry_run: bool) -> int:
    input_dir = ROOT / '报告' / date_str
    output_path = OUTPUT_DIR / f'{date_str}_最终投资总结.md'
    file_re = re.compile(rf'^{re.escape(date_str)}_(.+)_投资建议\.md$')

    if not input_dir.exists():
        print(f"Input dir {input_dir} does not exist.")
        return 1

    files = []
    for p in input_dir.iterdir():
        if not p.is_file(): continue
        m = file_re.match(p.name)
        if m:
            files.append((p, m.group(1)))
    
    if not files:
        print(f"No files matching pattern in {input_dir}")
        return 1

    _, plan_items = load_strategy_investment_plan_items(date_str)
    source_names = [x.get('fund_name', '').strip() for x in plan_items if isinstance(x, dict) and x.get('fund_name')]
    source_names = [x for x in source_names if x]
    source_names_set = set(source_names)
    source_norm_to_names: Dict[str, List[str]] = {}
    for nm in source_names:
        n = normalize_item_name(nm)
        for v in item_norm_variants(n):
            source_norm_to_names.setdefault(v, []).append(nm)

    ok, issues, source_hint = validate_report_items_against_strategy(date_str, files)
    fatal_issues = [it for it in issues if it.missing_items]
    warn_issues = [it for it in issues if (not it.missing_items and (it.extra_items or it.mapped_name_mismatches))]

    if fatal_issues:
        print('标的校验：发现与数据源不一致')
        print(source_hint)
        for it in fatal_issues:
            print(f'- {it.file_name}（{it.raw_model}）')
            if it.extra_items:
                print('  - 报告存在但数据源未匹配：' + ' / '.join(it.extra_items))
            if it.missing_items:
                print('  - 数据源存在但报告缺失：' + ' / '.join(it.missing_items))
            if it.mapped_name_mismatches:
                pairs = [f'{a} -> {b}' for a, b in it.mapped_name_mismatches]
                print('  - 名称不一致但已匹配：' + ' / '.join(pairs))

        if validate_only:
            return 2
        if not force:
            print('已停止生成。请修正报告/数据源后重试；如确认继续生成，添加 --force。')
            return 2
        print('已启用 --force，将继续生成每日最终报告。')
    elif warn_issues:
        print('标的校验：通过（存在报告多出标的或名称不一致但已匹配；生成时将忽略多出标的）')
        print(source_hint)
        for it in warn_issues:
            print(f'- {it.file_name}（{it.raw_model}）')
            if it.extra_items:
                print('  - 报告多出标的（将忽略）：' + ' / '.join(it.extra_items))
            if it.mapped_name_mismatches:
                pairs = [f'{a} -> {b}' for a, b in it.mapped_name_mismatches]
                print('  - 名称不一致但已匹配：' + ' / '.join(pairs))
        if validate_only:
            return 0
    else:
        if validate_only:
            print('标的校验：通过')
            print(source_hint)
            return 0

    parsed_models = []
    for path, raw_model in files:
        text = path.read_text(encoding='utf-8')
        canon = canonicalize_model(raw_model)
        cat_order, cats = parse_categories(text, raw_model)
        item_order, items = parse_items(text, raw_model)
        if source_names:
            filtered: Dict[str, CellCandidate] = {}
            for k, cand in items.items():
                mapped = map_report_item_to_source_name(
                    k,
                    source_names=source_names,
                    source_names_set=source_names_set,
                    source_norm_to_names=source_norm_to_names,
                )
                if not mapped:
                    continue
                if mapped in filtered:
                    filtered[mapped] = select_best_candidate([filtered[mapped], cand]) or filtered[mapped]
                else:
                    filtered[mapped] = cand
            items = filtered
            item_order = [nm for nm in source_names if nm in items]
        top_changes = parse_top_changes(text, raw_model, canon)
        themes, no_new = parse_themes(text, raw_model)
        
        parsed_models.append(ModelParsed(
            raw_model=raw_model,
            canonical_model=canon,
            categories=cats,
            items=items,
            top_changes=top_changes,
            themes=themes,
            explicitly_no_new=no_new,
            cat_order=cat_order,
            item_order=item_order
        ))

    # Identify columns
    present_models = sorted({m.canonical_model for m in parsed_models}, key=model_sort_key)
    model_cols = present_models
                 
    # Aggregate Data
    all_cats = set()
    
    # Stability ordering maps
    cat_seen_order = {}
    item_seen_order = {nm: i for i, nm in enumerate(source_names)} if source_names else {}
    
    for m in parsed_models:
        for k in m.categories: all_cats.add(k)
        
        for k in m.cat_order:
            if k not in cat_seen_order: cat_seen_order[k] = len(cat_seen_order)
        for k in m.item_order:
            if k not in item_seen_order: item_seen_order[k] = len(item_seen_order)

    # Sort Categories
    cat_list = list(all_cats)
    def cat_sort_key(k):
        if k in CATEGORY_ORDER_FIXED: return (0, CATEGORY_ORDER_FIXED.index(k))
        return (1, k)
    cat_list.sort(key=cat_sort_key)

    # Group Items (handle name variants across models, e.g. DeepSeek naming)
    @dataclass
    class ItemGroup:
        names: List[str]
        norms: List[str]
        entries_by_col: Dict[str, List[ItemEntry]]
        order_key: int

    all_item_entries: List[ItemEntry] = []
    for pm in parsed_models:
        for name, cand in pm.items.items():
            all_item_entries.append(ItemEntry(
                name=name,
                name_norm=normalize_item_name(name),
                candidate=cand,
                canonical_model=pm.canonical_model,
            ))

    item_groups: List[ItemGroup] = []
    for ie in all_item_entries:
        placed = False

        for g in item_groups:
            match = any(item_norm_similar(ie.name_norm, gn) for gn in g.norms)

            if match:
                g.names.append(ie.name)
                g.norms.append(ie.name_norm)
                if ie.canonical_model not in g.entries_by_col:
                    g.entries_by_col[ie.canonical_model] = []
                g.entries_by_col[ie.canonical_model].append(ie)
                g.order_key = min(g.order_key, item_seen_order.get(ie.name, 999999))
                placed = True
                break

        if not placed:
            item_groups.append(ItemGroup(
                names=[ie.name],
                norms=[ie.name_norm],
                entries_by_col={ie.canonical_model: [ie]},
                order_key=item_seen_order.get(ie.name, 999999),
            ))

    def item_group_sort_key(g: ItemGroup):
        return (g.order_key, sorted(set(g.names), key=lambda x: (len(x), x))[0])

    item_groups.sort(key=item_group_sort_key)

    # Build Tables
    cat_rows = []
    cat_cons_rows = []
    
    for cat in cat_list:
        row = [cat]
        cands_for_row = []
        for col in model_cols:
            # Find all candidates for this canonical model
            cands = []
            for pm in parsed_models:
                if pm.canonical_model == col and cat in pm.categories:
                    cands.append(pm.categories[cat])
            
            best = select_best_candidate(cands)
            cands_for_row.append(best)
            row.append(best.display if best else '—')
        
        cons, summ = summarize_consensus(cands_for_row)
        row.append(cons)
        row.append(summ)
        cat_rows.append(row)
        if cons.startswith('一致') or cons.startswith('基本一致'):
            cat_cons_rows.append(row)

    item_rows = []
    item_cons_rows = []
    
    for g in item_groups:
        freq = {}
        for n in g.names:
            freq[n] = freq.get(n, 0) + 1
        main_name = sorted(freq.items(), key=lambda x: (-x[1], len(x[0]), x[0]))[0][0]

        row = [main_name]
        cands_for_row = []
        for col in model_cols:
            cands = [ie.candidate for ie in g.entries_by_col.get(col, [])]
            best = select_best_candidate(cands) if cands else None
            cands_for_row.append(best)
            row.append(best.display if best else '—')
            
        cons, summ = summarize_consensus(cands_for_row)
        row.append(cons)
        row.append(summ)
        item_rows.append(row)
        if cons.startswith('一致') or cons.startswith('基本一致'):
            item_cons_rows.append(row)

    # Themes
    @dataclass
    class ThemeGroup:
        names: List[str]
        norms: List[str]
        tokens: Set[str]
        entries_by_col: Dict[str, List[ThemeEntry]]

    groups = []
    
    # Collect all entries
    all_entries = []
    for pm in parsed_models:
        for te in pm.themes:
            all_entries.append((pm.canonical_model, te))
            
    # Grouping
    for col, te in all_entries:
        placed = False
        te_tokens = set(topic_tokens(te.topic_norm))
        
        for g in groups:
            # Check similarity
            match = False
            if te.topic_norm in g.norms: match = True
            else:
                for gn in g.norms:
                    if gn and (gn in te.topic_norm or te.topic_norm in gn):
                        match = True
                        break
                if not match:
                    if len(te_tokens & g.tokens) >= 2:
                        match = True
            
            if match:
                g.names.append(te.topic)
                g.norms.append(te.topic_norm)
                g.tokens |= te_tokens
                if col not in g.entries_by_col: g.entries_by_col[col] = []
                g.entries_by_col[col].append(te)
                placed = True
                break
        
        if not placed:
            groups.append(ThemeGroup(
                names=[te.topic],
                norms=[te.topic_norm],
                tokens=te_tokens,
                entries_by_col={col: [te]}
            ))

    # Build Theme Rows
    theme_rows = []
    
    # Sort groups by number of proposers (columns involved)
    def group_sort_key(g):
        return -len(g.entries_by_col)
    groups.sort(key=group_sort_key)
    
    for g in groups:
        # Pick main name
        freq = {}
        for n in g.names: freq[n] = freq.get(n, 0) + 1
        main_name = sorted(freq.items(), key=lambda x: (-x[1], len(x[0]), x[0]))[0][0]
        main_norm = normalize_topic_name(main_name)
        
        row = [main_name]
        diffs = []
        
        # Merge note
        distinct = sorted(set(g.names), key=lambda x: (len(x), x))
        if len(distinct) > 1:
            diffs.append('合并：' + ' / '.join(distinct))
            
        proposers = list(g.entries_by_col.keys())
        
        for col in model_cols:
            if col in g.entries_by_col:
                entries = g.entries_by_col[col]
                # Best entry: closest to main name
                def dist(e):
                    if e.topic_norm == main_norm: return 0
                    if main_norm in e.topic_norm or e.topic_norm in main_norm: return 1
                    return 2
                best_e = sorted(entries, key=dist)[0]
                row.append(best_e.display)
                
                others = [e.topic for e in entries if e is not best_e]
                if others:
                    diffs.append(f'{col} 另提：' + ' / '.join(sorted(set(others))))
            else:
                row.append('—')

        if len(proposers) == 1:
            diffs.append(f'仅 {proposers[0]} 提出')
            
        # No New check
        no_new_cols = []
        for col in model_cols:
            if col not in proposers:
                # Check if this model explicitly said no new
                # We need to aggregate across all files for this canon model
                is_no_new = False
                for pm in parsed_models:
                    if pm.canonical_model == col and pm.explicitly_no_new:
                        is_no_new = True
                if is_no_new:
                    no_new_cols.append(col)
        
        if no_new_cols:
            diffs.append('其中 ' + ' / '.join(sorted(no_new_cols)) + ' 明确不新增')
            
        row.append('；'.join(diffs) if diffs else '—')
        theme_rows.append(row)

    # Output Markdown
    md = []
    md.append(f'# 投资总结（{date_str}）\n')
    
    md.append('## 0. 定投增减要点综述（1000字以内）')
    md.append(summarize_top_changes_paragraph(parsed_models, max_chars=1000))
    md.append('')

    md.append(f'## 1. 大板块比例调整建议（按大类横向对比）')
    md.append(render_table(['大板块'] + model_cols + ['一致性', '分歧摘要'], cat_rows))
    md.append('\n### 一致建议')
    md.append(render_table(['大板块'] + model_cols + ['一致性', '分歧摘要'], cat_cons_rows))
    
    md.append(f'\n## 2. 定投计划逐项建议（按标的横向对比）')
    md.append(render_table(['标的'] + model_cols + ['一致性', '分歧摘要'], item_rows))
    md.append('\n### 一致建议')
    md.append(render_table(['标的'] + model_cols + ['一致性', '分歧摘要'], item_cons_rows))
    
    md.append(f'\n## 3. 新的定投方向建议（按主题横向对比）')
    md.append(render_table(['主题/方向'] + model_cols + ['异同'], theme_rows))
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path.write_text('\n'.join(md), encoding='utf-8')
    print(f"Successfully generated: {output_path}")
    if publish:
        ok = publish_to_github(
            [output_path],
            f'每日总结 {date_str}',
            dry_run=publish_dry_run,
        )
        if not ok:
            return 3
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', dest='date', default=DEFAULT_DATE)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--publish-dry-run', action='store_true')
    args = parser.parse_args()
    sys.exit(main(
        args.date,
        force=args.force,
        validate_only=args.validate_only,
        publish=args.publish,
        publish_dry_run=args.publish_dry_run,
    ))
