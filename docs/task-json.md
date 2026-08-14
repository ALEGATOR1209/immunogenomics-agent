# Writing `task.json` files

`test/<NN-name>/task.json` is the whole definition of one eval task: the
prompt the agent sees, the answer it's graded against, and (optionally)
where its input data comes from. This doc covers how to write one. For how
the harness runs a task once `task.json` exists, see `test/test.py`'s
docstring and the "Architecture: the eval harness" section of `CLAUDE.md`.

## Where it lives

Task directories are numbered and short-named: `test/01-data-loading/`,
`test/02-clonotype-analysis/`, etc. A task directory needs `task.json` at
minimum; `data/` (either fetched or supplied - see below), an optional
`starter.ipynb`, and a generated `Dockerfile` join it once you've run the
task at least once.

## Full example

Annotated version of `test/01-data-loading/task.json`:

```jsonc
{
  // Optional. Tells fetch_data.py what to download into data/. Omit this
  // field entirely if you're supplying data/ by hand instead.
  "data": [
    { "type": "GEO", "uri": "GSM4385992", "path": "C143" },
    { "type": "GEO", "uri": "GSM4339771", "path": "C143" }
  ],

  // Required. How the agent's output.json gets scored.
  "grader": {
    "config": {
      // Field name -> correct value. The agent sees these key names (and
      // only these key names) as the required output.json shape, with
      // every value masked to its zero-equivalent - it never sees the
      // values below.
      "ground_truth": {
        "n_cells": 20857,
        "n_tcr": 2186,
        "nc_gene_id": "nCoV",
        "fst_gene_id": "A1BG",
        "airr_cell": "AAACCTGAGCTGCAAG-1"
      },
      // Optional, per numeric field. A field with no entry here must match
      // ground_truth exactly (case-insensitive for strings).
      "tolerances": {
        "n_cells": { "type": "absolute", "value": 0 },
        "n_tcr": { "type": "absolute", "value": 0 }
      }
    },
    "type": "numeric_tolerance"
  },

  // Conventional identifier. Not read by any script - purely for humans
  // scanning task.json/eval_result.json files.
  "id": "10x-data-loading-scirpy-tutorial",

  // Conventional, free-form. Also not read by any script today.
  "metadata": {
    "eval_type": "scientific",
    "kit": "scirpy",
    "task": "data-loading"
  },

  // Required. The prompt text, verbatim, substituted into SYSTEM.md's
  // <TASK> placeholder.
  "task": "There is a 10x-genomics single cell CellRanger data with RNA-seq (feature bc matrix) and TCR-seq (contig annotations) data. Output the total number of cells in the sample, number of cells with TCR repertoires data. ..."
}
```

## Field reference

### `task` (string, required)

The task prompt, dropped verbatim into `test/SYSTEM.md`'s `<TASK>`
placeholder by `render_prompt.py`. It's the only description of the task
the agent gets - there's no separate "context" or "background" field, so
write it self-contained:

- State what data is present (modality, format, sample structure) since the
  agent can't see this doc or your notes, only what render_prompt.py
  produces plus whatever's mounted at `data/` and (with `--skills`) the
  skills it chooses to load.
- Ask for each `ground_truth` field explicitly, in a way a careful reader
  could answer unambiguously - the agent has no way to guess an unstated
  tie-breaking rule (e.g. "sort ascending, take the first" needs to be said,
  not implied).
- Keep it a single string. Long prompts (see `03-clonotype-networks`) are
  fine - there's no length limit enforced.

### `grader` (object, required)

`grader.config.ground_truth` is a flat object of `field_name: correct_value`.
Whatever keys you put here become exactly the `output.json` shape the agent
must produce (`render_prompt.py` masks every value to its type's
zero-equivalent - `0`, `0.0`, `""`, `false`, or `null` - so the agent sees
the required keys and value *types* but never the answers). Rules of thumb:

- Use real `int`/`float`/`str`/`bool` JSON types for the values, not
  stringified numbers - the mask function and the tolerance comparison both
  branch on Python type, so `"n_cells": "20857"` would mask to `""` (a
  string placeholder) instead of `0`, misleading the agent about the
  expected shape.
- Key order matters for readability: it's the order fields appear in the
  masked shape shown to the agent, so order them the way you'd want someone
  reading the prompt to fill them in.
- Key *names* are visible to the agent verbatim - don't leak the answer
  into a key name (e.g. don't do `"answer_is_LT5": false`).

`grader.config.tolerances` is optional, keyed by the same field names. Two
types are implemented in `test/grade.py`:

- `{"type": "absolute", "value": N}` - `abs(actual - expected) <= value`,
  for numeric fields.
- `{"type": "list_overlap"}` - for a `ground_truth` field whose value is a
  *list* (e.g. "the two most abundant X, order doesn't matter"). Both sides
  are compared as sets (case-insensitive, deduplicated); a bare string
  answer is coerced to a one-item list so a model that ignores the list
  shape can still get partial credit. Score is Jaccard overlap: `n_correct /
  (n_ground_truth + n_incorrect_guessed)` - 1.0 only when the sets match
  exactly, 0 when there's no overlap, and a fraction in between for partial
  matches. Guessing extra wrong items on top of a correct one costs points
  (grows the denominator), so it doesn't pay to pad the list. Use this
  instead of `"absolute"` whenever the "correct" answer is inherently a
  near-tie between two categories in the underlying data (see
  `07-epitope-databases`'s `top_antigen_species_tumor`, changed from a
  single-string second-most-abundant field to a 2-item list after runs
  showed the single-answer version flipped between two categories separated
  by a handful of cells - not a sign of model error, just an unstable
  ranking).

Fields with no entry in `tolerances` are compared with `==` (falling back
to case-insensitive string comparison when both sides are strings) - this
is the right choice for categorical/string answers (gene names, sample
ids). Don't add a numeric tolerance to a string field: `grade.py` will
catch the resulting `TypeError`/`ValueError` and just mark that field
wrong, every time, rather than erroring the whole run - a silent
always-fails footgun, not a crash that would tell you something's off. A
numeric field with tolerance `{"type": "absolute", "value": 0}` still
requires an exact match - use `0` when you want exactness enforced but
still want it to go through the numeric (not string) comparison path.
Pick tolerance values based on how much the exact number is expected to
vary with reasonable-but-different analysis choices (filtering
thresholds, clustering parameters) - see the existing tasks for the range
used in practice (`02-clonotype-analysis` through `07-clonal-expansion`).

Each field contributes at most 1 point regardless of tolerance type -
`grade.py`'s per-field `"score"` (0 to 1) is what's summed into the
top-level `points`/`score`, while `"correct"` stays a bool (`score == 1.0`)
for `passed`/structure-comparison purposes.

`grader.type` (currently always `"numeric_tolerance"` in existing tasks) is
**not read by any script** - `grade.py` only ever looks at `grader.config`.
Keep setting it for consistency with existing tasks (and in case a future
grader dispatches on it), but don't expect changing it to change behavior
today.

### `id` (string, conventional)

A human-readable slug, e.g. `10x-data-loading-scirpy-tutorial`. Not read by
any script - it exists so someone scanning several `task.json` /
`eval_result.json` files can tell tasks apart at a glance. Follow the
existing `<dataset>-<task-name>-<source>` pattern.

### `metadata` (object, conventional)

Free-form, not read by any script. Existing tasks use `eval_type` (e.g.
`"scientific"`), `kit` (e.g. `"scirpy"`), and `task` (a short slug matching
the directory name minus its number, e.g. `"data-loading"`). Keep using the
same three keys unless you have a concrete reason to diverge - consistency
here is what makes cross-task analysis of `eval_result.json` files
possible later, even though nothing enforces it today.

### `data` (object or array, optional)

Tells `test/fetch_data.py` what to download into `data/` automatically.
Omit this field entirely for tasks whose data has to be supplied by hand
(the harness will tell you to on a fresh clone, via `setup.sh`'s or
`test.py`'s "missing data/" message).

A single source:

```json
"data": { "type": "GEO", "uri": "GSM4339771" }
```

or a list, for tasks needing several samples:

```json
"data": [
  { "type": "GEO", "uri": "GSM4339771" },
  { "type": "GEO", "uri": "GSM4339772" }
]
```

Each entry needs:

- `"type"` - only `"GEO"` is implemented. Anything else makes
  `fetch_data.py` die loudly (not silently skip), so a typo surfaces
  immediately.
- `"uri"` - a GEO sample accession (`GSMxxxxxxx`). `fetch_data.py`
  downloads that sample's entire `suppl/` directory from GEO's FTP server
  as-is - no per-file filtering, so make sure you actually want everything
  GEO lists there.
- `"path"` (optional) - overrides the destination folder under `data/`,
  which otherwise defaults to the accession itself. Useful when a single
  physical sample's data is split across multiple GEO accessions (e.g. a
  GEX matrix and a TCR-seq contig file registered as separate GSMs): give
  them the same `"path"` and both accessions' files land together in one
  folder, as in the example above (`data/C143/` from two different `uri`s).

Because folders are named by accession (or by `path` if you set one), not a
friendly label, the task prompt is responsible for telling the agent what
each folder/sample represents (e.g. "the tumor sample" vs. "the
normal-adjacent sample") - `fetch_data.py` has no field for that.

## Adding a new task, step by step

1. `mkdir test/<NN-name>` with the next number and a short slug.
2. Write `task.json` (`task`, `grader`, `id`, `metadata`, and `data` if the
   task should self-provision from GEO).
3. Get `data/` in place: `cd test && ./fetch_data.py <NN-name>` if you used
   the `data` field (or `test.py` will do this on its first run), otherwise
   supply `data/` by hand.
4. Optional: add `starter.ipynb` at the task directory root (not inside
   `data/` - that mount is read-only) if the task should begin from a
   partially-built notebook rather than empty. See `04-gene-usage`,
   `06-clonotype-clustering`, `07-clonal-expansion` for examples, and their
   task prompts for the "there's a jupyter notebook ... already set up.
   Build upon." phrasing that goes with it.
5. Before spending a full agent run, sanity-check the grading side alone:
   hand-write a plausible `output.json` and run
   `python3 grade.py task.json output.json` to confirm your `ground_truth`
   types and `tolerances` behave the way you expect.
6. Run it for real from inside `test/`: `./test.py <NN-name> --skills`
   (add `--timeout 5` for a quick sanity run before committing to a full
   20+ minute one).

A `Dockerfile` is generated into the task directory the first time you run
it, from the same template every task uses (`test/test.py`'s
`DOCKERFILE_TEMPLATE`). You don't need to write one; if it already exists,
`test.py` reuses it as-is, so delete it if you want the template
regenerated.
