"""Tests for Tutorial_V2/2-loading-data/2.1-load-csv-data.ipynb.

Three layers, cheapest first:

* `TestConnectionDetails` -- the credentials/port/namespace written in the
  notebook are valid against the running IRIS instance. These are the tests that
  catch drift in `docker-compose.yml` port mappings or IRIS passwords.
* `TestNotebookStructure` -- the notebook still contains the data files and cells
  the tutorial narrative depends on.
* `TestNotebookExecution` -- the whole notebook runs top-to-bottom without a
  single cell raising, and the loaded tables contain the expected row counts.
"""

import iris
import pandas as pd
import pytest

from conftest import (
    LOADING_DATA_DIR,
    NOTEBOOK_2_1,
    cell_text,
    assert_no_cell_errors,
    execute_notebook,
    find_cell,
    read_notebook,
)

SUPERHEROS_CSV = LOADING_DATA_DIR / "data" / "csv" / "superheros.csv"
HEALTHCARE_CSV = LOADING_DATA_DIR / "data" / "csv" / "healthcare_dataset.csv"

# Tables the notebook creates. Dropped before execution so the notebook's bare
# CREATE TABLE statements (which have no IF NOT EXISTS guard) succeed.
NOTEBOOK_TABLES = ["Sample.Person", "Sample.HealthCareData"]

# Rows the notebook inserts into Sample.Person: one Peter Parker, five comic
# book characters, then the five rows of superheros.csv.
EXPECTED_PERSON_ROWS = 1 + 5 + 5


def drop_notebook_tables(connection_args: dict):
    """Drop the tables notebook 2.1 creates, so it can be run from a clean slate."""
    conn = iris.connect(**connection_args)
    try:
        cursor = conn.cursor()
        for table in NOTEBOOK_TABLES:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()
        cursor.close()
    finally:
        conn.close()


def scalar_query(connection_args: dict, sql: str):
    """Run a single-value query and return that value."""
    conn = iris.connect(**connection_args)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        row = cursor.fetchone()
        value = row[0]  # Read before closing: the driver invalidates rows on close.
        cursor.close()
        return value
    finally:
        conn.close()


class TestConnectionDetails:
    """The IRIS connection details written into notebook 2.1 must be valid."""

    def test_connection_args_has_all_required_keys(self, iris_connection_args):
        assert set(iris_connection_args) == {
            "hostname",
            "port",
            "namespace",
            "username",
            "password",
        }, (
            "connection_args in 2.1 no longer has the documented keys: "
            f"{sorted(iris_connection_args)}"
        )

    def test_port_is_the_superserver_port(self, iris_connection_args):
        """The notebook explicitly warns this must be the superserver port, not 52773."""
        assert iris_connection_args["port"] != 52773, (
            "connection_args['port'] is the web server port. The DB-API driver "
            "needs the superserver port (1972 inside the container)."
        )

    def test_credentials_and_endpoint_accept_a_connection(self, iris_connection_args):
        """Fails loudly if the port mapping, namespace, user or password has changed."""
        try:
            conn = iris.connect(**iris_connection_args)
        except Exception as exc:
            pytest.fail(
                "Could not connect to IRIS with the connection_args written in "
                f"2.1-load-csv-data.ipynb ({iris_connection_args!r}).\n"
                "Check the superserver port mapping in docker-iris-fhir/docker-compose.yml "
                f"and the username/password/namespace.\nError: {exc}"
            )
        conn.close()

    def test_hello_from_iris_query_returns_expected_string(self, iris_connection_args):
        """The notebook's first cell prints 'Hello From IRIS'."""
        assert scalar_query(iris_connection_args, "SELECT 'Hello From IRIS'") == "Hello From IRIS"

    def test_connected_namespace_matches_connection_args(self, iris_connection_args):
        namespace = scalar_query(iris_connection_args, "SELECT $NAMESPACE")
        assert namespace.upper() == iris_connection_args["namespace"].upper(), (
            f"Connected to namespace {namespace!r} but connection_args asks for "
            f"{iris_connection_args['namespace']!r}."
        )


class TestNotebookStructure:
    """The notebook and its data files still have the shape the tutorial describes."""

    def test_csv_data_files_exist(self):
        assert SUPERHEROS_CSV.exists(), f"Missing CSV referenced by the notebook: {SUPERHEROS_CSV}"
        assert HEALTHCARE_CSV.exists(), f"Missing CSV referenced by the notebook: {HEALTHCARE_CSV}"

    def test_superheros_csv_has_the_documented_columns(self):
        df = pd.read_csv(SUPERHEROS_CSV)
        assert list(df.columns) == ["first_name", "last_name", "age"]
        assert len(df) == 5

    def test_healthcare_csv_is_non_trivial(self):
        df = pd.read_csv(HEALTHCARE_CSV, nrows=5)
        assert len(df.columns) > 1, "healthcare_dataset.csv parsed as a single column."

    def test_dependencies_importable(self):
        """The pip-install cells are skipped at execution time; assert the packages exist."""
        pytest.importorskip("iris", reason="intersystems-irispython is not installed")
        pytest.importorskip("pandas", reason="pandas is not installed")

    def test_reusable_class_cell_is_present(self):
        """The tutorial's headline deliverable is the CSVToTable class."""
        nb = read_notebook(NOTEBOOK_2_1)
        find_cell(nb, "class CSVToTable")


@pytest.fixture(scope="module")
def executed(iris_connection_args):
    """Notebook 2.1 executed once from a clean slate, and cleaned up afterwards."""
    drop_notebook_tables(iris_connection_args)
    yield execute_notebook(NOTEBOOK_2_1)
    drop_notebook_tables(iris_connection_args)


class TestNotebookExecution:
    """Execute 2.1 end to end and check the outputs and resulting tables."""

    def test_no_cell_raises(self, executed):
        assert_no_cell_errors(executed)

    def test_hello_cell_prints_greeting(self, executed):
        cell = find_cell(executed, "Hello From IRIS")
        assert "Hello From IRIS" in cell_text(cell)

    def test_superheros_dataframe_preview_rendered(self, executed):
        """`df.head()` on superheros.csv should show the comic book names."""
        cell = find_cell(executed, "superheros.csv")
        text = cell_text(cell)
        assert "Stark" in text and "Rogers" in text, (
            f"df.head() output did not contain the expected names. Got:\n{text}"
        )

    def test_reusable_class_reports_rows_inserted(self, executed):
        """The final cell prints the DDL, insert query, mapping and row count."""
        cell = find_cell(executed, "loader.run(csv_path, table_name)")
        text = cell_text(cell)
        expected_rows = len(pd.read_csv(HEALTHCARE_CSV))
        assert "CREATE TABLE" in text, f"No DDL printed. Got:\n{text}"
        assert "INSERT INTO" in text, f"No insert query printed. Got:\n{text}"
        assert f"Inserted {expected_rows} rows." in text, (
            f"Expected 'Inserted {expected_rows} rows.' in output. Got:\n{text}"
        )

    def test_person_table_has_expected_rows(self, executed, iris_connection_args):
        count = scalar_query(iris_connection_args, "SELECT COUNT(*) FROM Sample.Person")
        assert count == EXPECTED_PERSON_ROWS, (
            f"Sample.Person has {count} rows, expected {EXPECTED_PERSON_ROWS} "
            "(1 single insert + 5 executemany rows + 5 rows from superheros.csv)."
        )

    def test_person_table_contains_csv_loaded_row(self, executed, iris_connection_args):
        count = scalar_query(
            iris_connection_args,
            "SELECT COUNT(*) FROM Sample.Person WHERE LastName = 'Stark' AND Age = 45",
        )
        assert count == 1, "Tony Stark (45) from superheros.csv is not in Sample.Person."

    def test_healthcare_table_row_count_matches_csv(self, executed, iris_connection_args):
        expected = len(pd.read_csv(HEALTHCARE_CSV))
        count = scalar_query(iris_connection_args, "SELECT COUNT(*) FROM Sample.HealthCareData")
        assert count == expected, (
            f"Sample.HealthCareData has {count} rows but the CSV has {expected}."
        )
