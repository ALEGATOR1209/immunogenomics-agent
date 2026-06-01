import uuid
import shutil
from pathlib import Path

from smolagents import tool

from .data_loading import load_pytcr_file, PYTCR_COLUMNS


def create_session(upload_root: Path) -> dict:
    session_id = uuid.uuid4().hex
    workdir = upload_root / session_id
    workdir.mkdir(parents=True, exist_ok=True)
    return {"id": session_id, "workdir": workdir, "df": None, "filename": None}


def make_tools(session: dict) -> list:
    """Return a list of smolagents tools that close over this session's state."""

    @tool
    def load_data(filename: str) -> str:
        """
        Load a repertoire file that the user has already uploaded.
        Remaps columns to pyTCR standard format and returns a dataset summary.

        Args:
            filename: Name of the uploaded file (e.g. 'sample.tsv').
        """
        path = session["workdir"] / filename
        if not path.exists():
            available = [f.name for f in session["workdir"].iterdir()]
            return (
                f"File '{filename}' not found in your upload folder. "
                f"Available files: {available or 'none uploaded yet'}."
            )
        df, summary = load_pytcr_file(path)
        session["df"] = df
        session["filename"] = filename
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

    return [load_data, describe_data, remap_columns]
