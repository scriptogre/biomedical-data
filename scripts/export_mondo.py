#!/usr/bin/env python3
"""Export MONDO Disease Ontology TSVs to Parquet."""

from pathlib import Path
from urllib.request import urlretrieve

import duckdb

BASE_URL = "https://github.com/monarch-initiative/mondo/releases/latest/download"
OUTPUT = Path("output/mondo")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    raw = Path("/tmp/mondo_raw")
    raw.mkdir(parents=True, exist_ok=True)

    db = duckdb.connect()
    for name in ("mondo_nodes", "mondo_edges"):
        tsv = raw / f"{name}.tsv"
        if not tsv.exists():
            print(f"  Downloading {name}.tsv...", flush=True)
            urlretrieve(f"{BASE_URL}/{name}.tsv", tsv)

        out = OUTPUT / f"{name}.parquet"
        db.execute(f"""
            COPY (
                SELECT * FROM read_csv('{tsv}', delim='\t', header=true, quote='')
            ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """)
        count = db.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
        print(f"  {name}.parquet: {count:,} rows", flush=True)

    print("Done.", flush=True)


if __name__ == "__main__":
    main()
