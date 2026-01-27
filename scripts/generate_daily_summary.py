import argparse
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

ROOT = Path.cwd()

_MD_MARK_RE = re.compile(r'(\*\*|__|\*|_|`)+')


def strip_markdown_marks(s: str) -> str:
    if not s:
        return ''
    return _MD_MARK_RE.sub('', s).strip()


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--date", dest="report_date", default=date.today().isoformat())
    return p.parse_args()


def paths_for(report_date: str):
    input_dir = ROOT / "报告" / report_date
    output_dir = ROOT / "每日最终报告"
    output_path = output_dir / f"{report_date}_最终投资总结.md"
    file_re = re.compile(rf"^{re.escape(report_date)}_(.+)_投资建议\.md$")
    return input_dir, output_dir, output_path, file_re

# Model Order
MODEL_ORDER_FIXED = [
    'DeepSeek',
    'Gemini',
    'GPT-5.2',
    'Grok-4',
    'GLM-4.7',
    'Kimi',
    'MiniMax-M2.1',
    'TraeAI',
]

CATEGORY_ORDER_FIXED = ['债券', '中股', '期货', '美股']

# --- Helper Functions ---

def canonicalize_model(raw_model: str) -> str:
    s = raw_model.strip()
    low = s.lower()
    if low.startswith('gemini'): return 'Gemini'
    if low.startswith('kimi'): return 'Kimi'
    if low.startswith('minimax'): return 'MiniMax-M2.1'
    if low.startswith('traeai'): return 'TraeAI'
    if low.startswith('deepseek'): return 'DeepSeek'
    if low.startswith('grok'): return 'Grok-4'
    if low.startswith('glm'): return 'GLM-4.7'
    return s

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

def extract_section_lines(text: str, heading_substring: str) -> List[str]:
    lines = text.splitlines()
    start_idx = None
    for i, ln in enumerate(lines):
        if heading_substring in ln:
            start_idx = i
            break
    if start_idx is None:
        return []

    out = []
    for ln in lines[start_idx + 1:]:
        if ln.startswith('## '):
            break
        out.append(ln)
    return out

def parse_tables_from_lines(lines: List[str]) -> List[List[List[str]]]:
    tables = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith('|'):
            block = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                block.append(lines[i])
                i += 1
            parsed = parse_markdown_table(block)
            if parsed:
                tables.append(parsed)
            continue
        i += 1
    return tables

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
        hh = strip_markdown_marks(h).strip()
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
class ModelParsed:
    raw_model: str
    canonical_model: str
    categories: Dict[str, CellCandidate]
    items: Dict[str, CellCandidate]
    themes: List[ThemeEntry]
    explicitly_no_new: bool
    cat_order: List[str]
    item_order: List[str]

# --- Logic ---

def direction_to_stat(direction: Optional[str], *, is_category: bool) -> Optional[str]:
    if not direction: return None
    d = direction.strip()
    if any(x in d for x in ['维持', '不变', '保持']): return '不变'
    if any(x in d for x in ['暂停', '停止', '减半', '减仓', '减配', '降低', '下调']): return '减'
    if any(x in d for x in ['加仓', '加码', '提升', '上调', '增配']): return '增'
    
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
        table, _ = find_table_after_heading(text, '大板块比例调整建议')
    if not table or len(table) < 2:
        return [], {}

    header = table[0]
    body = table[1:]
    if body and is_separator_row(body[0]): body = body[1:]

    key_col = find_col(header, ['大板块'])
    if key_col is None:
        key_col = find_col(header, ['大类'])

    pct_col = find_col(header, ['建议%'])
    if pct_col is None:
        pct_col = find_col(header, ['目标比例'])
    if pct_col is None:
        pct_col = find_col(header, ['目标%'])

    dir_col = find_col(header, ['建议'], excludes=['建议%'])
    if dir_col is None:
        dir_col = find_col(header, ['调整建议'])

    if key_col is None or pct_col is None: return [], {}

    order = []
    out = {}
    for row in body:
        needed = [key_col, pct_col]
        if dir_col is not None:
            needed.append(dir_col)
        if len(row) <= max(needed): continue
        key = strip_markdown_marks(row[key_col]).strip()
        if not key: continue
        
        pct = parse_float_from_text(strip_markdown_marks(row[pct_col]).strip())
        direction = None
        if dir_col is not None:
            dir_cell = strip_markdown_marks(row[dir_col]).strip()
            if dir_cell:
                direction = dir_cell

        if direction:
            if re.fullmatch(r'[+-]?\d+(?:\.\d+)?%?', direction):
                v = parse_float_from_text(direction)
                if v is not None:
                    if v > 0:
                        direction = '增配'
                    elif v < 0:
                        direction = '减配'
                    else:
                        direction = '不变'
        
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
    order = []
    out = {}
    section_lines = extract_section_lines(text, '定投计划逐项建议')
    if not section_lines:
        return [], {}

    tables = parse_tables_from_lines(section_lines)
    if not tables:
        return [], {}

    for table in tables:
        if len(table) < 2:
            continue

        header = table[0]
        body = table[1:]
        if body and is_separator_row(body[0]): body = body[1:]

        key_col = find_col(header, ['标的'])
        if key_col is None:
            continue

        pct_col = find_col(header, ['建议%'])
        if pct_col is None:
            pct_col = find_col(header, ['建议比例'])

        dir_col = find_col(header, ['建议'], excludes=['建议%'])
        if dir_col is None:
            dir_col = find_col(header, ['建议操作'])
        if dir_col is None:
            dir_col = find_col(header, ['操作'])

        for row in body:
            needed = [key_col]
            if pct_col is not None:
                needed.append(pct_col)
            if dir_col is not None:
                needed.append(dir_col)
            if len(row) <= max(needed):
                continue

            key = strip_markdown_marks(row[key_col]).strip()
            if not key:
                continue

            pct = None
            if pct_col is not None:
                pct = parse_float_from_text(strip_markdown_marks(row[pct_col]).strip())

            direction = None
            if dir_col is not None:
                direction = strip_markdown_marks(row[dir_col]).strip() or None

            pct_disp = format_pct(pct) if pct is not None else '—'
            dir_disp = direction if direction else '—'

            if pct is None and not direction:
                display = '—'
            elif pct is not None:
                display = f'{pct_disp}（{dir_disp}）'
            else:
                display = f'—（{dir_disp}）'

            if key not in out:
                order.append(key)
                out[key] = CellCandidate(
                    display=display,
                    pct=pct,
                    direction_raw=direction,
                    direction_stat=direction_to_stat(direction, is_category=False),
                    raw_model=raw_model
                )
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

def parse_themes(text: str, raw_model: str) -> Tuple[List[ThemeEntry], bool]:
    table, remaining = find_table_after_heading(text, '新的定投方向建议')
    
    explicitly_no_new = bool(re.search(r'本周期不新增|不新增|无新增|无需新增', remaining))
    
    if not table:
        section_lines = extract_section_lines(text, '新的定投方向建议')
        entries = []
        for ln in section_lines:
            m = re.match(r'^\s*(?:\d+[\.\、]|[-*])\s*(.+)$', ln.strip())
            if not m:
                continue
            item = m.group(1).strip()
            item = strip_markdown_marks(item)
            m_topic = re.match(r'^(.*?)\s*(?:[-—–]\s+)(.+)$', item)
            if m_topic:
                topic = m_topic.group(1).strip()
            else:
                topic = item.strip()
            if not topic:
                continue
            entries.append(ThemeEntry(
                topic=topic,
                topic_norm=normalize_topic_name(topic),
                pct=None,
                caliber='—',
                display='—',
                raw_model=raw_model
            ))
        return entries, explicitly_no_new

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
    
    def remove_pct_from_caliber(caliber: str) -> str:
        if not caliber:
            return '—'
        cleaned = re.sub(r'\s*的?\s*-?\d+(?:\.\d+)?\s*%?\s*', '', caliber, count=1).strip()
        if cleaned.endswith('的'):
            cleaned = cleaned[:-1].strip()
        return cleaned or '—'

    entries = []
    for row in body:
        if len(row) <= max(topic_col, pct_col, caliber_col): continue
        topic = strip_markdown_marks(row[topic_col]).strip()
        if not topic or topic in ['无', '—', '-']: continue
        
        pct_cell = strip_markdown_marks(row[pct_col]).strip()
        caliber_cell = strip_markdown_marks(row[caliber_col]).strip()
        
        pct = parse_float_from_text(pct_cell)
        caliber = caliber_cell or '—'
        
        if pct is None:
            pct_alt = parse_float_from_text(caliber_cell)
            if pct_alt is not None and (not pct_cell or pct_cell in {'—', '-', '新增方向'}):
                pct = pct_alt
                caliber = remove_pct_from_caliber(caliber_cell)
        
        display = '—'
        if pct is not None:
            display = f'{format_pct(pct)}（{caliber}）'
            
        entries.append(ThemeEntry(
            topic=topic,
            topic_norm=normalize_topic_name(topic),
            pct=pct,
            caliber=caliber,
            display=display,
            raw_model=raw_model
        ))

    if not entries:
         if bool(re.search(r'本周期不新增|不新增|无新增|无需新增', remaining)):
            explicitly_no_new = True

    return entries, explicitly_no_new

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

# --- Main Execution ---

def main():
    args = parse_args()
    report_date = args.report_date
    input_dir, output_dir, output_path, file_re = paths_for(report_date)

    if not input_dir.exists():
        print(f"Input dir {input_dir} does not exist.")
        return

    files = []
    for p in input_dir.iterdir():
        if not p.is_file(): continue
        m = file_re.match(p.name)
        if m:
            files.append((p, m.group(1)))
    
    if not files:
        print(f"No files matching pattern in {input_dir}")
        return

    parsed_models = []
    for path, raw_model in files:
        text = path.read_text(encoding='utf-8')
        canon = canonicalize_model(raw_model)
        cat_order, cats = parse_categories(text, raw_model)
        item_order, items = parse_items(text, raw_model)
        themes, no_new = parse_themes(text, raw_model)
        
        parsed_models.append(ModelParsed(
            raw_model=raw_model,
            canonical_model=canon,
            categories=cats,
            items=items,
            themes=themes,
            explicitly_no_new=no_new,
            cat_order=cat_order,
            item_order=item_order
        ))

    # Identify columns
    present_canons = sorted({m.canonical_model for m in parsed_models})
    model_cols = [m for m in MODEL_ORDER_FIXED if m in present_canons] + \
                 sorted([m for m in present_canons if m not in MODEL_ORDER_FIXED])
                 
    # Aggregate Data
    all_cats = set()
    all_items = set()
    
    # Stability ordering maps
    cat_seen_order = {}
    item_seen_order = {}
    
    for m in parsed_models:
        for k in m.categories: all_cats.add(k)
        for k in m.items: all_items.add(k)
        
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

    # Sort Items (First seen order)
    item_list = list(all_items)
    item_list.sort(key=lambda k: (item_seen_order.get(k, 9999), k))

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
    
    for item in item_list:
        row = [item]
        cands_for_row = []
        for col in model_cols:
            cands = []
            for pm in parsed_models:
                if pm.canonical_model == col and item in pm.items:
                    cands.append(pm.items[item])
            best = select_best_candidate(cands)
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
    md.append(f'# 投资总结（{report_date}）\n')
    
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
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text('\n'.join(md), encoding='utf-8')
    print(f"Successfully generated: {output_path}")

if __name__ == '__main__':
    main()
