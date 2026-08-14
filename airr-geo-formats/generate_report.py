#!/usr/bin/env python3
"""Generate report.md from outline.yaml + fields.yaml + results/*.json."""

import json
import re
from pathlib import Path

import yaml

TOPIC_DIR = Path(__file__).resolve().parent

# Bidirectional category name mapping: fields.yaml category name -> possible JSON keys.
# This project's fields.yaml categories already match the JSON top-level keys
# (identification, data_location, format_specifics, sample_context, loadability,
# provenance), but the mapping is kept generic per the report format's conventions.
CATEGORY_MAPPING = {
    "identification": ["identification"],
    "data_location": ["data_location"],
    "format_specifics": ["format_specifics"],
    "sample_context": ["sample_context"],
    "loadability": ["loadability"],
    "provenance": ["provenance"],
}

# Fields shown in the table of contents, alongside item name.
TOC_FIELDS = [
    ("Status", ["status"]),
    ("Loadability", ["loadability", "loadability_confidence"]),
    ("GEO", ["data_location", "geo_accession"]),
    ("Year", ["identification", "year"]),
    ("Species", ["sample_context", "species"]),
    ("Format", ["format"]),
]

INTERNAL_KEYS = {"_source_file", "uncertain", "id", "label"}


def load_outline():
    outline_path = TOPIC_DIR / "outline.yaml"
    with open(outline_path) as f:
        return yaml.safe_load(f)


def load_fields():
    fields_path = TOPIC_DIR / "fields.yaml"
    with open(fields_path) as f:
        return yaml.safe_load(f)


def load_results(output_dir: Path):
    items = []
    for jf in sorted(output_dir.glob("*.json")):
        with open(jf) as f:
            data = json.load(f)
        data["_source_file"] = jf.name
        items.append(data)
    return items


def get_nested(data: dict, path):
    """Look up path (list of keys) directly, then via CATEGORY_MAPPING, then anywhere nested."""
    cur = data
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            cur = None
            break
    if cur is not None:
        return cur

    if len(path) == 2:
        category, field = path
        for candidate_key in CATEGORY_MAPPING.get(category, [category]):
            sub = data.get(candidate_key)
            if isinstance(sub, dict) and field in sub:
                return sub[field]

    for v in data.values():
        if isinstance(v, dict):
            found = get_nested(v, path[-1:]) if len(path) == 1 else None
            if found is not None:
                return found
    return None


def slugify_anchor(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text


def is_uncertain(field_name: str, value, uncertain_list) -> bool:
    if value is None or value == "":
        return True
    if field_name in (uncertain_list or []):
        return True
    if isinstance(value, str) and "[uncertain]" in value:
        return True
    return False


def shorten_geo(value: str) -> str:
    if not value:
        return "n/a"
    m = re.search(r"GSE\d+", value)
    return m.group(0) if m else value.split(",")[0].split("(")[0].strip()[:20]


def format_value(value) -> str:
    if isinstance(value, list):
        if not value:
            return ""
        if all(isinstance(v, dict) for v in value):
            return "<br>".join(
                " | ".join(f"{k}: {v}" for k, v in d.items()) for d in value
            )
        joined = ", ".join(str(v) for v in value)
        if len(joined) <= 100:
            return joined
        return "<br>".join(f"- {v}" for v in value)
    if isinstance(value, dict):
        return "; ".join(f"**{k}**: {v}" for k, v in value.items())
    text = str(value)
    if len(text) > 100:
        return f"> {text}"
    return text


def build_toc_line(index: int, item: dict) -> str:
    label = item.get("label") or item.get("id") or item.get("_source_file")
    anchor = slugify_anchor(label)
    parts = [f"{index}. [{label}](#{anchor})"]
    metrics = []
    for display_name, path in TOC_FIELDS:
        value = get_nested(item, path)
        if value is None or value == "":
            continue
        if display_name == "GEO":
            value = shorten_geo(str(value))
        else:
            value = str(value)
            if len(value) > 40:
                value = value[:37] + "..."
        metrics.append(f"{display_name}: {value}")
    if metrics:
        parts.append(" | ".join(metrics))
    return " - ".join(parts)


def build_detail_section(item: dict, fields_doc: dict) -> str:
    label = item.get("label") or item.get("id") or item.get("_source_file")
    anchor = slugify_anchor(label)
    lines = [f"## {label}", f'<a id="{anchor}"></a>', ""]

    uncertain_list = item.get("uncertain", [])
    covered_top_keys = set()

    for category in fields_doc.get("categories", []):
        cat_name = category["name"]
        covered_top_keys.add(cat_name)
        cat_data = None
        for candidate_key in CATEGORY_MAPPING.get(cat_name, [cat_name]):
            if candidate_key in item and isinstance(item[candidate_key], dict):
                cat_data = item[candidate_key]
                break
        if cat_data is None:
            continue

        rows = []
        for field in category.get("fields", []):
            fname = field["name"]
            value = cat_data.get(fname)
            if is_uncertain(fname, value, uncertain_list):
                continue
            rows.append((fname, format_value(value)))

        if not rows:
            continue

        lines.append(f"### {cat_name.replace('_', ' ').title()}")
        lines.append("")
        for fname, fvalue in rows:
            label_text = fname.replace("_", " ").title()
            if "\n" in fvalue or fvalue.startswith(">") or "<br>" in fvalue:
                if lines and lines[-1] != "":
                    lines.append("")
                lines.append(f"**{label_text}**:")
                lines.append("")
                lines.append(fvalue)
                lines.append("")
            else:
                lines.append(f"- **{label_text}**: {fvalue}")
        lines.append("")

    # Extra fields present in JSON but not defined in fields.yaml
    known_categories = {c["name"] for c in fields_doc.get("categories", [])}
    all_mapped_keys = set()
    for cat_name in known_categories:
        all_mapped_keys.update(CATEGORY_MAPPING.get(cat_name, [cat_name]))

    extra = {}
    for k, v in item.items():
        if k in INTERNAL_KEYS or k in all_mapped_keys or k == "format" or k == "status":
            continue
        extra[k] = v

    if extra:
        lines.append("### Other Info")
        lines.append("")
        for k, v in extra.items():
            lines.append(f"- **{k.replace('_', ' ').title()}**: {format_value(v)}")
        lines.append("")

    if uncertain_list:
        lines.append("### Uncertain Fields")
        lines.append("")
        for u in uncertain_list:
            lines.append(f"- {u}")
        lines.append("")

    return "\n".join(lines)


def main():
    outline = load_outline()
    fields_doc = load_fields()

    output_dir = TOPIC_DIR / outline["execution"].get("output_dir", "./results")
    output_dir = output_dir.resolve()

    items = load_results(output_dir)

    topic = outline.get("topic", "Research Report").strip()
    title = topic.split(".")[0].strip()
    if len(title) > 100:
        title = title[:97].rsplit(" ", 1)[0] + "..."

    toc_lines = [build_toc_line(i + 1, item) for i, item in enumerate(items)]
    detail_sections = [build_detail_section(item, fields_doc) for item in items]

    excluded = outline.get("excluded_from_scope", [])
    excluded_lines = []
    if excluded:
        excluded_lines.append("## Excluded From Scope")
        excluded_lines.append("")
        for ex in excluded:
            excluded_lines.append(f"- **{ex.get('format', ex)}**: {ex.get('reason', '').strip()}")
        excluded_lines.append("")

    report = []
    report.append(f"# {title}")
    report.append("")
    report.append(topic)
    report.append("")
    report.append("## Table of Contents")
    report.append("")
    report.extend(toc_lines)
    report.append("")
    if excluded_lines:
        report.extend(excluded_lines)
    report.append("---")
    report.append("")
    report.extend(detail_sections)

    report_path = TOPIC_DIR / "report.md"
    report_path.write_text("\n".join(report))
    print(f"Wrote {report_path} ({len(items)} items)")


if __name__ == "__main__":
    main()
