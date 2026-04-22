# Biomedical Data (Parquet)

Zstd-compressed Parquet exports of biomedical databases for use with [DuckDB](https://duckdb.org/). These are **curated subsets** tailored for pharmacology research — not full database mirrors.

Automated monthly via GitHub Actions. Download from [Releases](https://github.com/scriptogre/biomedical-data/releases).

## Databases

| Database | What's included | Source |
|---|---|---|
| **DrugCentral** | All tables from the official schema | [Public PostgreSQL](https://unmtid-dbs.net/) |
| **Pharos/TCRD** | All tables from the MySQL dump | [FigShare](https://figshare.com/search?q=pharos+database+mysql) |
| **Open Targets** | Selected datasets (targets, diseases, drugs, associations, mechanisms, indications) | [EBI FTP](https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/latest/) |
| **Clinical Trials (AACT)** | All tables from the daily flat file export | [AACT](https://aact.ctti-clinicaltrials.org/downloads) |
| **MONDO** | Full ontology (nodes + edges) | [GitHub releases](https://github.com/monarch-initiative/mondo/releases) |
| **STRING** | Human (taxon 9606) only: protein info, aliases, physical interactions | [StringDB](https://string-db.org/) |
| **CORUM** | Full complex dataset | [Helmholtz Munich](https://mips.helmholtz-muenchen.de/corum/) |

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
