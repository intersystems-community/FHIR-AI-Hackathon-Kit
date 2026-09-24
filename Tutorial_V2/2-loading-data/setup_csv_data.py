"""
Skip-setup script for the 2.1-load-csv-data.ipynb tutorial.

Run this once to recreate the tables the tutorial builds, so you can jump
straight to the querying tutorials without working through 2.1:

* Sample.Person          -- FirstName, LastName, Age (11 superhero rows)
* Sample.HealthCareData  -- healthcare_dataset.csv, with column types inferred

Existing tables with these names are dropped and recreated, so it is safe to
run more than once.

Usage (from any directory):
    python setup_csv_data.py
"""

import re
import time
from pathlib import Path

import iris
import pandas as pd

connection_args = {
    "hostname": "localhost",
    "port": 32782,
    "namespace": "FHIRSERVER",
    "username": "SuperUser",
    "password": "SYS",
}

CSV_DIR = Path(__file__).parent / "data" / "csv"
SUPERHEROS_CSV = CSV_DIR / "superheros.csv"
HEALTHCARE_CSV = CSV_DIR / "healthcare_dataset.csv"

INSERT_BATCH_SIZE = 5000

# Mapping of pandas datatypes to IRIS SQL datatypes (anything else is a string)
TYPE_MAP = {
    "int64": "BIGINT",
    "float64": "DOUBLE",
    "bool": "BIT",
    "datetime64[ns]": "TIMESTAMP",
    "object": "VARCHAR(32000)",
}


def insert_in_batches(cursor, insert_query: str, rows: list, label: str):
    """executemany in chunks, printing progress so large files don't look stuck."""
    start = time.time()
    for batch_start in range(0, len(rows), INSERT_BATCH_SIZE):
        batch = rows[batch_start : batch_start + INSERT_BATCH_SIZE]
        cursor.executemany(insert_query, batch)
        done = batch_start + len(batch)
        print(f"  {label}: inserted {done}/{len(rows)} rows ({time.time() - start:.1f}s)")


def sanitize_column_name(name: str) -> str:
    """Turn a CSV header like 'Blood Type' into a SQL identifier like 'BLOOD_TYPE'."""
    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", safe_name):
        raise ValueError(f"Cannot turn CSV column {name!r} into a SQL identifier (got {safe_name!r})")
    return safe_name


def dataframe_to_rows(df: pd.DataFrame) -> list:
    """Convert a DataFrame to a list of rows for executemany, with NaN as NULL."""
    return [[None if pd.isna(value) else value for value in row] for row in df.itertuples(index=False, name=None)]


def load_person_table(cursor):
    """Sample.Person: hand-written DDL, a few manual rows, then superheros.csv."""
    print("Creating Sample.Person")
    cursor.execute("DROP TABLE IF EXISTS Sample.Person")
    cursor.execute(
        """CREATE TABLE Sample.Person (
                FirstName VARCHAR(30),
                LastName VARCHAR(30),
                Age INTEGER)"""
    )

    insert_statement = "INSERT INTO Sample.Person (FirstName, LastName, Age) VALUES (?, ?, ?)"

    manual_rows = [
        ["Peter", "Parker", 18],
        ["Bruce", "Wayne", 50],
        ["Natasha", "Romanoff", 30],
        ["Clark", "Kent", 35],
        ["Diana", "Prince", 32],
        ["Peter", "Parker", 25],
    ]
    csv_rows = pd.read_csv(SUPERHEROS_CSV).values.tolist()

    insert_in_batches(cursor, insert_statement, manual_rows + csv_rows, "Sample.Person")


def load_healthcare_table(cursor):
    """Sample.HealthCareData: DDL inferred from the CSV's column types."""
    table_name = "Sample.HealthCareData"

    print(f"Reading {HEALTHCARE_CSV.name}")
    df = pd.read_csv(HEALTHCARE_CSV)

    column_names = [sanitize_column_name(col) for col in df.columns]
    column_types = [TYPE_MAP.get(str(dtype), "VARCHAR(32000)") for dtype in df.dtypes]
    column_defs = [f"{name} {sql_type}" for name, sql_type in zip(column_names, column_types)]

    ddl = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"
    placeholders = ", ".join("?" for _ in column_names)
    insert_query = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"

    print(f"Creating {table_name}")
    print(f"  {ddl}")
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    cursor.execute(ddl)

    insert_in_batches(cursor, insert_query, dataframe_to_rows(df), table_name)


def main():
    print(f"Connecting to IRIS at {connection_args['hostname']}:{connection_args['port']} ({connection_args['namespace']})")
    conn = iris.connect(**connection_args)
    cursor = conn.cursor()
    try:
        load_person_table(cursor)
        conn.commit()
        load_healthcare_table(cursor)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    print("Done. Sample.Person and Sample.HealthCareData are ready.")


if __name__ == "__main__":
    main()
