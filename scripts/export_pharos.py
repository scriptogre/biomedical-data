#!/usr/bin/env python3
"""Export Pharos/TCRD from MySQL dump to Parquet.

Requires Docker (spins up a temporary MySQL container).
The MySQL dump is downloaded from FigShare automatically.
"""

import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import duckdb

OUTPUT = Path("output/pharos")
CONTAINER = "pharos-export-mysql"
MYSQL_PASSWORD = "pharos"
MYSQL_PORT = "3307"


def resolve_latest() -> tuple[str, str]:
    """Return (version, download_url) for the latest Pharos MySQL dump."""
    req = urllib.request.Request(
        "https://api.figshare.com/v2/articles/search",
        data=json.dumps({
            "search_for": "Pharos database MySQL",
            "author": "Keith Kelleher",
            "order": "published_date",
            "order_direction": "desc",
            "page_size": 1,
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    articles = json.loads(urllib.request.urlopen(req).read())
    article = json.loads(
        urllib.request.urlopen(
            f"https://api.figshare.com/v2/articles/{articles[0]['id']}"
        ).read()
    )
    version = re.search(r"[0-9]+\.[0-9]+", article["title"]).group()
    url = article["files"][0]["download_url"]
    return version, url


def start_mysql() -> None:
    subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)
    subprocess.run(
        [
            "docker", "run", "--name", CONTAINER,
            "-e", f"MYSQL_ROOT_PASSWORD={MYSQL_PASSWORD}",
            "-p", f"{MYSQL_PORT}:3306",
            "-d", "mysql:8",
            "--disable-log-bin",
            "--innodb-flush-log-at-trx-commit=0",
            "--innodb-doublewrite=0",
            "--innodb-buffer-pool-size=4G",
            "--innodb-log-file-size=1G",
            "--innodb-write-io-threads=16",
            "--sync-binlog=0",
        ],
        check=True,
    )

    print("  Waiting for MySQL...", flush=True)
    for _ in range(120):
        result = subprocess.run(
            ["docker", "exec", CONTAINER,
             "mysql", "-uroot", f"-p{MYSQL_PASSWORD}", "-e", "SELECT 1"],
            capture_output=True,
        )
        if result.returncode == 0:
            return
        time.sleep(2)
    raise RuntimeError("MySQL container failed to start")


def restore_dump(dump_path: Path) -> None:
    gunzip = subprocess.Popen(["gunzip", "-c", str(dump_path)], stdout=subprocess.PIPE)
    mysql = subprocess.Popen(
        ["docker", "exec", "-i", CONTAINER,
         "mysql", "-uroot", f"-p{MYSQL_PASSWORD}"],
        stdin=gunzip.stdout,
    )
    gunzip.stdout.close()
    mysql.wait()
    if mysql.returncode != 0:
        raise RuntimeError("Failed to restore MySQL dump")


def find_database_name() -> str:
    result = subprocess.run(
        ["docker", "exec", CONTAINER,
         "mysql", "-uroot", f"-p{MYSQL_PASSWORD}", "-N", "-e",
         "SHOW DATABASES LIKE 'pharos%'"],
        capture_output=True, text=True,
    )
    databases = [db for db in result.stdout.strip().split("\n") if db != ""]
    for name in databases:
        if name != "pharos":
            return name
    return "pharos"


def export_to_parquet() -> None:
    mysql_db = find_database_name()
    print(f"  Found database: {mysql_db}", flush=True)

    db = duckdb.connect()
    db.execute("PRAGMA threads=10")
    db.execute("PRAGMA memory_limit='8GB'")
    db.execute("INSTALL mysql; LOAD mysql;")
    db.execute(f"""
        ATTACH 'host=127.0.0.1 port={MYSQL_PORT} user=root
               password={MYSQL_PASSWORD} database={mysql_db}'
        AS pharos_db (TYPE mysql);
    """)

    tables = db.execute(f"""
        SELECT table_name
        FROM pharos_db.information_schema.tables
        WHERE table_schema = '{mysql_db}' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """).fetchall()

    print(f"  Exporting {len(tables)} tables...", flush=True)
    for (table_name,) in tables:
        out = OUTPUT / f"{table_name}.parquet"
        try:
            db.execute(
                f"COPY pharos_db.{table_name} TO '{out}' "
                f"(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 1000000)"
            )
            count = db.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
            print(f"    {table_name}.parquet: {count:,} rows", flush=True)
        except Exception as e:
            print(f"    {table_name}: FAILED ({e})", flush=True)


def stop_mysql() -> None:
    subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("Querying FigShare for latest Pharos...", flush=True)
    version, download_url = resolve_latest()
    print(f"  Found: Pharos v{version}", flush=True)

    dump_path = Path(f"/tmp/pharos-{version}-mysql.sql.gz")
    if not dump_path.exists():
        print("Downloading MySQL dump (~2.1 GB)...", flush=True)
        urllib.request.urlretrieve(download_url, dump_path)

    try:
        print("Starting MySQL container...", flush=True)
        start_mysql()

        print("Restoring dump...", flush=True)
        restore_dump(dump_path)

        print("Exporting to Parquet...", flush=True)
        export_to_parquet()
    finally:
        print("Cleaning up...", flush=True)
        stop_mysql()

    print(f"Done. Version: {version}", flush=True)
    Path("output/pharos_version.txt").write_text(version)


if __name__ == "__main__":
    main()
