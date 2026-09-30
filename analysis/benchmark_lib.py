"""Shared loading/plotting/stats helpers for the per-model benchmark notebooks in this directory.

Each notebook (muse-glimmer-30B.ipynb, claude-opus-5.ipynb, ...) keeps its own HARDWARE label,
MODEL_NAME/MODEL_LABEL, and any genuinely model-specific plots (e.g. claude-opus-5's cost-per-run
chart, priced off Anthropic's API rates). Everything else that was identical between them lives
here.
"""

import fnmatch
import gzip
import io
import json
import re
import tarfile
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.patches import Patch, Rectangle
from matplotlib.path import Path as MplPath
from matplotlib.ticker import MaxNLocator
from scipy.stats import false_discovery_control, mannwhitneyu, wilcoxon

BASE_DIR = Path.cwd()
TEST_DIR = BASE_DIR.parent / "test"
DATA_DIR = BASE_DIR.parent / "data"
RUNS_PER_BATCH = 5

SURFACE = "#fcfcfb"
SERIES = {False: ("#eb6834", "No skills"), True: ("#2a78d6", "Skills")}

TOKEN_FIELDS = {  # column name -> key in run.jsonl's usage object
  "input_tokens": "input",
  "output_tokens": "output",
  "cache_read_tokens": "cacheRead",
  "cache_write_tokens": "cacheWrite",
  "total_tokens": "totalTokens",
}


def count_tokens(run_dir: Path) -> dict[str, int | None]:
  events_file = run_dir / "run.jsonl"
  if events_file.exists():
    lines = events_file.open(encoding="utf-8", errors="replace")
  elif events_file.with_suffix(".jsonl.gz").exists():  # older run dirs get gzipped to save disk
    lines = gzip.open(events_file.with_suffix(".jsonl.gz"), "rt", encoding="utf-8", errors="replace")
  else:
    return {column: None for column in TOKEN_FIELDS}

  totals = {column: 0 for column in TOKEN_FIELDS}
  for line in lines:
    line = line.strip()
    if not line.startswith("{"):  # the container logs boot noise before the event stream
      continue
    try:
      event = json.loads(line)
    except json.JSONDecodeError:  # a killed container can leave a half-written line
      continue
    if event.get("type") == "message_end":  # usage is per API call, so sum over the run
      usage = event.get("message", {}).get("usage") or {}
      for column, key in TOKEN_FIELDS.items():
        totals[column] += usage.get(key) or 0
  return totals


def add_token_counts(runs: pd.DataFrame, test_dir: Path = TEST_DIR) -> pd.DataFrame:
  # run.jsonl is the big file in a run dir, so only read it for the runs we keep
  counts = [count_tokens(test_dir / row.task / "runs" / row.run) for row in runs.itertuples()]
  return runs.join(pd.DataFrame(counts, index=runs.index))


def load_runs(
  test_dir: Path = TEST_DIR, model: str | None = None, hardware: str | None = None
) -> pd.DataFrame:
  # test/*/runs mixes every model ever benchmarked in the same tree, so callers that want one
  # model's numbers must filter explicitly rather than assume the tree is already scoped to it.
  rows = []
  for runs_dir in sorted(test_dir.glob("*/runs")):
    task_json = runs_dir.parent / "task.json"
    metadata = json.loads(task_json.read_text()).get("metadata", {}) if task_json.exists() else {}
    for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
      result_file = run_dir / "eval_result.json"
      if not result_file.exists():
        print(f"Skipping {run_dir} because {result_file} does not exist")
        continue
      r = json.loads(result_file.read_text())
      if model is not None and r.get("model") != model:
        continue
      rows.append(
        {
          "task": runs_dir.parent.name,
          "eval_type": metadata.get("eval_type"),
          "kit": metadata.get("kit"),
          "task_type": metadata.get("task"),
          "run": run_dir.name,
          "start_time": pd.to_datetime(r.get("start_time")),
          "skills": r["skills"],
          "score": r["score"],
          "points": r["points"],
          "total": r["total"],
          "passed": r["passed"],
          "structure_match": r.get("structure_match"),
          "duration_seconds": r["duration_seconds"],
          "timed_out": r.get("timed_out", False),
          "interrupted": r.get("interrupted", False),
          "model": r.get("model"),
          "harness": r.get("harness"),
          "model_server": r.get("model_server"),
          "hardware": hardware,
        }
      )
  return pd.DataFrame(rows)


def latest_batches(runs: pd.DataFrame, n: int = RUNS_PER_BATCH) -> pd.DataFrame:
  # start_time is absent on pre-2026-08-11 runs; those are the oldest, so NaT sorts first
  ordered = runs.sort_values(["task", "skills", "start_time"], na_position="first")
  return ordered.groupby(["task", "skills"], as_index=False).tail(n).reset_index(drop=True)


# test.py passes each hosted provider's API key into the container (only that provider's — see
# HOSTED_PROVIDER_KEYS in test.py), and pi echoes the environment into run.jsonl/run.txt, so a
# hosted-provider run's copy has to be scrubbed before anything is committed. Local llama.cpp runs
# never see a credential, so they pass redact=() and skip this entirely.
SECRET_PATTERNS: dict[str, tuple[re.Pattern[bytes], bytes]] = {
  "anthropic": (re.compile(rb"sk-ant-[A-Za-z0-9_-]{20,}"), b"sk-ant-***REDACTED***"),
  "openai": (re.compile(rb"sk-(?!ant-)[A-Za-z0-9_-]{20,}"), b"sk-***REDACTED***"),
  "gemini": (re.compile(rb"AIza[0-9A-Za-z_-]{35}"), b"AIza***REDACTED***"),
}


def _run_files(src: Path, exclude: tuple[str, ...]):
  for path in sorted(src.rglob("*")):
    if not path.is_file():
      continue
    parts = path.relative_to(src).parts
    if any(fnmatch.fnmatch(part, pattern) for part in parts for pattern in exclude):
      continue
    yield path


def save_runs(
  runs: pd.DataFrame,
  dir: Path,
  test_dir: Path = TEST_DIR,
  exclude: tuple[str, ...] = (),
  redact: tuple[str, ...] = (),
  force: bool = False,
) -> None:
  # .tar.xz: liblzma-based compression (~3x smaller than a deflate zip on this data, since
  # run.jsonl resends the full growing conversation history each turn) that still extracts
  # natively via macOS's built-in tar/Archive Utility, unlike a zip with LZMA/bzip2 entries.
  dir.mkdir(parents=True, exist_ok=True)
  runs.to_csv(dir / "benchmark.csv", index=False)

  patterns = [SECRET_PATTERNS[provider] for provider in redact]

  archive_path = dir / "runs.tar.xz"
  old_tf = tarfile.open(archive_path, "r:xz") if archive_path.exists() else None
  members_by_run = {}
  if old_tf is not None:
    for member in old_tf.getmembers():
      if not member.isfile():
        continue
      parts = member.name.split("/")
      if len(parts) > 2:  # "runs/<task>/<run>/..."
        members_by_run.setdefault((parts[1], parts[2]), []).append(member)

  to_write = [row for row in runs.itertuples() if force or (row.task, row.run) not in members_by_run]
  write_keys = {(row.task, row.run) for row in to_write}

  masked = 0
  tmp_path = archive_path.with_suffix(".tmp")
  with tarfile.open(tmp_path, "w:xz") as new_tf:
    for key, members in members_by_run.items():  # carry over untouched runs without recompressing twice
      if key in write_keys:
        continue
      for member in members:
        new_tf.addfile(member, old_tf.extractfile(member))  # already redacted by a prior save_runs
    for row in to_write:
      src = test_dir / row.task / "runs" / row.run
      for file in _run_files(src, exclude):
        arcname = str(Path("runs") / row.task / row.run / file.relative_to(src))
        if patterns:  # only pay for reading+scanning bytes when there's something to redact
          data = file.read_bytes()
          for pattern, replacement in patterns:
            data, hits = pattern.subn(replacement, data)
            masked += hits
          info = new_tf.gettarinfo(file, arcname=arcname)
          info.size = len(data)
          new_tf.addfile(info, io.BytesIO(data))
        else:
          new_tf.add(file, arcname=arcname)

  if old_tf is not None:
    old_tf.close()
  tmp_path.replace(archive_path)

  print(f"{dir / 'benchmark.csv'}: {len(runs)} rows")
  print(f"{archive_path}: added {len(to_write)}, already present {len(runs) - len(to_write)}")
  if patterns:
    print(f"masked {masked} credential(s) in the archived logs")


MIN_BOX_FRACTION = 0.05  # of the y-range, so a zero-spread batch reads as a box in any unit
COLUMN_LABELS = {
  "score": "Score",
  "total_tokens": "Total tokens (M)",
  "duration_seconds": "Duration (s)",
}
COLUMN_SCALES = {"total_tokens": 1e6}  # plotted in the label's units, not raw counts
COLUMN_TICK_FORMATS = {"total_tokens": lambda v, _: f"{v:,.2f}"}
TASK_TYPE_ORDER = (
  "data-loading",
  "clonotype-analysis",
  "clonotype-networks",
  "gene-usage",
  "repertoire-similarity",
  "clonotype-clustering",
  "epitope-databases",
  "complex-biological-effect",
)
TASK_TYPE_ALIASES = {"clonotype-analyzis": "clonotype-analysis"}  # after 18-liver-clonotype-analyzis


def group_tick_labels(groups: list[str], aggregation: str) -> list[str]:
  if aggregation == "task_type":
    return [f"{i + 1}\n" + textwrap.fill(g.replace("-", " "), 12) for i, g in enumerate(groups)]
  return [f'{g.split("-")[0]}\n' + textwrap.fill(g.split("-", 1)[1], 12) for g in groups]


def ordered_groups(runs: pd.DataFrame, aggregation: str) -> tuple[pd.DataFrame, list[str]]:
  # the groups to report per, in display order: task types follow the pipeline order,
  # anything else (tasks, or a task type not in TASK_TYPE_ORDER) sorts by name
  if aggregation != "task_type":
    return runs, sorted(runs[aggregation].unique())
  runs = runs.assign(task_type=runs["task_type"].replace(TASK_TYPE_ALIASES))
  present = set(runs["task_type"])
  return runs, [t for t in TASK_TYPE_ORDER if t in present] + sorted(present - set(TASK_TYPE_ORDER))


POINT_SIZE = 22
POINT_STEP = 0.045  # x spacing (axis units) at which POINT_SIZE dots just touch
POINT_ROW_WIDTH = 0.28  # a row of tied runs never gets wider than the box (0.3)


def _swarm_layout(values: np.ndarray, y_range: float) -> tuple[np.ndarray, np.ndarray]:
  # runs whose values would overlap (e.g. many scores of exactly 1.0) are laid out side by side
  # at their exact value; a row too long to fit the box is packed tighter with smaller dots,
  # so every run stays visible without being moved off the value it scored
  bins = np.round(values / (y_range / 40)).astype(int)
  dx, sizes = np.zeros(len(values)), np.full(len(values), float(POINT_SIZE))
  for b in np.unique(bins):
    idx = np.flatnonzero(bins == b)
    if len(idx) == 1:
      continue
    step = min(POINT_STEP, POINT_ROW_WIDTH / (len(idx) - 1))
    dx[idx] = (np.arange(len(idx)) - (len(idx) - 1) / 2) * step
    sizes[idx] = POINT_SIZE * (step / POINT_STEP) ** 2  # scatter size is area
  return dx, sizes


def plot_benchmark(runs: pd.DataFrame, column: str, model_label: str, ax=None, points: bool = True, aggregation: str = "task"):
  runs = runs.assign(**{column: runs[column] / COLUMN_SCALES.get(column, 1.0)})
  runs, tasks = ordered_groups(runs, aggregation)
  pos = {task: i for i, task in enumerate(tasks)}
  if ax is None:
    _, ax = plt.subplots(figsize=(11, 5.5))

  values = runs[column].astype(float)
  low, high = min(0.0, values.min()), values.max()
  pad = 0.05 * (high - low or 1.0)
  ylim = (low - pad, high + pad)
  min_box = MIN_BOX_FRACTION * (ylim[1] - ylim[0])

  for skills, (color, _) in SERIES.items():
    offset = 0.19 if skills else -0.19
    batches = {task: batch for task, batch in runs[runs["skills"] == skills].groupby(aggregation)}
    present = [t for t in tasks if t in batches]
    bp = ax.boxplot(
      [batches[t][column].values for t in present],
      positions=[pos[t] + offset for t in present],
      widths=0.3, patch_artist=True, manage_ticks=False, zorder=2,
      whis=1.5, showfliers=not points,  # with points on, the runs past the whiskers are already drawn
      showmeans=True, meanline=True,
      boxprops=dict(facecolor=color + "38", edgecolor=color, linewidth=1.2),  # 38 = ~22% alpha
      medianprops=dict(linewidth=0),
      meanprops=dict(color=color, linewidth=2, linestyle="-"),
      whiskerprops=dict(color=color, linewidth=1.2),
      capprops=dict(color=color, linewidth=1.2),
    )

    for box in bp["boxes"]:  # redraw boxes that collapsed to a line (IQR of 0)
      verts = box.get_path().vertices
      lo, hi = verts[:, 1].min(), verts[:, 1].max()
      if hi - lo < min_box:
        x0, x1 = verts[:, 0].min(), verts[:, 0].max()
        mid = (lo + hi) / 2
        bottom, top = mid - min_box / 2, mid + min_box / 2
        box.set_path(
          MplPath([(x0, bottom), (x1, bottom), (x1, top), (x0, top), (x0, bottom)], closed=True)
        )

    if points:  # n = 5, so show the runs the box is drawn from
      for task, batch in batches.items():
        dx, sizes = _swarm_layout(batch[column].values, ylim[1] - ylim[0])
        ax.scatter(
          pos[task] + offset + dx, batch[column],
          s=sizes, color=color, edgecolor=SURFACE, linewidth=0.8 * np.sqrt(sizes / POINT_SIZE),
          alpha=0.75, zorder=3,
        )

  label = COLUMN_LABELS.get(column, column.replace("_", " ").capitalize())
  ax.set_xticks(range(len(tasks)))
  ax.set_xticklabels(group_tick_labels(tasks, aggregation), fontsize=9)
  ax.set_xlim(-0.6, len(tasks) - 0.4)
  ax.set_ylim(*ylim)
  if column == "score":
    ax.set_yticks(np.arange(0, 1.01, 0.25))
  else:
    ax.yaxis.set_major_formatter(COLUMN_TICK_FORMATS.get(column, lambda v, _: f"{v:,.0f}"))
  ax.set_ylabel(label)
  ax.set_title(  # only the first letter, so a unit like (M) keeps its case
    f"{model_label} — {label[0].lower() + label[1:]} per {aggregation.replace('_', ' ')}, with and without skills",
    loc="left", pad=18,
  )
  box_sizes = runs.groupby([aggregation, "skills"]).size()
  runs_per_box = (
    f"{box_sizes.iloc[0]}" if box_sizes.nunique() == 1 else f"{box_sizes.min()}-{box_sizes.max()}"
  )
  ax.text(
    0, 1.02,
    f"{runs_per_box} runs per box; box = IQR, whiskers = 1.5×IQR, bar = mean, dots = individual runs",
    transform=ax.transAxes, ha="left", va="bottom", fontsize=9, color="#52514e",
  )
  ax.grid(axis="y", color="#e5e4e0", linewidth=0.8)
  ax.set_axisbelow(True)
  for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
  ax.spines["bottom"].set_color("#c3c2b7")
  ax.tick_params(length=0)
  ax.legend(
    handles=[
      Patch(facecolor=color + "38", edgecolor=color, linewidth=1.2, label=series_label)
      for color, series_label in SERIES.values()
    ],
    frameon=False, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2,
  )
  return ax


VENDOR_COLORS = {  # fixed per vendor, so a model keeps its color whichever subset is plotted
  "alibaba": "#2a78d6",
  "anthropic": "#eb6834",
  "deepseek": "#1baf7a",
  "google": "#eda100",
  "meta": "#e87ba4",
  "minimax": "#008300",
  "nvidia": "#4a3aa7",
  "openai": "#e34948",
}
VARIANT_MARKERS = ("o", "D", "s", "^")  # tells apart several benchmarks from one vendor
HARDWARE_COLORS = {
  "cloud": "#2a78d6",
  "NVIDIA GeForce RTX 4070 SUPER": "#eb6834",
  "Apple M5 Max 128GB": "#1baf7a",
  "Apple M3 Max 36GB": "#eda100",
}
FALLBACK_COLOR = "#8a8984"


def drop_sparse_tasks(benchmarks: pd.DataFrame, min_runs: int = 3) -> pd.DataFrame:
  # a model's task is dropped when either arm (with / without skills) has fewer than min_runs
  # runs: both arms go, so the two means a model is compared on always cover the same tasks
  counts = benchmarks.groupby(["benchmark", "task", "skills"]).size().unstack("skills", fill_value=0)
  keep = counts[(counts >= min_runs).all(axis=1)].index
  return benchmarks.set_index(["benchmark", "task"]).loc[lambda d: d.index.isin(keep)].reset_index()


VARIANT_HATCHES = ("", "////", "....", "xxxx")  # the bar-chart counterpart of VARIANT_MARKERS


def _series_styles(runs: pd.DataFrame, by: str) -> pd.DataFrame:
  # label, color, marker and hatch per series, so a model looks the same in every chart:
  # by="benchmark" is colored by vendor, with a marker/hatch per benchmark within the vendor
  if by == "benchmark":
    series = runs[["vendor", "benchmark"]].drop_duplicates().sort_values(["vendor", "benchmark"])
    variant = series.groupby("vendor").cumcount()
    series["marker"] = [VARIANT_MARKERS[i] for i in variant]
    series["hatch"] = [VARIANT_HATCHES[i] for i in variant]
    series["color"] = series["vendor"].map(VENDOR_COLORS).fillna(FALLBACK_COLOR)
  else:
    order = list(HARDWARE_COLORS) if by == "hardware" else []
    present = runs[by].unique()
    series = pd.DataFrame({by: [s for s in order if s in present] + sorted(set(present) - set(order))})
    series["marker"] = "o"
    series["hatch"] = ""
    series["color"] = series[by].map(HARDWARE_COLORS if by == "hardware" else {}).fillna(FALLBACK_COLOR)
  series["label"] = series[by]
  return series.reset_index(drop=True)


def plot_models_by_task_type(benchmarks: pd.DataFrame, column: str, ax=None, by: str = "benchmark") -> pd.DataFrame:
  # one dumbbell per series and task type: hollow = mean without skills, filled = mean with
  # skills, so the line between them is the effect of skills. by="benchmark" is one series per
  # model, identified by vendor color plus a marker shape per benchmark within the vendor;
  # by="hardware" pools every model run on the same machine. Each series has a fixed slot
  # in each group.
  runs = benchmarks.assign(**{column: benchmarks[column] / COLUMN_SCALES.get(column, 1.0)})
  runs, task_types = ordered_groups(runs, "task_type")
  series = _series_styles(runs, by)
  means = runs.groupby([by, "task_type", "skills"])[column].mean().unstack("skills")
  if ax is None:
    _, ax = plt.subplots(figsize=(13, 5.5))

  step = 0.8 / len(series)
  for i, s in enumerate(series.itertuples()):
    color = s.color
    for j, task_type in enumerate(task_types):
      if (s.label, task_type) not in means.index:
        continue  # this series never ran a task of this type
      without, with_skills = means.loc[(s.label, task_type)].reindex([False, True])
      x = j - 0.4 + step * (i + 0.5)
      ax.plot([x, x], [without, with_skills], color=color, linewidth=1.2, alpha=0.6, zorder=2)
      ax.scatter(x, without, s=34, marker=s.marker, facecolor=SURFACE, edgecolor=color, linewidth=1.5, zorder=3)
      ax.scatter(x, with_skills, s=34, marker=s.marker, color=color, edgecolor=SURFACE, linewidth=0.8, zorder=3)

  label = COLUMN_LABELS.get(column, column.replace("_", " ").capitalize())
  ax.set_xticks(range(len(task_types)))
  ax.set_xticklabels(group_tick_labels(task_types, "task_type"), fontsize=9)
  ax.set_xlim(-0.5, len(task_types) - 0.5)
  for j in range(1, len(task_types)):  # separate the groups, since each can hold a dozen marks
    ax.axvline(j - 0.5, color="#e5e4e0", linewidth=0.8, zorder=1)
  if column == "score":
    ax.set_ylim(-0.03, 1.03)
    ax.set_yticks(np.arange(0, 1.01, 0.25))
  else:
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(COLUMN_TICK_FORMATS.get(column, lambda v, _: f"{v:,.0f}"))
  ax.set_ylabel(label)
  ax.set_title(f"Mean {label[0].lower() + label[1:]} per task type, by {by if by != 'benchmark' else 'model'}", loc="left", pad=18)
  ax.text(
    0, 1.02, "hollow = without skills, filled = with skills; line = effect of skills",
    transform=ax.transAxes, ha="left", va="bottom", fontsize=9, color="#52514e",
  )
  ax.grid(axis="y", color="#e5e4e0", linewidth=0.8)
  ax.set_axisbelow(True)
  for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
  ax.spines["bottom"].set_color("#c3c2b7")
  ax.tick_params(length=0)
  ax.legend(
    handles=[
      plt.Line2D(
        [], [], linestyle="", marker=s.marker, markersize=6, color=s.color, label=s.label,
      )
      for s in series.itertuples()
    ],
    frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=9,
  )
  return means.rename(columns={False: "no_skills", True: "skills"})


def plot_total_score(benchmarks: pd.DataFrame, by: str = "benchmark", column: str = "score", ax=None) -> pd.DataFrame:
  # the whole-benchmark number from plot_skill_summary (mean over every run, SEM error bars),
  # one pair of bars per model (by="benchmark") or machine (by="hardware"), best first. Each
  # pair takes its series color (+ hatch for a vendor's second model, as in
  # plot_models_by_task_type); on the skills bar a dashed box spans the change from the
  # no-skills mean, and the relative change is printed above the pair
  scaled = benchmarks[column] / COLUMN_SCALES.get(column, 1.0)
  stats = scaled.groupby([benchmarks[by], benchmarks["skills"]]).agg(["mean", "sem", "size"]).unstack("skills")
  stats = stats.sort_values(("mean", True), ascending=False)
  groups = list(stats.index)
  styles = _series_styles(benchmarks, by).set_index("label").loc[groups]
  top = (stats["mean"] + stats["sem"].fillna(0)).max().max()
  pad = 0.02 * (1.0 if column == "score" else top)
  if ax is None:
    _, ax = plt.subplots(figsize=(max(6, 1.1 * len(groups)), 5.5))

  value_format = VALUE_FORMATS.get(column, "{:,.0f}")
  width = 0.36
  for i, group in enumerate(groups):
    color, hatch = styles.loc[group, "color"], styles.loc[group, "hatch"]
    without, with_skills = (stats.loc[group, ("mean", s)] for s in (False, True))
    pair_top = 0.0
    for skills, mean in ((False, without), (True, with_skills)):
      x = i + (0.2 if skills else -0.2)
      error = np.nan_to_num(stats.loc[group, ("sem", skills)])
      ax.bar(x, mean, width=width, color=color + "70", edgecolor=color, linewidth=1.2, hatch=hatch, zorder=2)
      ax.errorbar(x, mean, yerr=error, color=color, linewidth=1.2, capsize=4, zorder=4)
      ax.text(x, mean + error + pad, value_format.format(mean), ha="center", va="bottom", fontsize=9, color=color)
      pair_top = max(pair_top, mean + error)
    ax.add_patch(Rectangle(  # the change skills made: from the no-skills mean to the skills mean
      (i + 0.2 - width / 2, min(without, with_skills)), width, abs(with_skills - without),
      fill=False, edgecolor=color, linewidth=2.5, linestyle=(0, (3, 2)), zorder=3,
    ))
    if without:
      ax.text(
        i, pair_top + 5 * pad, f"{(with_skills - without) / without:+.0%}",
        ha="center", va="bottom", fontsize=11, fontweight="bold", color=color,
      )

  label = COLUMN_LABELS.get(column, column.replace("_", " ").capitalize())
  group_label = by if by != "benchmark" else "model"
  ax.set_xticks(range(len(groups)))
  ax.set_xticklabels(  # slanted, so long model ids never run into each other at any figure width
    groups, fontsize=9, rotation=25, ha="right", rotation_mode="anchor",
  )
  ax.set_xlim(-0.6, len(groups) - 0.4)
  ax.set_ylabel(label)
  if column == "score":  # ticks stop at 1, the headroom above holds the change labels
    ax.set_ylim(0, 1.15)
    ax.set_yticks(np.arange(0, 1.01, 0.25))
  else:
    ax.set_ylim(0, top * 1.25)
    ax.yaxis.set_major_formatter(COLUMN_TICK_FORMATS.get(column, lambda v, _: f"{v:,.0f}"))
  ax.set_title(f"Mean {label[0].lower() + label[1:]} over all runs, per {group_label}", loc="left", pad=18)
  ax.text(
    0, 1.02, "error bars = standard error of the mean; % = relative change with skills",
    transform=ax.transAxes, ha="left", va="bottom", fontsize=9, color="#52514e",
  )
  key = "#8a8984"
  ax.legend(
    handles=[
      Patch(facecolor=key, edgecolor=key, label="No skills"),
      Patch(fill=False, edgecolor=key, linewidth=2.5, linestyle=(0, (3, 2)), label="Skills"),
    ],
    frameon=False, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2,
  )
  style_bar_axis(ax)
  return stats


SUMMARY_METRICS = ("score", "duration_seconds", "total_tokens")
VALUE_FORMATS = {"score": "{:.3f}", "duration_seconds": "{:,.0f}", "total_tokens": "{:.2f}"}


def plot_skill_summary(runs: pd.DataFrame, metrics=SUMMARY_METRICS, axs=None):
  if axs is None:
    _, axs = plt.subplots(nrows=len(metrics), ncols=1, figsize=(6, 3.4 * len(metrics)))
  axs = np.ravel(axs)
  order = [False, True]

  for ax, metric in zip(axs, metrics):
    scaled = runs[metric] / COLUMN_SCALES.get(metric, 1.0)  # same units as the per-task plots
    stats = scaled.groupby(runs["skills"]).agg(["mean", "sem", "size"])
    means = [stats.loc[skills, "mean"] for skills in order]
    errors = [stats.loc[skills, "sem"] for skills in order]

    for x, skills in enumerate(order):  # one call per bar: ecolor takes a single color
      color = SERIES[skills][0]
      ax.bar(
        x, stats.loc[skills, "mean"], yerr=stats.loc[skills, "sem"], width=0.55,
        color=color + "38", edgecolor=color, linewidth=1.5, ecolor=color, capsize=6, zorder=2,
      )

    value_format = VALUE_FORMATS.get(metric, "{:,.0f}")
    for x, (mean, error) in enumerate(zip(means, errors)):
      ax.text(
        x, mean + error + 0.02 * max(means), value_format.format(mean),
        ha="center", va="bottom", fontsize=10,
      )

    label = COLUMN_LABELS.get(metric, metric.replace("_", " ").capitalize())
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([f"{SERIES[s][1]}\n(n={stats.loc[s, 'size']:.0f})" for s in order])
    ax.set_xlim(-0.6, len(order) - 0.4)
    ax.set_ylim(0, max(m + e for m, e in zip(means, errors)) * 1.18)
    ax.set_ylabel(label)
    ax.set_title(f"Mean {label[0].lower() + label[1:]} over all runs", loc="left", pad=14)
    if metric != "score":
      ax.yaxis.set_major_formatter(COLUMN_TICK_FORMATS.get(metric, lambda v, _: f"{v:,.0f}"))
    ax.grid(axis="y", color="#e5e4e0", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
      ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.tick_params(length=0)

  axs[0].text(
    0, 1.02, "error bars = standard error of the mean", transform=axs[0].transAxes,
    ha="left", va="bottom", fontsize=9, color="#52514e",
  )
  return axs


def compare_skills(runs: pd.DataFrame, metrics=SUMMARY_METRICS, aggregation: str = "task") -> pd.DataFrame:
  runs, groups = ordered_groups(runs, aggregation)
  rows = []
  for metric in metrics:
    per_group = [(group, runs[runs[aggregation] == group]) for group in groups]
    for scope, data in [("all tasks (pooled)", runs)] + per_group:
      without = data.loc[~data["skills"], metric].astype(float)
      with_skills = data.loc[data["skills"], metric].astype(float)
      if np.ptp(np.concatenate([without, with_skills])) == 0:
        p = 1.0  # every run identical: U is undefined, and there is nothing to detect
      else:
        _, p = mannwhitneyu(with_skills, without, alternative="two-sided")
      rows.append(
        {
          "metric": metric, "scope": scope, "test": "Mann-Whitney U",
          "n": f"{len(without)} vs {len(with_skills)}",
          "mean_no_skills": without.mean(), "mean_skills": with_skills.mean(),
          "diff": with_skills.mean() - without.mean(), "p_value": p,
        }
      )

    # paired alternative: one mean per task, so task difficulty cancels out; kept per task even
    # when aggregating by task type, since finer pairs give the test more to work with
    task_means = runs.groupby(["task", "skills"])[metric].mean().unstack()
    _, p = wilcoxon(task_means[True], task_means[False])
    rows.append(
      {
        "metric": metric, "scope": "all tasks (paired by task)", "test": "Wilcoxon signed-rank",
        "n": f"{len(task_means)} tasks",
        "mean_no_skills": task_means[False].mean(), "mean_skills": task_means[True].mean(),
        "diff": (task_means[True] - task_means[False]).mean(), "p_value": p,
      }
    )

  results = pd.DataFrame(rows)
  results["p_fdr"] = np.nan
  per_task = ~results["scope"].str.startswith("all tasks")
  for metric in metrics:  # Benjamini-Hochberg within each metric's family of per-group tests
    family = per_task & (results["metric"] == metric)
    results.loc[family, "p_fdr"] = false_discovery_control(results.loc[family, "p_value"], method="bh")
  results["significant_fdr"] = results["p_fdr"] < 0.05
  return results


def metric_table(significance: pd.DataFrame, metric: str) -> pd.DataFrame:
  return significance[significance["metric"] == metric].drop(columns="metric").reset_index(drop=True)


def style_bar_axis(ax):
  ax.grid(axis="y", color="#e5e4e0", linewidth=0.8)
  ax.set_axisbelow(True)
  for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
  ax.spines["bottom"].set_color("#c3c2b7")
  ax.tick_params(length=0)


def plot_timeouts(runs: pd.DataFrame, model_label: str, axs=None):
  tasks = sorted(runs["task"].unique())
  if axs is None:
    _, axs = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [7, 1.5]})
  task_ax, total_ax = axs

  by_task = runs.groupby(["task", "skills"])["timed_out"].sum()
  by_skills = runs.groupby("skills")["timed_out"].agg(["sum", "size"])
  n_runs = int(by_skills["size"].iloc[0])  # same n for both series (RUNS_PER_BATCH * n tasks)

  for skills, (color, series_label) in SERIES.items():
    xs = [i + (0.19 if skills else -0.19) for i in range(len(tasks))]
    heights = [by_task.get((t, skills), 0) for t in tasks]
    task_ax.bar(xs, heights, width=0.36, color=color + "38", edgecolor=color, linewidth=1.2, zorder=2)
    for x, h in zip(xs, heights):
      if h:
        task_ax.text(x, h + 0.06, f"{h:.0f}", ha="center", va="bottom", fontsize=8.5, color="#52514e")

    x = 0.19 if skills else -0.19
    total = int(by_skills.loc[skills, "sum"])
    total_ax.bar(x, total, width=0.36, color=color + "38", edgecolor=color, linewidth=1.2, zorder=2)
    total_ax.text(x, total + 0.4, f"{total}/{n_runs}", ha="center", va="bottom", fontsize=9, color="#52514e")

  task_ax.set_xticks(range(len(tasks)))
  task_ax.set_xticklabels(
    [f'{t.split("-")[0]}\n' + textwrap.fill(t.split("-", 1)[1], 12) for t in tasks], fontsize=9
  )
  task_ax.set_xlim(-0.6, len(tasks) - 0.4)
  task_ax.set_ylim(0, max(by_task.max(), 1) * 1.3)
  task_ax.yaxis.set_major_locator(MaxNLocator(integer=True))
  task_ax.set_ylabel(f"Timeouts (of {RUNS_PER_BATCH} runs)")
  task_ax.set_title(
    f"{model_label} — timeouts per task, with and without skills", loc="left", pad=18,
  )
  task_ax.legend(
    handles=[
      Patch(facecolor=color + "38", edgecolor=color, linewidth=1.2, label=series_label)
      for color, series_label in SERIES.values()
    ],
    frameon=False, loc="upper left", ncol=2,
  )
  style_bar_axis(task_ax)

  total_ax.set_xticks([0])
  total_ax.set_xticklabels(["all tasks"], fontsize=9)
  total_ax.set_xlim(-0.6, 0.6)
  total_ax.set_ylim(0, max(by_skills["sum"].max(), 1) * 1.3)
  total_ax.yaxis.set_major_locator(MaxNLocator(integer=True))
  total_ax.set_ylabel(f"Timeouts (of {n_runs} runs)")
  total_ax.set_title("Total", loc="left", pad=18)
  style_bar_axis(total_ax)

  return axs
