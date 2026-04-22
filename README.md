# Biomedical Data (Parquet)

Pre-built zstd-compressed Parquet files for biomedical databases that only distribute data as database dumps or flat files.

Automated monthly via GitHub Actions. Download from [Releases](https://github.com/scriptogre/biomedical-data/releases).

## Databases

| Database | Source Format | Export Method |
|---|---|---|
| **DrugCentral** | PostgreSQL (public instance) | DuckDB postgres scanner |
| **Pharos/TCRD** | MySQL dump (FigShare) | Temp MySQL container + DuckDB mysql scanner |
| **Open Targets** | Parquet part-files (EBI FTP) | Consolidate via DuckDB |
| **Clinical Trials (AACT)** | Pipe-delimited flat files | DuckDB CSV reader |
| **MONDO** | TSV (GitHub releases) | DuckDB CSV reader |
| **STRING** | TSV (StringDB) | DuckDB CSV reader |
| **CORUM** | TSV (Helmholtz Munich) | DuckDB CSV reader |

## Usage

```bash
# Download a database
gh release download drugcentral/latest -R scriptogre/biomedical-data
tar xzf drugcentral.tar.gz -C data/drugcentral/
```

```python
import duckdb
conn = duckdb.connect()
conn.execute("SELECT * FROM read_parquet('data/drugcentral/structures.parquet') LIMIT 10")
```

## License

Each database retains its original license. This repository only provides format conversion.
