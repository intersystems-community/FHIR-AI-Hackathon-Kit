"""Shared fixtures and helpers for the Tutorials notebook tests.

The tests here execute the tutorial notebooks against a live IRIS instance and
assert that:

1. the connection details / endpoints / credentials written in the notebooks
   actually work (so drift in ports, namespaces or passwords is caught), and
2. every cell runs without raising, producing roughly the documented output.

Values are extracted FROM the notebook source rather than duplicated here, so a
future edit to a notebook's credentials is what gets tested.
"""

import ast
import re
import sys
import time
from pathlib import Path

import iris
import nbformat
import pytest
from nbclient import NotebookClient

REPO_ROOT = Path(__file__).resolve().parent.parent
TUTORIAL_ROOT = REPO_ROOT / "Tutorials"
DATA_DIR = TUTORIAL_ROOT / "data"
SETUP_SCRIPTS_DIR = TUTORIAL_ROOT / "setup-scripts"

# The notebooks' load_dotenv() walks up from the notebook folder to this file.
ENV_FILE = REPO_ROOT / ".env"

NOTEBOOK_2_1 = TUTORIAL_ROOT / "2-tabular" / "2.1-load-csv-data.ipynb"
NOTEBOOK_3_1 = TUTORIAL_ROOT / "3-fhir" / "3.1-load-fhir-data.ipynb"

AI_DIR = TUTORIAL_ROOT / "5-ai"
NOTEBOOK_VECTOR_SEARCH = TUTORIAL_ROOT / "4-vector-search" / "4.1-vector-search.ipynb"
NOTEBOOK_AGENTS = AI_DIR / "5.1-agents-and-tools.ipynb"
VECTOR_TABLE = "Diabetes.VectorStore"

# Cells whose source starts with a pip install are skipped when executing a
# notebook: they are slow and would mutate the test runner's environment. The
# packages they install are asserted to be importable instead (see the
# test_dependencies_importable tests).
PIP_CELL_RE = re.compile(r"^\s*[!%]?\s*pip\s+install\b", re.MULTILINE)

KERNEL_TIMEOUT_SECONDS = 900


# ----------------------------------------------------------------------
# Notebook reading / source extraction
# ----------------------------------------------------------------------


def read_notebook(path: Path) -> nbformat.NotebookNode:
    """Read a notebook without executing it."""
    if not path.exists():
        raise FileNotFoundError(f"Notebook not found: {path}")
    return nbformat.read(path, as_version=4)


def code_cells(nb: nbformat.NotebookNode) -> list:
    """Return the notebook's code cells in document order."""
    return [cell for cell in nb.cells if cell.cell_type == "code"]


def notebook_source(nb: nbformat.NotebookNode) -> str:
    """Concatenate the notebook's code cell sources into one parseable string.

    pip-install cells are excluded: they are shell syntax, not Python, and would
    make `ast.parse` fail.
    """
    return "\n".join(cell.source for cell in code_cells(nb) if not is_pip_cell(cell))


def is_pip_cell(cell) -> bool:
    """True if the cell is nothing but pip install invocations."""
    return cell.cell_type == "code" and bool(PIP_CELL_RE.search(cell.source))


def extract_dict_literal(source: str, name: str) -> dict:
    """Return the value of a top-level `name = {...}` assignment in `source`.

    Raises:
        ValueError: if no such assignment exists or its value is not a literal.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise ValueError(f"No literal dict assignment named {name!r} found in notebook source.")


def extract_all_dict_literals(source: str, name: str) -> list:
    """Return the value of every `name = {...}` assignment in `source`, at any depth.

    Used where a notebook repeats the same dict (e.g. connection details
    redefined inside a function), so the copies can be checked for agreement.

    Raises:
        ValueError: if `name` is never assigned a dict literal.
    """
    tree = ast.parse(source)
    values = [
        ast.literal_eval(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Dict)
        and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
    ]
    if not values:
        raise ValueError(f"No literal dict assignment named {name!r} found in notebook source.")
    return values


def extract_str_assignments(source: str, name: str) -> list:
    """Return every string literal assigned to `name`, in document order.

    Raises:
        ValueError: if `name` is never assigned a string literal.
    """
    tree = ast.parse(source)
    values = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
        ):
            values.append(node.value.value)
    if not values:
        raise ValueError(f"No string assignment named {name!r} found in notebook source.")
    return values


def extract_last_str_assignment(source: str, name: str) -> str:
    """Return the final string literal assigned to `name`."""
    return extract_str_assignments(source, name)[-1]


# ----------------------------------------------------------------------
# Notebook execution
# ----------------------------------------------------------------------


def cell_errors(cell) -> list:
    """Return the error outputs of an executed cell."""
    return [out for out in cell.get("outputs", []) if out.output_type == "error"]


def cell_text(cell) -> str:
    """Return all stdout / text-ish output of an executed cell as one string."""
    chunks = []
    for out in cell.get("outputs", []):
        if out.output_type == "stream":
            chunks.append(out.text)
        elif out.output_type in ("execute_result", "display_data"):
            chunks.append(out.get("data", {}).get("text/plain", ""))
        elif out.output_type == "error":
            chunks.append("\n".join(out.get("traceback", [])))
    return "\n".join(chunks)


def format_cell_error(cell, index: int) -> str:
    """Build a readable failure message for a cell that raised."""
    error = cell_errors(cell)[0]
    source = cell.source.strip()
    if len(source) > 800:
        source = source[:800] + "\n... (truncated)"
    return (
        f"Cell {index} (id={cell.get('id')}) raised "
        f"{error.ename}: {error.evalue}\n"
        f"--- source ---\n{source}\n"
        f"--- traceback ---\n" + "\n".join(error.get("traceback", []))
    )


def execute_notebook(path: Path, skip_pip: bool = True) -> nbformat.NotebookNode:
    """Execute a notebook in its own directory and return the executed notebook.

    Errors are collected rather than raised (`allow_errors=True`) so that the
    tests can report every failing cell with its traceback, instead of stopping
    at the first one.
    """
    nb = read_notebook(path)
    if skip_pip:
        nb.cells = [cell for cell in nb.cells if not is_pip_cell(cell)]

    total = len(nb.cells)
    started = time.monotonic()

    def report_cell_start(cell, cell_index, **_):
        # Written to the real stderr so it shows through pytest's output capture:
        # some notebooks spend minutes waiting on external APIs.
        if cell.cell_type != "code":
            return
        elapsed = time.monotonic() - started
        lines = cell.source.strip().splitlines()
        first_line = lines[0][:70] if lines else "(empty cell)"
        sys.__stderr__.write(
            f"[{path.name}] cell {cell_index + 1}/{total} (+{elapsed:.0f}s) {first_line}\n"
        )
        sys.__stderr__.flush()

    client = NotebookClient(
        nb,
        timeout=KERNEL_TIMEOUT_SECONDS,
        kernel_name="python3",
        allow_errors=True,
        resources={"metadata": {"path": str(path.parent)}},
        on_cell_start=report_cell_start,
    )
    client.execute()
    sys.__stderr__.write(f"[{path.name}] finished in {time.monotonic() - started:.0f}s\n")
    return nb


def assert_no_cell_errors(nb: nbformat.NotebookNode, allowed_error_cell_ids=frozenset()):
    """Fail if any executed code cell raised, unless its id is explicitly allowed.

    Args:
        nb: An executed notebook.
        allowed_error_cell_ids: Cell ids the tutorial deliberately shows failing.
    """
    failures = []
    for index, cell in enumerate(code_cells(nb)):
        if not cell_errors(cell):
            continue
        if cell.get("id") in allowed_error_cell_ids:
            continue
        failures.append(format_cell_error(cell, index))
    if failures:
        raise AssertionError(
            f"{len(failures)} cell(s) raised while executing the notebook:\n\n"
            + "\n\n".join(failures)
        )


def find_cell(nb: nbformat.NotebookNode, needle: str):
    """Return the first code cell whose source contains `needle`.

    Raises:
        ValueError: if no cell matches -- the notebook has changed shape and the
                    test's assumptions no longer hold.
    """
    for cell in code_cells(nb):
        if needle in cell.source:
            return cell
    raise ValueError(f"No code cell containing {needle!r} found in notebook.")


# ----------------------------------------------------------------------
# IRIS
# ----------------------------------------------------------------------


def run_query(connection_args: dict, sql: str, params=()) -> list:
    """Run a query and return all rows as tuples.

    The cursor is closed before the connection: leaving a cursor that fetched a
    long text column open when the connection closes crashes the driver on
    teardown (see Tutorials/5-ai/BUG_REPORT.md).
    """
    conn = iris.connect(**connection_args)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, list(params))
        rows = [tuple(row) for row in cursor.fetchall()]
        cursor.close()
        return rows
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture(scope="session")
def nb_2_1_source() -> str:
    """Unexecuted code source of notebook 2.1."""
    return notebook_source(read_notebook(NOTEBOOK_2_1))


@pytest.fixture(scope="session")
def nb_3_1_source() -> str:
    """Unexecuted code source of notebook 3.1."""
    return notebook_source(read_notebook(NOTEBOOK_3_1))


@pytest.fixture(scope="session")
def iris_connection_args(nb_2_1_source) -> dict:
    """The `connection_args` dict as written in notebook 2.1."""
    return extract_dict_literal(nb_2_1_source, "connection_args")


@pytest.fixture(scope="session")
def fhir_config(nb_3_1_source) -> dict:
    """The FHIR base URL and credentials as written in notebook 3.1."""
    return {
        "server_url": extract_last_str_assignment(nb_3_1_source, "server_url"),
        "base_url": extract_last_str_assignment(nb_3_1_source, "baseURL"),
        "username": extract_last_str_assignment(nb_3_1_source, "username"),
        "password": extract_last_str_assignment(nb_3_1_source, "password"),
    }


@pytest.fixture(scope="session")
def nb_vector_search_source() -> str:
    """Unexecuted code source of the vector search notebook."""
    return notebook_source(read_notebook(NOTEBOOK_VECTOR_SEARCH))


@pytest.fixture(scope="session")
def nb_agents_source() -> str:
    """Unexecuted code source of the agents and tools notebook."""
    return notebook_source(read_notebook(NOTEBOOK_AGENTS))
