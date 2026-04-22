#!/usr/bin/env python3
"""Export Open Targets Platform Parquet data (consolidate part-files)."""

import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen

import duckdb

BASE = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/latest/output"
RAW = Path("/tmp/opentargets_raw")
OUTPUT = Path("output/opentargets")

DATASETS = [
    "target", "disease", "drug_molecule", "drug_mechanism_of_action",
    "association_overall_direct", "association_by_datatype_direct",
    "clinical_indication",
]


def _download(job: tuple[str, str]) -> None:
    ds, fname = job
    (RAW / ds / fname).write_bytes(urlopen(f"{BASE}/{ds}/{fname}").read())


def download_all() -> None:
    jobs: list[tuple[str, str]] = []
    for ds in DATASETS:
        (RAW / ds).mkdir(parents=True, exist_ok=True)
        html = urlopen(f"{BASE}/{ds}/").read().decode()
        files = re.findall(r'href="([^"]*\.parquet)"', html)
        print(f"  {ds}: {len(files)} files", flush=True)
        jobs.extend((ds, f) for f in files)

    print(f"  total: {len(jobs)} files, downloading...", flush=True)
    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(_download, jobs))


def consolidate() -> None:
    db = duckdb.connect()
    for ds in DATASETS:
        out = OUTPUT / f"{ds}.parquet"
        db.execute(
            f"COPY (SELECT * FROM read_parquet('{RAW / ds}/*.parquet'))"
            f" TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        count = db.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
        print(f"  {ds}.parquet: {count:,} rows", flush=True)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("Downloading Open Targets data...", flush=True)
    download_all()

    print("Consolidating to Parquet...", flush=True)
    consolidate()

    print("Done.", flush=True)


if __name__ == "__main__":
    main()
