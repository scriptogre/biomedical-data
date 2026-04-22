#!/usr/bin/env python3
"""Export AACT Clinical Trials flat files to Parquet."""

import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen, urlretrieve

import duckdb

OUTPUT = Path("output/clinicaltrials")


def discover_latest() -> str:
    for days_ago in range(8):
        d = date.today() - timedelta(days=days_ago)
        url = f"https://aact.ctti-clinicaltrials.org/static/exported_files/daily/{d}?source=web"
        try:
            resp = urlopen(url)
            resp.close()
            return str(d)
        except HTTPError:
            continue
    print("ERROR: Could not find AACT snapshot.", flush=True)
    sys.exit(1)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("Discovering latest AACT snapshot...", flush=True)
    snapshot_date = discover_latest()
    print(f"  Latest: {snapshot_date}", flush=True)

    zip_path = Path(f"/tmp/aact_{snapshot_date}.zip")
    if not zip_path.exists():
        url = f"https://aact.ctti-clinicaltrials.org/static/exported_files/daily/{snapshot_date}?source=web"
        print("Downloading flat files (~2.2 GB)...", flush=True)
        urlretrieve(url, zip_path)

    db = duckdb.connect()
    with zipfile.ZipFile(zip_path) as z:
        txt_files = [n for n in z.namelist() if n.endswith(".txt")]
        print(f"Converting {len(txt_files)} tables...", flush=True)

        for name in sorted(txt_files):
            table_name = Path(name).stem
            z.extract(name, "/tmp/aact_flat")
            txt_path = Path(f"/tmp/aact_flat/{name}")
            out = OUTPUT / f"{table_name}.parquet"

            try:
                db.execute(
                    f"COPY (SELECT * FROM read_csv('{txt_path}', delim='|', "
                    f"header=true, null_padding=true, parallel=false, "
                    f"quote='\"', all_varchar=true)) "
                    f"TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)"
                )
                count = db.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
                print(f"  {table_name}.parquet: {count:,} rows", flush=True)
            except Exception as e:
                print(f"  {table_name}: FAILED ({e})", flush=True)
            finally:
                txt_path.unlink(missing_ok=True)

    print("Done.", flush=True)


if __name__ == "__main__":
    main()
