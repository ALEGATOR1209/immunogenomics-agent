import uuid
import shutil
from pathlib import Path

from smolagents import tool

from .data_loading import load_pytcr_file, combine_files, PYTCR_COLUMNS


def create_session(upload_root: Path) -> dict:
    session_id = uuid.uuid4().hex
    workdir = upload_root / session_id
    workdir.mkdir(parents=True, exist_ok=True)
    return {"id": session_id, "workdir": workdir, "df": None, "filename": None}


def make_tools(session: dict) -> list:
    """Return a list of smolagents tools that close over this session's state."""

    @tool
    def load_data(filenames: str) -> str:
        """
        Load one or more uploaded repertoire files and combine them into one dataset.
        Remaps columns to pyTCR standard format and returns a summary.

        Args:
            filenames: Comma-separated file names, e.g. 'sample1.tsv' or 'a.tsv, b.tsv'.
        """
        names = [n.strip() for n in filenames.split(",") if n.strip()]
        paths: list[Path] = []
        missing: list[str] = []
        for name in names:
            p = session["workdir"] / name
            if p.exists():
                paths.append(p)
            else:
                missing.append(name)

        if missing:
            available = [f.name for f in session["workdir"].iterdir()]
            return (
                f"Files not found: {missing}. "
                f"Available: {available or 'none uploaded yet'}."
            )

        df, summary = combine_files(paths) if len(paths) > 1 else load_pytcr_file(paths[0], sample_name=paths[0].stem)
        session["df"] = df
        session["filenames"] = [p.name for p in paths]
        return summary

    @tool
    def describe_data() -> str:
        """
        Return a summary of the currently loaded dataset including shape,
        columns present, and the first few rows.
        """
        df = session["df"]
        if df is None:
            return "No data loaded yet. Please upload a file first."

        present = [c for c in PYTCR_COLUMNS if c in df.columns]
        extra = [c for c in df.columns if c not in PYTCR_COLUMNS]
        lines = [
            f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns",
            f"pyTCR columns present: {present}",
        ]
        if extra:
            lines.append(f"Extra columns: {extra}")
        lines.append("\nFirst 3 rows:")
        lines.append(df.head(3).to_string(index=False))
        return "\n".join(lines)

    @tool
    def remap_columns(mapping: str) -> str:
        """
        Manually remap columns that could not be auto-detected.
        Use this when load_data reports unmapped pyTCR columns.

        Args:
            mapping: Comma-separated pairs in the form 'original:target'.
                     Example: 'aa_sequence:cdr3aa, read_count:#count'
        """
        df = session["df"]
        if df is None:
            return "No data loaded. Upload and load a file first."

        rename: dict[str, str] = {}
        errors: list[str] = []
        for pair in mapping.split(","):
            parts = pair.strip().split(":")
            if len(parts) != 2:
                errors.append(f"Invalid pair '{pair.strip()}' — expected 'original:target'")
                continue
            original, target = parts[0].strip(), parts[1].strip()
            if original not in df.columns:
                errors.append(f"Column '{original}' not found in data")
            else:
                rename[original] = target

        if errors:
            return "Errors:\n" + "\n".join(errors)

        session["df"] = df.rename(columns=rename)
        applied = ", ".join(f"{k}→{v}" for k, v in rename.items())
        return f"Remapped: {applied}"

    @tool
    def show_data(n: int = 10, sort_by: str = "", ascending: bool = True) -> str:
        """
        Display rows from the loaded dataset as a table.
        Use this for requests like 'show head', 'show first N rows',
        'sort by frequency and show top 10', etc.

        Args:
            n: Number of rows to show (default 10).
            sort_by: Column name to sort by before slicing. Empty string means no sorting.
            ascending: Sort direction (True = ascending, False = descending).
        """
        df = session["df"]
        if df is None:
            return "No data loaded yet. Please upload a file first."

        if sort_by:
            if sort_by not in df.columns:
                return f"Column '{sort_by}' not found. Available columns: {df.columns.tolist()}"
            df = df.sort_values(sort_by, ascending=ascending)

        subset = df.head(n)
        session["last_view"] = subset
        return subset.to_markdown(index=False)

    @tool
    def plot_clonotypes_per_sample() -> str:
        """
        Plot the number of clonotypes (rows) per sample as a bar chart.
        Use this for requests like 'plot clonotypes per sample',
        'how many clonotypes does each sample have', 'show sample sizes', etc.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        df = session["df"]
        if df is None:
            return "No data loaded yet. Please upload a file first."
        if "sample" not in df.columns:
            return "No 'sample' column found in the loaded data."

        counts = df.groupby("sample").size().sort_values(ascending=False)

        fig, ax = plt.subplots(figsize=(max(6, len(counts) * 0.6), 5))
        bars = ax.bar(counts.index, counts.values, color="#4C72B0", edgecolor="white")
        ax.bar_label(bars, fmt="%d", padding=3, fontsize=9)
        ax.set_xlabel("Sample")
        ax.set_ylabel("Clonotypes")
        ax.set_title("Clonotypes per sample")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        plot_dir = session["workdir"] / "plots"
        plot_dir.mkdir(exist_ok=True)
        out = plot_dir / "clonotypes_per_sample.png"
        fig.savefig(out, dpi=150)
        plt.close(fig)

        session["last_plot"] = str(out)
        return f"Plot saved. Samples: {len(counts)}, range {int(counts.min()):,}–{int(counts.max()):,} clonotypes."

    @tool
    def plot_cdr3aa_length_distribution() -> str:
        """
        Plot the distribution of CDR3 amino acid sequence lengths vs clonotype counts.
        Use this for requests like 'plot CDR3 length distribution',
        'show cdr3aa vs counts', 'CDR3 length histogram', etc.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        df = session["df"]
        if df is None:
            return "No data loaded yet. Please upload a file first."
        if "cdr3aa" not in df.columns:
            return "No 'cdr3aa' column found in the loaded data."

        lengths = df["cdr3aa"].dropna().str.len()
        counts = lengths.value_counts().sort_index()

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(counts.index, counts.values, color="#DD8452", edgecolor="white")
        ax.set_xlabel("CDR3aa length (aa)")
        ax.set_ylabel("Clonotype count")
        ax.set_title("CDR3aa length distribution")
        ax.set_xticks(counts.index)
        plt.tight_layout()

        plot_dir = session["workdir"] / "plots"
        plot_dir.mkdir(exist_ok=True)
        out = plot_dir / "cdr3aa_length_distribution.png"
        fig.savefig(out, dpi=150)
        plt.close(fig)

        session["last_plot"] = str(out)
        return (
            f"Plot saved. Length range: {int(counts.index.min())}–{int(counts.index.max())} aa, "
            f"mode: {int(counts.idxmax())} aa ({int(counts.max()):,} clonotypes)."
        )

    @tool
    def plot_cdr3aa_counts(top_n: int = 20) -> str:
        """
        Plot top CDR3 amino acid sequences (x-axis) against their read counts (y-axis).
        Use this for requests like 'plot CDR3aa counts', 'top clonotypes by count',
        'most abundant CDR3 sequences', 'cdr3aa vs #count'.

        Args:
            top_n: How many top clonotypes to show (default 20).
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        df = session["df"]
        if df is None:
            return "No data loaded yet. Please upload a file first."
        if "cdr3aa" not in df.columns:
            return "No 'cdr3aa' column found in the loaded data."
        if "#count" not in df.columns:
            return "No '#count' column found in the loaded data."

        top = (
            df.groupby("cdr3aa")["#count"]
            .sum()
            .sort_values(ascending=False)
            .head(top_n)
        )

        fig, ax = plt.subplots(figsize=(max(10, top_n * 0.6), 5))
        ax.bar(range(len(top)), top.values, color="#55A868", edgecolor="white")
        ax.set_xticks(range(len(top)))
        ax.set_xticklabels(top.index, rotation=45, ha="right", fontsize=8)
        ax.set_xlabel("CDR3aa sequence")
        ax.set_ylabel("Read count (#count)")
        ax.set_title(f"Top {len(top)} CDR3aa sequences by read count")
        plt.tight_layout()

        plot_dir = session["workdir"] / "plots"
        plot_dir.mkdir(exist_ok=True)
        out = plot_dir / "cdr3aa_counts.png"
        fig.savefig(out, dpi=150)
        plt.close(fig)

        session["last_plot"] = str(out)
        return (
            f"Plot saved. Top sequence: {top.index[0]} ({int(top.iloc[0]):,} reads), "
            f"showing {len(top)} of {df['cdr3aa'].nunique():,} unique CDR3aa sequences."
        )

    return [load_data, describe_data, remap_columns, show_data,
            plot_clonotypes_per_sample, plot_cdr3aa_length_distribution, plot_cdr3aa_counts]
