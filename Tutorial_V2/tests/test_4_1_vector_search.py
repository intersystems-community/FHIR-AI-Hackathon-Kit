"""Tests for Tutorial_V2/4-ai/vector-search.ipynb.

Layered like the 2.x tests, cheapest first:

* `TestConnectionDetails` -- the IRIS connection details written in the
  notebook (twice: once at the top, once inside `vector_search_diabetes_text`)
  agree with each other and are accepted by the running instance.
* `TestNotebookStructure` -- the PDFs the notebook chunks exist, the vector
  column width matches the embedding model, and the OpenAI key is configured.
* `TestNotebookExecution` -- the notebook runs top to bottom, each search
  returns the text the narrative describes, and afterwards the
  `Diabetes.VectorStore` table holds every raw text and every chunk of every PDF
  under the right `Source`.

Executing this module DROPS and rebuilds `Diabetes.VectorStore` (the notebook's
first code cell does so) and makes several hundred OpenAI embedding calls. The
agents-and-tools tests (test_4_2) read that table, so this module is numbered to
run first.
"""

import os
import re

import pytest
from dotenv import dotenv_values

from conftest import (
    AI_DIR,
    NOTEBOOK_VECTOR_SEARCH,
    VECTOR_TABLE,
    assert_no_cell_errors,
    cell_text,
    execute_notebook,
    extract_all_dict_literals,
    find_cell,
    read_notebook,
    run_query,
)

PAPERS_DIR = AI_DIR / "papers"
RAW_TEXT_SOURCE = "Raw_text"

# Documented dimension of OpenAI's text-embedding-3-small.
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def notebook_pdf_paths() -> list:
    """The PDF paths exactly as the notebook builds them (relative to 4-ai/)."""
    return ["papers/" + name for name in os.listdir(PAPERS_DIR) if name[-4:] == ".pdf"]


@pytest.fixture(scope="module")
def connection_args(nb_vector_search_source) -> dict:
    """The top-level `connection_args` dict written in the notebook."""
    return extract_all_dict_literals(nb_vector_search_source, "connection_args")[0]


@pytest.fixture(scope="module")
def get_chunks():
    """The notebook's own `get_chunks` function, so expected chunk counts use its logic."""
    cell = find_cell(read_notebook(NOTEBOOK_VECTOR_SEARCH), "def get_chunks")
    namespace = {}
    exec(cell.source, namespace)
    return namespace["get_chunks"]


class TestConnectionDetails:
    """The IRIS connection details written into the notebook must be valid."""

    def test_connection_args_copies_agree(self, nb_vector_search_source):
        """The search function redefines connection_args; it must match the top-level copy."""
        copies = extract_all_dict_literals(nb_vector_search_source, "connection_args")
        assert len(copies) >= 2, (
            "Expected connection_args at the top of the notebook and inside "
            f"vector_search_diabetes_text; found {len(copies)}."
        )
        assert all(copy == copies[0] for copy in copies), (
            f"The notebook's connection_args copies disagree: {copies}"
        )

    def test_connection_is_accepted(self, connection_args):
        """Catches a changed superserver port, namespace or password."""
        try:
            rows = run_query(connection_args, "SELECT 1")
        except Exception as exc:
            pytest.fail(
                f"Could not connect with the notebook's connection_args {connection_args}.\n"
                "Check the container is running and the superserver port mapping in "
                f"docker-iris-fhir/docker-compose.yml.\nError: {exc}"
            )
        assert rows == [(1,)]

    def test_iris_supports_vector_functions(self, connection_args):
        """VECTOR_COSINE / TO_VECTOR must be available on this IRIS version."""
        rows = run_query(
            connection_args,
            "SELECT VECTOR_COSINE(TO_VECTOR('1,0', DOUBLE), TO_VECTOR('1,0', DOUBLE))",
        )
        assert float(rows[0][0]) == pytest.approx(1.0)


class TestNotebookStructure:
    """The notebook's local inputs exist and its constants are consistent."""

    def test_dependencies_importable(self):
        pytest.importorskip("openai", reason="openai is not installed (pip install openai)")
        pytest.importorskip("pymupdf", reason="pymupdf is not installed (pip install pymupdf)")
        pytest.importorskip("dotenv", reason="python-dotenv is not installed")

    def test_openai_api_key_is_configured(self):
        """The notebook calls load_dotenv() from 4-ai/, so the key must be in 4-ai/.env."""
        env_file = AI_DIR / ".env"
        assert env_file.exists(), (
            f"{env_file} does not exist. The notebook loads OPENAI_API_KEY from it."
        )
        assert dotenv_values(env_file)["OPENAI_API_KEY"], (
            f"OPENAI_API_KEY in {env_file} is empty."
        )

    def test_papers_directory_contains_pdfs(self):
        pdfs = notebook_pdf_paths()
        assert pdfs, f"No PDFs found in {PAPERS_DIR}; the chunking section has nothing to read."

    def test_every_pdf_yields_chunks(self, get_chunks):
        """A scanned/empty PDF would produce zero chunks and silently add nothing."""
        empty = []
        for pdf in notebook_pdf_paths():
            _, chunks = get_chunks(str(AI_DIR / pdf))
            if not chunks:
                empty.append(pdf)
        assert not empty, f"These PDFs produced no text chunks: {empty}"

    def test_vector_column_width_matches_embedding_model(self, nb_vector_search_source):
        """The VECTOR(DOUBLE, n) column must match the embedding model's output size."""
        match = re.search(r"VECTOR\(\s*DOUBLE\s*,\s*(\d+)\s*\)", nb_vector_search_source)
        assert match, "No VECTOR(DOUBLE, n) column definition found in the notebook."
        assert int(match.group(1)) == EMBEDDING_DIMENSIONS, (
            f"The table is created with VECTOR(DOUBLE, {match.group(1)}) but "
            f"{EMBEDDING_MODEL} returns {EMBEDDING_DIMENSIONS} dimensions."
        )

    def test_one_embedding_model_is_used_throughout(self, nb_vector_search_source):
        """Stored and query embeddings must come from the same model to be comparable."""
        models = set(re.findall(r'model\s*=\s*"([^"]+)"', nb_vector_search_source))
        assert models == {EMBEDDING_MODEL}, (
            f"Expected every embedding call to use {EMBEDDING_MODEL!r}; found {models}."
        )


@pytest.fixture(scope="module")
def executed():
    """The notebook executed once, shared by every execution-dependent test."""
    pytest.importorskip("openai", reason="openai is required to execute the notebook")
    pytest.importorskip("pymupdf", reason="pymupdf is required to execute the notebook")
    return execute_notebook(NOTEBOOK_VECTOR_SEARCH)


class TestNotebookExecution:
    """Execute the notebook end to end and check its outputs."""

    def test_no_cell_raises(self, executed):
        assert_no_cell_errors(executed)

    def test_embedding_has_documented_dimensions(self, executed):
        cell = find_cell(executed, "print(len(embeddings[0]))")
        text = cell_text(cell)
        assert re.search(rf"^{EMBEDDING_DIMENSIONS}\s*$", text, re.MULTILINE), (
            f"Expected the embedding length {EMBEDDING_DIMENSIONS} to be printed. Got:\n{text}"
        )

    def test_first_row_readback_shows_raw_text(self, executed):
        cell = find_cell(executed, "WHERE ID=1")
        text = cell_text(cell)
        assert f"Source: {RAW_TEXT_SOURCE}" in text, f"Unexpected first-row output:\n{text}"
        assert "Text: Managing blood glucose levels" in text, f"Unexpected first-row output:\n{text}"

    def test_exercise_query_finds_physical_activity_text(self, executed):
        """The narrative's point: a match with no keywords in common."""
        cell = find_cell(executed, 'prompt = "Is exercise good for diabetes?"')
        text = cell_text(cell)
        assert "Regular physical activity" in text, (
            f"The exercise query did not return the physical activity text. Got:\n{text}"
        )

    def test_search_function_finds_high_glucose_symptoms(self, executed):
        cell = find_cell(executed, "def vector_search_diabetes_text")
        text = cell_text(cell)
        assert f"'Source': '{RAW_TEXT_SOURCE}'" in text and "Frequent thirst" in text, (
            f"vector_search_diabetes_text did not return the thirst/urination text. Got:\n{text}"
        )

    def test_sweat_glucose_query_cites_glucose_sensing_paper(self, executed):
        cell = find_cell(executed, "sweat of healthy patients")
        text = cell_text(cell)
        assert "Source: papers/GlucoseSensingForDiabetesMonitoring.pdf" in text, (
            f"Expected the glucose sensing paper as the source. Got:\n{text[:1500]}"
        )

    def test_combination_therapy_query_cites_multi_target_drugs_paper(self, executed):
        cell = find_cell(executed, "combination therapy")
        text = cell_text(cell)
        assert "Source: papers/Type2DiabetesMellitusReviewOfMultiTargetDrugs.pdf" in text, (
            f"Expected the multi-target drugs review as the source. Got:\n{text[:1500]}"
        )


class TestVectorStoreContents:
    """After execution, the table must hold exactly what the notebook set out to insert.

    Depends on `executed` so the notebook has rebuilt the table first.
    """

    @pytest.fixture(scope="class")
    def rows_per_source(self, executed, connection_args) -> dict:
        # %EXACT: Source uses the default case-insensitive collation, which would
        # otherwise upper-case the grouped values.
        rows = run_query(
            connection_args,
            f"SELECT %EXACT(Source), COUNT(*) FROM {VECTOR_TABLE} GROUP BY %EXACT(Source)",
        )
        return {source: count for source, count in rows}

    def test_all_raw_texts_inserted(self, rows_per_source):
        cell = find_cell(read_notebook(NOTEBOOK_VECTOR_SEARCH), "diabetes_texts = [")
        namespace = {}
        exec(cell.source, namespace)
        expected = len(namespace["diabetes_texts"])
        assert rows_per_source[RAW_TEXT_SOURCE] == expected, (
            f"Expected {expected} {RAW_TEXT_SOURCE!r} rows, found "
            f"{rows_per_source[RAW_TEXT_SOURCE]}."
        )

    def test_every_pdf_is_a_source(self, rows_per_source):
        """Each paper must be stored under its own Source, not only the last one read."""
        missing = sorted(set(notebook_pdf_paths()) - set(rows_per_source))
        assert not missing, (
            f"These PDFs have no rows in {VECTOR_TABLE}: {missing}.\n"
            f"Sources present: {rows_per_source}"
        )

    def test_every_pdf_chunk_is_inserted_once(self, rows_per_source, get_chunks):
        """Row count per PDF must equal the number of chunks get_chunks makes for it."""
        wrong = {}
        for pdf in notebook_pdf_paths():
            _, chunks = get_chunks(str(AI_DIR / pdf))
            # A source absent from the GROUP BY genuinely has zero rows.
            stored = rows_per_source.get(pdf, 0)
            if stored != len(chunks):
                wrong[pdf] = {"chunks": len(chunks), "rows": stored}
        assert not wrong, f"Per-PDF row counts do not match chunk counts: {wrong}"

    def test_no_unexpected_sources(self, rows_per_source):
        expected = {RAW_TEXT_SOURCE, *notebook_pdf_paths()}
        extra = sorted(set(rows_per_source) - expected)
        assert not extra, f"Unexpected Source values in {VECTOR_TABLE}: {extra}"
