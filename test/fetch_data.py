#!/usr/bin/env python3
"""Downloads a task's data/ directory from the source(s) declared in its
task.json, grouped one subfolder per sample.

Usage:
    ./fetch_data.py <task-dir>            # e.g. ./fetch_data.py 01-data-loading
    ./fetch_data.py <task-dir> --force    # re-download files that already exist

task.json declares what to fetch via a "data" field, either a single object
or a list of them (one task can need several GEO samples):
    "data": {"type": "GEO", "uri": "GSM4339771"}
    "data": [{"type": "GEO", "uri": "GSM4339771"}, {"type": "GEO", "uri": "GSM4339772"}]

Each entry becomes data/<uri>/ (accession as the folder name - task prompts
are expected to tell the agent what each accession represents, rather than
this script encoding a friendly sample name). For "type": "GEO", the
accession's entire suppl/ directory on GEO's FTP server is downloaded as-is
(GEO's own listing is the source of truth for what belongs to a sample, no
per-task file filtering).

An optional "path" overrides the destination folder, relative to data/ -
useful when several accessions' files belong together (e.g. RNA-seq and
TCR-seq GSMs for the same physical sample):
    "data": [{"type": "GEO", "uri": "GSM4385992", "path": "C143"},
             {"type": "GEO", "uri": "GSM4339771", "path": "C143"}]
Both entries' files land together in data/C143/.

Only "type": "GEO" is implemented; anything else dies with a clear error so
a typo in task.json doesn't silently no-op. Safe to re-run: existing files
are left alone unless --force is given, same as setup.sh's idempotency.
"""
import argparse
import ftplib
import json
import sys
from pathlib import Path

GEO_FTP_HOST = "ftp.ncbi.nlm.nih.gov"


def log(msg):
    print(f">> {msg}")


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def geo_suppl_path(accession):
    # NCBI buckets each sample's files under .../GSMnnnnnn/GSMxxxxxxx/suppl/,
    # where the bucket name replaces the accession's last 3 digits with
    # "nnn" - e.g. GSM4339771 -> /geo/samples/GSM4339nnn/GSM4339771/suppl.
    if not (accession.startswith("GSM") and accession[3:].isdigit() and len(accession) > 6):
        die(f"'{accession}' doesn't look like a GEO sample accession (expected e.g. GSM4339771)")
    return f"/geo/samples/{accession[:-3]}nnn/{accession}/suppl"


def fetch_geo_sample(accession, dest_dir, force):
    dest_dir.mkdir(parents=True, exist_ok=True)
    remote_dir = geo_suppl_path(accession)
    try:
        ftp = ftplib.FTP(GEO_FTP_HOST, timeout=30)
        ftp.login()
        ftp.cwd(remote_dir)
        names = ftp.nlst()
        # nlst() leaves (or resets) the session in ASCII mode, and SIZE
        # refuses to run in it - binary mode has to be set after, not before.
        ftp.voidcmd("TYPE I")
    except ftplib.all_errors as e:
        die(f"Couldn't list {GEO_FTP_HOST}{remote_dir}: {e}")
    if not names:
        die(f"{accession}'s suppl/ directory is empty - nothing to download.")

    for name in names:
        target = dest_dir / name
        if target.exists() and not force:
            log(f"  {accession}/{name} already present, skipping (--force to re-download)")
            continue
        try:
            size = ftp.size(name)
        except ftplib.all_errors:
            size = None
        log(f"  {accession}/{name} ({size if size is not None else '?'} bytes)")
        try:
            with open(target, "wb") as f:
                ftp.retrbinary(f"RETR {name}", f.write)
        except ftplib.all_errors as e:
            target.unlink(missing_ok=True)
            die(f"Download failed for {accession}/{name}: {e}")
    ftp.quit()


FETCHERS = {"GEO": fetch_geo_sample}


def fetch_task_data(task_dir, force=False):
    task_json = task_dir / "task.json"
    if not task_json.is_file():
        die(f"Missing task.json in {task_dir}")
    spec = json.loads(task_json.read_text()).get("data")
    if not spec:
        die(f"{task_json} has no \"data\" field - nothing declared to fetch.")
    entries = spec if isinstance(spec, list) else [spec]

    data_dir = task_dir / "data"
    for entry in entries:
        etype = entry.get("type")
        uri = entry.get("uri")
        fetcher = FETCHERS.get(etype)
        if fetcher is None:
            die(f"Unsupported data type '{etype}' (only {sorted(FETCHERS)} implemented) in {entry}")
        if not uri:
            die(f"Data entry missing \"uri\": {entry}")
        dest_name = entry.get("path") or uri
        log(f"Fetching {etype} {uri} -> {data_dir / dest_name}/")
        fetcher(uri, data_dir / dest_name, force)
    log(f"Done. Data in {data_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task_dir", type=Path, help="task directory containing task.json, e.g. 01-data-loading")
    parser.add_argument("--force", action="store_true", help="re-download files that already exist on disk")
    args = parser.parse_args()
    if not args.task_dir.is_dir():
        die(f"No such directory: {args.task_dir}")
    fetch_task_data(args.task_dir, args.force)


if __name__ == "__main__":
    main()
