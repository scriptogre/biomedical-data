#!/usr/bin/env python3
"""Export CORUM protein complex data to Parquet."""

import ssl
from pathlib import Path
from urllib.request import urlopen

import duckdb

OUTPUT = Path("output/corum")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    raw = Path("/tmp/corum_raw")
    raw.mkdir(parents=True, exist_ok=True)

    dest = raw / "allComplexes.tsv"
    if not dest.exists():
        print("  Downloading allComplexes.tsv...", flush=True)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        url = "https://mips.helmholtz-muenchen.de/fastapi-corum/public/file/download_current_file?file_id=complete&file_format=txt"
        dest.write_bytes(urlopen(url, context=ctx).read())

    db = duckdb.connect()
    out = OUTPUT / "allComplexes.parquet"
    db.execute(f"""
        COPY (
            SELECT * FROM read_csv('{dest}', delim='\t', header=true, quote='"',
                                   null_padding=true, parallel=false)
        ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    count = db.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
    print(f"  allComplexes.parquet: {count:,} rows", flush=True)
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
