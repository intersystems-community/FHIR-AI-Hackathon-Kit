---
name: iris-sql-python
description: Create, load and query InterSystems IRIS SQL tables from Python using the intersystems-irispython DB-API driver (import iris). Covers connecting, CREATE TABLE, parameterised INSERT/SELECT, executemany bulk loads, loading a CSV with pandas type inference, transactions and schema discovery. Use for any tabular / relational data work against IRIS.
---

# IRIS SQL from Python (DB-API)

Source tutorials: `Tutorials/2-tabular/2.1-load-csv-data.ipynb`, `Tutorials/2-tabular/2.2-querying-sql-tables-with-python.ipynb`, skip-setup `Tutorials/setup-scripts/setup_csv_data.py`.

Package: `pip install intersystems-irispython` (import name `iris`). For container ports/creds see the `iris-environment` skill.

## Connect

```python
import iris

connection_args = {
    "hostname": "localhost",
    "port": 32782,
    "namespace": "FHIRSERVER",
    "username": "SuperUser",
    "password": "SYS",
}

conn = iris.connect(**connection_args)
cursor = conn.cursor()
try:
    cursor.execute("SELECT 'Hello From InterSystems IRIS'")
    print(cursor.fetchone()[0])
finally:
    cursor.close()
    conn.close()
```

Always close cursor then connection. Community Edition has a small connection limit; leaked connections cause license errors.

## Create tables

`Schema.Table` naming: `Sample.Person` = package `Sample`, table `Person`.

```python
cursor.execute("DROP TABLE IF EXISTS Sample.Person")   # makes the step re-runnable
cursor.execute("""CREATE TABLE Sample.Person (
    FirstName VARCHAR(30),
    LastName  VARCHAR(30),
    Age       INTEGER)""")
```

Each table gets an implicit `ID` row id column (`WHERE ID=1` works).

## Insert

Use `?` placeholders, never f-string values into SQL.

```python
insert = "INSERT INTO Sample.Person (FirstName, LastName, Age) VALUES (?, ?, ?)"
cursor.execute(insert, ["Peter", "Parker", 18])
cursor.executemany(insert, [["Bruce", "Wayne", 50], ["Clark", "Kent", 35]])
```

For large loads, `executemany` in batches (setup script uses 5000 rows/batch) and log progress per batch.

## Query

Three steps: define, execute, fetch. `cursor.execute(...)` returns a status (-1 on success), not rows; failures raise (`iris.dbapi.ProgrammingError` etc.).

```python
cursor.execute("SELECT FirstName, LastName, Age FROM Sample.Person WHERE Age >= ?", [30])
first = cursor.fetchone()        # DataRow, list(first) for a list
some  = cursor.fetchmany(3)      # next 3 rows
rest  = cursor.fetchall()        # remaining rows
cols  = [d[0] for d in cursor.description]
```

Fetches advance a cursor position. To read all rows again, re-execute.

## Transactions (verified against the kit container)

The driver autocommits by default (`conn.autocommit == True`), so `conn.rollback()` does nothing. For all-or-nothing loads:

```python
conn.autocommit = False
try:
    cursor.executemany(insert, rows)
    conn.commit()
except Exception:
    conn.rollback()
    raise
```

## CSV -> table with inferred types

```python
import pandas as pd

TYPE_MAP = {"int64": "BIGINT", "float64": "DOUBLE", "bool": "BIT", "datetime64[ns]": "TIMESTAMP"}

df = pd.read_csv("Tutorials/data/csv/healthcare_dataset.csv")
cols = [sanitize(c) for c in df.columns]                     # see below
types = [TYPE_MAP.get(str(t), "VARCHAR(32000)") for t in df.dtypes]   # non-listed dtypes are strings
ddl = f"CREATE TABLE {table} ({', '.join(f'{c} {t}' for c, t in zip(cols, types))})"
insert = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
rows = [tuple(None if pd.isna(v) else v.to_pydatetime() if isinstance(v, pd.Timestamp) else v for v in r)
        for r in df.itertuples(index=False, name=None)]
```

- Sanitise identifiers: ASCII only, `[^A-Za-z0-9_]` -> `_`, prefix leading digits and SQL reserved words (e.g. `COL_`), dedupe collisions. The full robust version is the `CSVToTable` class in the 2.1 notebook ("Reusable Class" section); the setup script uses the same column names, e.g. `Blood Type` -> `BLOOD_TYPE`.
- Convert `NaN` -> `None` and `pd.Timestamp` -> `datetime` before inserting.

## Discover schema

```sql
SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'Sample'
SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'Sample' AND TABLE_NAME = 'HealthCareData'
```

IRIS SQL uses `SELECT TOP n`, not `LIMIT`. Identifiers are case-insensitive in queries.

Existing tutorial tables in `FHIRSERVER`: `Sample.Person`, `Sample.HealthCareData`, `Diabetes.VectorStore`.
