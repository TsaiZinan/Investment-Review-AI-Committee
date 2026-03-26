import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "Data" / "model_registry.json"
REPORT_DIR = ROOT / "报告"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class CandidateRow:
    canonical_name: str
    suggested_input: str
    family: str
    active_count: int
    recent_count: int
    last_seen: Optional[str]
    pinned: bool
    sort_key: Tuple[int, int, str]


def _default_registry() -> Dict[str, Any]:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {
        "version": 1,
        "settings": {
            "active_window_days": 30,
            "active_min_seen": 2,
            "recent_window_days": 90,
            "fallback_limit": 8,
        },
        "families": [],
        "models": [],
        "observations": {},
    }


def normalize_model_token(value: str) -> str:
    text = unicodedata.normalize("NFKC", (value or "").strip()).lower()
    return re.sub(r"[\s\-_./()（）]+", "", text)


def parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def ensure_registry_shape(registry: Dict[str, Any]) -> Dict[str, Any]:
    default = json.loads((ROOT / "Data" / "model_registry.json").read_text(encoding="utf-8")) if REGISTRY_PATH.exists() else _default_registry()
    merged = {
        "version": registry.get("version", default.get("version", 1)),
        "settings": {**default.get("settings", {}), **registry.get("settings", {})},
        "families": [],
        "models": [],
        "observations": registry.get("observations", {}) or {},
    }

    family_by_key: Dict[str, Dict[str, Any]] = {}
    for family in default.get("families", []):
        key = str(family.get("key", "")).strip()
        if key:
            family_by_key[key] = dict(family)
    for family in registry.get("families", []):
        key = str(family.get("key", "")).strip()
        if not key:
            continue
        current = family_by_key.get(key, {})
        merged_family = {**current, **family}
        prefixes = current.get("prefixes", []) + family.get("prefixes", [])
        uniq_prefixes: List[str] = []
        seen_prefixes: Set[str] = set()
        for prefix in prefixes:
            p = str(prefix).strip()
            if not p:
                continue
            norm = normalize_model_token(p)
            if norm in seen_prefixes:
                continue
            seen_prefixes.add(norm)
            uniq_prefixes.append(p)
        merged_family["prefixes"] = uniq_prefixes
        family_by_key[key] = merged_family
    merged["families"] = sorted(family_by_key.values(), key=lambda item: (int(item.get("order", 9999)), str(item.get("key", ""))))

    model_by_canonical: Dict[str, Dict[str, Any]] = {}
    for model in default.get("models", []):
        canonical = str(model.get("canonical_name", "")).strip()
        if canonical:
            model_by_canonical[canonical] = dict(model)
    for model in registry.get("models", []):
        canonical = str(model.get("canonical_name", "")).strip()
        if not canonical:
            continue
        current = model_by_canonical.get(canonical, {})
        merged_model = {**current, **model}
        aliases = current.get("aliases", []) + model.get("aliases", [])
        uniq_aliases: List[str] = []
        seen_aliases: Set[str] = set()
        for alias in aliases:
            alias_text = str(alias).strip()
            if not alias_text:
                continue
            norm = normalize_model_token(alias_text)
            if norm in seen_aliases:
                continue
            seen_aliases.add(norm)
            uniq_aliases.append(alias_text)
        if canonical not in uniq_aliases:
            uniq_aliases.insert(0, canonical)
        merged_model["aliases"] = uniq_aliases
        merged_model.setdefault("family", derive_family_key(canonical, merged))
        merged_model.setdefault("default_input", canonical)
        merged_model.setdefault("order", 9999)
        merged_model.setdefault("pinned", False)
        merged_model["canonical_name"] = canonical
        model_by_canonical[canonical] = merged_model
    merged["models"] = sorted(
        model_by_canonical.values(),
        key=lambda item: (
            family_order(item.get("family", ""), merged),
            int(item.get("order", 9999)),
            str(item.get("canonical_name", "")),
        ),
    )

    cleaned_observations: Dict[str, List[str]] = {}
    for raw_model, raw_dates in merged["observations"].items():
        model_name = str(raw_model).strip()
        if not model_name:
            continue
        seen_dates: Set[str] = set()
        valid_dates: List[str] = []
        for dt in raw_dates or []:
            dt_text = str(dt).strip()
            if not DATE_RE.match(dt_text) or dt_text in seen_dates:
                continue
            seen_dates.add(dt_text)
            valid_dates.append(dt_text)
        cleaned_observations[model_name] = sorted(valid_dates)
    merged["observations"] = cleaned_observations
    return merged


def load_registry() -> Dict[str, Any]:
    if REGISTRY_PATH.exists():
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    else:
        registry = _default_registry()
    return ensure_registry_shape(registry)


def save_registry(registry: Dict[str, Any]) -> None:
    REGISTRY_PATH.write_text(json.dumps(ensure_registry_shape(registry), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def family_order(family_key: str, registry: Dict[str, Any]) -> int:
    for family in registry.get("families", []):
        if str(family.get("key", "")).strip() == family_key:
            return int(family.get("order", 9999))
    return 9999


def derive_family_key(model_name: str, registry: Dict[str, Any]) -> str:
    token = normalize_model_token(model_name)
    for family in registry.get("families", []):
        prefixes = family.get("prefixes", []) or []
        for prefix in prefixes:
            if token.startswith(normalize_model_token(str(prefix))):
                return str(family.get("key", "")).strip()
    return "other"


def find_model_entry(model_name: str, registry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    token = normalize_model_token(model_name)
    if not token:
        return None
    for entry in registry.get("models", []):
        canonical = str(entry.get("canonical_name", "")).strip()
        if normalize_model_token(canonical) == token:
            return entry
        for alias in entry.get("aliases", []) or []:
            if normalize_model_token(str(alias)) == token:
                return entry
    return None


def canonicalize_model_name(model_name: str, registry: Optional[Dict[str, Any]] = None) -> str:
    registry = registry or load_registry()
    entry = find_model_entry(model_name, registry)
    return str(entry.get("canonical_name", "")).strip() if entry else (model_name or "").strip()


def build_model_sort_key(model_name: str, registry: Optional[Dict[str, Any]] = None) -> Tuple[int, int, str]:
    registry = registry or load_registry()
    entry = find_model_entry(model_name, registry)
    if entry:
        family = str(entry.get("family", "")).strip()
        return (family_order(family, registry), int(entry.get("order", 9999)), str(entry.get("canonical_name", "")).strip())
    derived_family = derive_family_key(model_name, registry)
    return (family_order(derived_family, registry), 9999, (model_name or "").strip())


def collect_report_observations() -> Dict[str, Set[str]]:
    observations: Dict[str, Set[str]] = {}
    if not REPORT_DIR.exists():
        return observations
    for day_dir in REPORT_DIR.iterdir():
        if not day_dir.is_dir() or not DATE_RE.match(day_dir.name):
            continue
        date_str = day_dir.name
        file_re = re.compile(rf"^{re.escape(date_str)}_(.+)_投资建议\.md$")
        for path in day_dir.iterdir():
            if not path.is_file():
                continue
            match = file_re.match(path.name)
            if not match:
                continue
            raw_model = match.group(1).strip()
            if not raw_model:
                continue
            observations.setdefault(raw_model, set()).add(date_str)
    return observations


def combine_observations(registry: Dict[str, Any]) -> Dict[str, Set[str]]:
    combined = collect_report_observations()
    for raw_model, raw_dates in (registry.get("observations", {}) or {}).items():
        model_name = str(raw_model).strip()
        if not model_name:
            continue
        target = combined.setdefault(model_name, set())
        for dt in raw_dates or []:
            if DATE_RE.match(str(dt).strip()):
                target.add(str(dt).strip())
    return combined


def ensure_model_entry(model_name: str, registry: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    model_text = (model_name or "").strip()
    entry = find_model_entry(model_text, registry)
    changed = False
    if entry:
        aliases = [str(alias).strip() for alias in entry.get("aliases", []) or [] if str(alias).strip()]
        if model_text and all(normalize_model_token(alias) != normalize_model_token(model_text) for alias in aliases):
            aliases.append(model_text)
            entry["aliases"] = aliases
            changed = True
        return entry, changed

    family = derive_family_key(model_text, registry)
    existing_orders = [
        int(item.get("order", 9999))
        for item in registry.get("models", [])
        if str(item.get("family", "")).strip() == family and str(item.get("order", "")).strip() != ""
    ]
    next_order = max(existing_orders) + 1 if existing_orders else 0
    entry = {
        "canonical_name": model_text,
        "family": family,
        "order": next_order,
        "default_input": model_text,
        "pinned": False,
        "aliases": [model_text],
    }
    registry.setdefault("models", []).append(entry)
    changed = True
    return entry, changed


def sync_registry_with_reports(registry: Dict[str, Any]) -> bool:
    changed = False
    for raw_model in sorted(collect_report_observations()):
        _, entry_changed = ensure_model_entry(raw_model, registry)
        changed = changed or entry_changed
    return changed


def register_observation(model_name: str, observed_date: str, registry: Dict[str, Any]) -> Tuple[str, bool]:
    entry, changed = ensure_model_entry(model_name, registry)
    observations = registry.setdefault("observations", {})
    dates = {str(dt).strip() for dt in observations.get(model_name, []) if DATE_RE.match(str(dt).strip())}
    if observed_date not in dates:
        dates.add(observed_date)
        observations[model_name] = sorted(dates)
        changed = True
    canonical = str(entry.get("canonical_name", "")).strip() or model_name.strip()
    return canonical, changed


def _counts_in_windows(raw_dates: Set[str], reference_date: date, active_window_days: int, recent_window_days: int) -> Tuple[int, int, Optional[str]]:
    active_cutoff = reference_date - timedelta(days=max(active_window_days - 1, 0))
    recent_cutoff = reference_date - timedelta(days=max(recent_window_days - 1, 0))
    active_count = 0
    recent_count = 0
    last_seen: Optional[str] = None
    for dt_text in raw_dates:
        dt = parse_iso_date(dt_text)
        if not dt:
            continue
        if dt >= active_cutoff:
            active_count += 1
        if dt >= recent_cutoff:
            recent_count += 1
        if last_seen is None or dt_text > last_seen:
            last_seen = dt_text
    return active_count, recent_count, last_seen


def _preferred_input(raw_stats: List[Tuple[str, int, int, Optional[str]]], entry: Dict[str, Any]) -> str:
    preferred = str(entry.get("default_input", "")).strip() or str(entry.get("canonical_name", "")).strip()
    if not raw_stats:
        return preferred
    ranked = sorted(
        raw_stats,
        key=lambda item: (
            item[1],
            item[2],
            item[3] or "",
            item[0] == preferred,
            item[0],
        ),
        reverse=True,
    )
    return ranked[0][0]


def _last_seen_sort_value(value: Optional[str]) -> int:
    dt = parse_iso_date(value)
    if not dt:
        return -1
    return dt.toordinal()


def build_candidate_rows(registry: Dict[str, Any], reference_date: Optional[date] = None) -> List[CandidateRow]:
    reference_date = reference_date or date.today()
    settings = registry.get("settings", {}) or {}
    active_window_days = int(settings.get("active_window_days", 30))
    active_min_seen = int(settings.get("active_min_seen", 2))
    recent_window_days = int(settings.get("recent_window_days", 90))
    combined = combine_observations(registry)

    raw_stats_by_canonical: Dict[str, List[Tuple[str, int, int, Optional[str]]]] = {}
    for raw_model, raw_dates in combined.items():
        canonical = canonicalize_model_name(raw_model, registry)
        active_count, recent_count, last_seen = _counts_in_windows(raw_dates, reference_date, active_window_days, recent_window_days)
        raw_stats_by_canonical.setdefault(canonical, []).append((raw_model, active_count, recent_count, last_seen))

    rows: List[CandidateRow] = []
    for entry in registry.get("models", []):
        canonical = str(entry.get("canonical_name", "")).strip()
        raw_stats = raw_stats_by_canonical.get(canonical, [])
        active_count = sum(item[1] for item in raw_stats)
        recent_count = sum(item[2] for item in raw_stats)
        last_seen = max((item[3] or "" for item in raw_stats), default="") or None
        pinned = bool(entry.get("pinned", False))
        if active_count < active_min_seen and recent_count == 0 and not pinned:
            continue
        suggested_input = _preferred_input(raw_stats, entry)
        rows.append(
            CandidateRow(
                canonical_name=canonical,
                suggested_input=suggested_input,
                family=str(entry.get("family", "")).strip(),
                active_count=active_count,
                recent_count=recent_count,
                last_seen=last_seen,
                pinned=pinned,
                sort_key=build_model_sort_key(canonical, registry),
            )
        )

    if rows:
        active_rows = [row for row in rows if row.active_count >= active_min_seen or row.pinned]
        if active_rows:
            rows = active_rows
        rows.sort(key=lambda row: (row.sort_key[0], row.sort_key[1], -(1 if row.pinned else 0), -row.active_count, -row.recent_count, -_last_seen_sort_value(row.last_seen), row.suggested_input))
        return rows

    fallback_limit = int(settings.get("fallback_limit", 8))
    recent_rows: List[CandidateRow] = []
    for entry in registry.get("models", []):
        canonical = str(entry.get("canonical_name", "")).strip()
        raw_stats = raw_stats_by_canonical.get(canonical, [])
        if not raw_stats and not entry.get("pinned", False):
            continue
        suggested_input = _preferred_input(raw_stats, entry)
        recent_count = max((item[2] for item in raw_stats), default=0)
        last_seen = max((item[3] or "" for item in raw_stats), default="") or None
        recent_rows.append(
            CandidateRow(
                canonical_name=canonical,
                suggested_input=suggested_input,
                family=str(entry.get("family", "")).strip(),
                active_count=sum(item[1] for item in raw_stats),
                recent_count=recent_count,
                last_seen=last_seen,
                pinned=bool(entry.get("pinned", False)),
                sort_key=build_model_sort_key(canonical, registry),
            )
        )
    recent_rows.sort(key=lambda row: (-(1 if row.pinned else 0), -row.recent_count, -_last_seen_sort_value(row.last_seen), row.sort_key[0], row.sort_key[1], row.suggested_input))
    return recent_rows[:fallback_limit]


def format_candidate_summary(rows: List[CandidateRow]) -> str:
    if not rows:
        return "当前没有可推荐的活跃候选，请直接让用户输入模型名。"
    labels = [row.suggested_input for row in rows]
    parts = [
        f"动态候选（按最近使用生成）: {', '.join(labels)}",
        "",
        "| 建议输入 | canonical | 30天出现 | 90天出现 | 最近一次 |",
        "|---|---|---:|---:|---|",
    ]
    for row in rows:
        parts.append(
            f"| {row.suggested_input} | {row.canonical_name} | {row.active_count} | {row.recent_count} | {row.last_seen or '—'} |"
        )
    return "\n".join(parts)


def command_suggest(args: argparse.Namespace) -> int:
    registry = load_registry()
    changed = sync_registry_with_reports(registry)
    reference_date = parse_iso_date(args.date) or date.today()
    rows = build_candidate_rows(registry, reference_date=reference_date)
    if changed:
        save_registry(registry)
    print(format_candidate_summary(rows))
    return 0


def command_observe(args: argparse.Namespace) -> int:
    registry = load_registry()
    changed = sync_registry_with_reports(registry)
    observed_date = args.date or date.today().isoformat()
    if not DATE_RE.match(observed_date):
        raise SystemExit(f"Invalid date: {observed_date}")
    canonical, observation_changed = register_observation(args.model, observed_date, registry)
    changed = changed or observation_changed
    if changed:
        save_registry(registry)
    print(f"已记录模型名：raw={args.model} -> canonical={canonical} @ {observed_date}")
    rows = build_candidate_rows(registry, reference_date=parse_iso_date(observed_date) or date.today())
    print("")
    print(format_candidate_summary(rows))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="动态维护模型注册表与候选列表")
    subparsers = parser.add_subparsers(dest="command", required=True)

    suggest = subparsers.add_parser("suggest", help="根据近期使用情况输出动态候选列表")
    suggest.add_argument("--date", help="参考日期，格式 YYYY-MM-DD")
    suggest.set_defaults(func=command_suggest)

    observe = subparsers.add_parser("observe", help="记录一次模型使用并更新注册表")
    observe.add_argument("--model", required=True, help="原始模型名")
    observe.add_argument("--date", help="观测日期，格式 YYYY-MM-DD")
    observe.set_defaults(func=command_observe)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
