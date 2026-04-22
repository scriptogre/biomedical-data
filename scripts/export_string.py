#!/usr/bin/env python3
"""Export STRING protein interaction data to Parquet."""

import gzip
import json
from pathlib import Path
from urllib.request import urlopen, urlretrieve

import duckdb

TAXON = "9606"
OUTPUT = Path("output/string")


def get_version() -> str:
    data = json.loads(urlopen("https://string-db.org/api/json/version").read())
    return data[0]["string_version"]


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    raw = Path("/tmp/string_raw")
    raw.mkdir(parents=True, exist_ok=True)

    print("Fetching STRING version...", flush=True)
    version = get_version()
    print(f"  Version: {version}", flush=True)

    base = "https://stringdb-downloads.org/download"
    files = {
        "protein_info": f"protein.info.v{version}/{TAXON}.protein.info.v{version}.txt.gz",
        "protein_aliases": f"protein.aliases.v{version}/{TAXON}.protein.aliases.v{version}.txt.gz",
        "interaction": f"protein.physical.links.full.v{version}/{TAXON}.protein.physical.links.full.v{version}.txt.gz",
    }

    db = duckdb.connect()
    for name, remote in files.items():
        filename = remote.split("/")[-1].removesuffix(".gz")
        dest = raw / filename
        if not dest.exists():
            print(f"  Downloading {filename}...", flush=True)
            data = urlopen(f"{base}/{remote}").read()
            dest.write_bytes(gzip.decompress(data))

        out = OUTPUT / f"{name}.parquet"
        # protein_info and protein_aliases have '#' prefix on first column
        if name in ("protein_info", "protein_aliases"):
            db.execute(f"""
                COPY (
                    SELECT "#string_protein_id" AS string_protein_id, *
                    EXCLUDE ("#string_protein_id")
                    FROM read_csv('{dest}', delim='\t', header=true, quote='')
                ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """)
        else:
            # interaction file is space-delimited
            db.execute(f"""
                COPY (
                    SELECT * FROM read_csv('{dest}', delim=' ', header=true, quote='')
                ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """)
        count = db.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
        print(f"  {name}.parquet: {count:,} rows", flush=True)

    Path("output/string_version.txt").write_text(version)
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
