#!/usr/bin/env python3
"""Export DrugCentral from public PostgreSQL to Parquet."""

from pathlib import Path

import duckdb

OUTPUT = Path("output/drugcentral")

PG_HOST = "unmtid-dbs.net"
PG_PORT = "5433"
PG_USER = "drugman"
PG_PASSWORD = "dosage"
PG_DB = "drugcentral"

# Official DrugCentral tables (from the canonical pg_dump)
TABLES = [
    "act_table_full", "action_type", "active_ingredient", "approval",
    "approval_type", "atc", "atc_ddd", "attr_type", "data_source",
    "dbversion", "ddi", "ddi_risk", "doid", "doid_xref", "drug_class",
    "faers", "faers_female", "faers_ger", "faers_male", "faers_ped",
    "humanim", "id_type", "identifier", "ijc_connect_items",
    "ijc_connect_structures", "inn_stem", "label", "lincs_signature",
    "ob_exclusivity", "ob_exclusivity_code", "ob_patent",
    "ob_patent_use_code", "ob_product", "omop_relationship", "parentmol",
    "pdb", "pharma_class", "pka", "prd2label", "product", "property",
    "property_type", "protein_type", "ref_type", "reference", "section",
    "struct2atc", "struct2drgclass", "struct2obprod", "struct2parent",
    "struct_type_def", "structure_type", "structures", "synonyms",
    "target_class", "target_component", "target_dictionary", "target_go",
    "target_keyword", "td2tc", "tdgo2tc", "tdkey2tc", "vetomop",
    "vetprod", "vetprod2struct", "vetprod_type", "vettype",
]


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    db = duckdb.connect()
    db.execute("INSTALL postgres; LOAD postgres;")
    db.execute(f"""
        ATTACH 'host={PG_HOST} port={PG_PORT} user={PG_USER}
               password={PG_PASSWORD} dbname={PG_DB}'
        AS dc_db (TYPE postgres, READ_ONLY);
    """)

    print(f"Exporting {len(TABLES)} tables...", flush=True)
    for table_name in TABLES:
        out = OUTPUT / f"{table_name}.parquet"
        try:
            db.execute(
                f"COPY dc_db.public.{table_name} TO '{out}' "
                f"(FORMAT PARQUET, COMPRESSION ZSTD)"
            )
            count = db.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
            print(f"  {table_name}.parquet: {count:,} rows", flush=True)
        except Exception as e:
            print(f"  {table_name}: FAILED ({e})", flush=True)


if __name__ == "__main__":
    main()
