# The `data/` directory

One directory per model per stand: `data/<vendor>/<slug>/`. The same model run
on different hardware gets its own slug (`muse-glimmer-30b` vs
`muse-glimmer-30b-m5max`), because mixing stands inside one directory makes the
per-task means meaningless.

| file | required | what it is |
|---|---|---|
| `benchmark.csv` | yes | one row per run |
| `runs.tar.xz` | yes | the raw artefacts of those runs |
| `presets.ini` | for local models | the exact llama.cpp flags used |

## `benchmark.csv`

Twenty-two canonical columns, in this order:

```
task, run, start_time, skills, score, points, total, passed, structure_match,
duration_seconds, timed_out, interrupted, model, harness, model_server,
hardware, fields, input_tokens, output_tokens, cache_read_tokens,
cache_write_tokens, total_tokens
```

`fields` is a Python `repr()` of the grader's per-field dict, single quotes and
all — that is how the existing datasets store it, and `ast.literal_eval` reads
it back.

Write it with `lineterminator="\n"`. Python's `csv` module defaults to `\r\n`,
which makes every line differ from the existing files even when the data is
identical.

### Extra columns

Anything beyond the canonical twenty-two goes **after** them, never in the
middle. Datasets that lack those fields then come back as `NaN` under
`pandas.concat`, and code selecting by name is unaffected.

The M5 Max datasets carry seven, describing the stand per run rather than per
directory:

```
temperature, top_p, top_k, context_size, timeout_minutes,
kv_cache_type, quantization
```

`timeout_minutes` is per **task**, not per model. Time limits get raised
mid-series often enough that one number per model would misdescribe most rows —
and knowing which limit a run had is the difference between "the model could
not" and "the run was cut off".

## `runs.tar.xz`

```
runs/<task>/<run-id>/eval_result.json
runs/<task>/<run-id>/outputs/output.json
runs/<task>/<run-id>/outputs/task.ipynb
runs/<task>/<run-id>/prompt.txt
runs/<task>/<run-id>/run.jsonl
runs/<task>/<run-id>/run.txt
```

`<run-id>` matches the `run` column, so a CSV row and its artefacts always find
each other. Working directories (`workspace/`) stay out.

Check the archive against the CSV after packing — count `eval_result.json`
entries and compare to the row count. A truncated archive is invisible
otherwise: the CSV looks right, and the mismatch only shows up when someone
tries to read a run that is not there.

## Pack it reproducibly

**Identical runs must produce a byte-identical archive.** Otherwise every
re-export writes a fresh 40–90 MB blob into git history, forever, even when
not a single run changed.

That has already cost this repository real weight. `.git` is around 805 MB
against 377 MB of actual data: the history holds two different
`qwen-3.6-35b-m5max/runs.tar.xz` (65 MB and 90 MB) and two different
`nemotron-3.5-lightning-30b-a3b/runs.tar.xz` (54 MB and 59 MB), each pair with
the same contents, plus twenty-five `runs.tar.xz` blobs in total.

Three things make `tar | xz` non-deterministic, and all three need fixing:

1. **File order** — tar walks the directory in whatever order the filesystem
   returns. Feed an explicit sorted list with `-T` and `--no-recursion`.
2. **Headers** — real mtimes, uids, gids and owner names land in the archive.
   Zero the mtimes, pass `--uid 0 --gid 0 --uname '' --gname ''`, and use
   `--format ustar`; `pax` would additionally record atime and ctime.
3. **Compression** — `xz -T0` splits the stream into blocks by core count, so
   the output depends on how busy the machine was. Use `-T1`.

```bash
find runs -print | LC_ALL=C sort > filelist
find runs -exec touch -t 197001010000 {} +
tar --no-recursion --format ustar \
    --uid 0 --gid 0 --uname '' --gname '' \
    -cf - -T filelist | xz -1 -T1 -c > runs.tar.xz
```

Verify by packing the same tree twice and comparing checksums; they should
match exactly.

With this in place, an unchanged dataset produces the same file, git sees no
change, and history stops growing. Re-exporting only the models whose runs
actually changed keeps it smaller still.
