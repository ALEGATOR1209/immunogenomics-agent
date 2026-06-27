import pandas as pd
from pathlib import Path

PYTCR_COLUMNS = ["sample", "freq", "#count", "cdr3aa", "cdr3nt", "v", "d", "j"]

# Common column names from various repertoire sequencing platforms
COLUMN_ALIASES: dict[str, list[str]] = {
    "sample":  ["sample_name", "sample_id", "specimen", "patient"],
    "freq":    ["frequency", "proportion", "fraction", "pct", "percent"],
    "#count":  ["templates", "count", "reads", "num_reads", "cloneCount", "duplicate_count"],
    "cdr3aa":  ["amino_acid", "cdr3", "aa_seq", "junction_aa", "cdr3_aa", "aaSeqCDR3"],
    "cdr3nt":  ["rearrangement", "nt_seq", "junction", "nucleotide", "cdr3_nt", "nSeqCDR3"],
    "v":       ["v_resolved", "v_gene", "v_call", "bestVGene", "vGeneName"],
    "d":       ["d_resolved", "d_gene", "d_call", "bestDGene", "dGeneName"],
    "j":       ["j_resolved", "j_gene", "j_call", "bestJGene", "jGeneName"],
}


def _detect_separator(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".tsv":
        return "\t"
    if suffix == ".csv":
        return ","
    # Sniff the first line
    with open(path) as f:
        first = f.readline()
    return "\t" if first.count("\t") > first.count(",") else ","


def _build_column_map(columns: list[str]) -> tuple[dict[str, str], list[str]]:
    """Return (rename_map, unmapped_pytcr_columns)."""
    cols_lower = {c.lower(): c for c in columns}
    rename: dict[str, str] = {}
    missing: list[str] = []

    for target, aliases in COLUMN_ALIASES.items():
        if target in columns:
            continue  # already correctly named
        matched = next(
            (cols_lower[a.lower()] for a in aliases if a.lower() in cols_lower),
            None,
        )
        if matched:
            rename[matched] = target
        else:
            missing.append(target)

    return rename, missing


def load_pytcr_file(path: Path, sample_name: str | None = None) -> tuple[pd.DataFrame, str]:
    """
    Load a repertoire file and remap columns to pyTCR standard.
    If the file has no sample column and sample_name is provided, it is injected.
    Returns (dataframe, summary_text).
    """
    sep = _detect_separator(path)
    df = pd.read_csv(path, sep=sep, low_memory=False)

    rename_map, unmapped = _build_column_map(df.columns.tolist())
    df = df.rename(columns=rename_map)

    if "sample" not in df.columns and sample_name:
        df.insert(0, "sample", sample_name)
        unmapped = [c for c in unmapped if c != "sample"]

    summary = _build_summary(df, path.name, rename_map, unmapped)
    return df, summary


def combine_files(paths: list[Path]) -> tuple[pd.DataFrame, str]:
    """Load and concatenate multiple repertoire files into one dataset."""
    frames: list[pd.DataFrame] = []
    per_file: list[str] = []

    for path in paths:
        df, summary = load_pytcr_file(path, sample_name=path.stem)
        frames.append(df)
        per_file.append(summary)

    combined = pd.concat(frames, ignore_index=True)

    lines = [
        f"**{len(paths)} files** combined into one dataset.\n",
        f"- Total clonotypes: {len(combined):,}",
    ]
    if "sample" in combined.columns:
        samples = combined["sample"].nunique()
        lines.append(f"- Unique samples: {samples}")
    if "#count" in combined.columns:
        lines.append(f"- Total reads: {int(combined['#count'].sum()):,}")
    if "cdr3aa" in combined.columns:
        lengths = combined["cdr3aa"].dropna().str.len()
        lines.append(f"- CDR3aa length: {int(lengths.min())}–{int(lengths.max())} aa")

    lines.append("\n---\n")
    lines.extend(per_file)

    return combined, "\n".join(lines)


def _build_summary(
    df: pd.DataFrame,
    filename: str,
    rename_map: dict[str, str],
    unmapped: list[str],
) -> str:
    lines = [f"**{filename}** loaded successfully.\n"]

    lines.append(f"- Clonotypes: {len(df):,}")

    if "sample" in df.columns:
        samples = df["sample"].nunique()
        sample_list = df["sample"].unique()
        if samples <= 5:
            lines.append(f"- Samples ({samples}): {', '.join(str(s) for s in sample_list)}")
        else:
            lines.append(f"- Samples: {samples} unique")

    if "#count" in df.columns:
        total = df["#count"].sum()
        lines.append(f"- Total reads: {total:,}")

    if "cdr3aa" in df.columns:
        lengths = df["cdr3aa"].dropna().str.len()
        lines.append(f"- CDR3aa length: {int(lengths.min())}–{int(lengths.max())} aa (median {int(lengths.median())})")

    if rename_map:
        mappings = ", ".join(f"{old}→{new}" for old, new in rename_map.items())
        lines.append(f"\n_Column remapping applied: {mappings}_")

    if unmapped:
        lines.append(
            f"\n**Warning:** Could not auto-map these pyTCR columns: `{'`, `'.join(unmapped)}`. "
            "Tell me which columns in your file correspond to them."
        )
        available = [c for c in df.columns if c not in PYTCR_COLUMNS]
        if available:
            lines.append(f"Available columns: `{'`, `'.join(available)}`")

    return "\n".join(lines)
