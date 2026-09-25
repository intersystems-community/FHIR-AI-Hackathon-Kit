"""Tests for Tutorial_V2/4-ai/agents-and-tools.ipynb.

The notebook gives an LLM agent three tools that read data loaded by earlier
tutorials, so on top of the usual layers there is a prerequisites layer:

* `TestConnectionDetails` -- the IRIS connection details and FHIR URL /
  credentials written into the tool functions are accepted by the servers.
* `TestNotebookStructure` -- dependencies, the OpenAI key, and the
  deterministic base64 helpers.
* `TestPrerequisiteData` -- the data each tool reads exists: `Sample.Person`
  (from 2.1), `Diabetes.VectorStore` (from vector-search.ipynb) and the Synthea
  patient Tish Lemke with a body height Observation (from 2.2). `Sample.Person`
  is rebuilt by 2.1's `setup_csv_data.py` before this module runs; for the
  others, a failure here means an earlier notebook needs running, not that this
  one is broken.
* `TestToolsDirectly` -- each tool function, called without an LLM, returns
  what the agent will need.
* `TestNotebookExecution` -- the notebook runs top to bottom and each agent
  answer is grounded in the real data. LLM output varies run to run, so these
  assert on facts (the tool was called, the true height / age appears) rather
  than on exact wording.
"""

import subprocess
import sys

import pytest
import requests
from dotenv import dotenv_values
from requests.auth import HTTPBasicAuth

from conftest import (
    AI_DIR,
    LOADING_DATA_DIR,
    NOTEBOOK_AGENTS,
    VECTOR_TABLE,
    assert_no_cell_errors,
    cell_text,
    execute_notebook,
    extract_all_dict_literals,
    extract_dict_literal,
    extract_last_str_assignment,
    find_cell,
    read_notebook,
    run_query,
)

REQUEST_TIMEOUT_SECONDS = 60

# The patient and hero the notebook's example prompts ask about.
FHIR_PATIENT_GIVEN = "Tish"
FHIR_PATIENT_FAMILY = "Lemke"
BODY_HEIGHT_LOINC = "http://loinc.org|8302-2"
SPIDERMAN_LAST_NAME = "Parker"

# Skip-setup script that recreates the tables 2.1 builds. test_2_1 drops those
# tables when it finishes, so this module rebuilds them before reading them.
SETUP_CSV_DATA_SCRIPT = LOADING_DATA_DIR / "setup_csv_data.py"


@pytest.fixture(scope="module", autouse=True)
def csv_tables_loaded():
    """Run 2.1's skip-setup script so Sample.Person exists for the SQL tool."""
    subprocess.run([sys.executable, str(SETUP_CSV_DATA_SCRIPT)], check=True)


def cell_namespace(*needles: str) -> dict:
    """Exec the notebook cells containing each of `needles`, in order, in one namespace.

    Lets the tests call the notebook's own tool functions without an LLM. Pass
    every cell the tool depends on (e.g. the one defining CONNECTION_ARGS).
    """
    nb = read_notebook(NOTEBOOK_AGENTS)
    namespace = {}
    for needle in needles:
        exec(find_cell(nb, needle).source, namespace)
    return namespace


@pytest.fixture(scope="module")
def connection_args(nb_agents_source) -> dict:
    """The CONNECTION_ARGS dict the SQL and vector tools use."""
    return extract_dict_literal(nb_agents_source, "CONNECTION_ARGS")


@pytest.fixture(scope="module")
def fhir_config(nb_agents_source) -> dict:
    """The FHIR base URL and credentials hard-coded in the fhir_query tool."""
    return {
        "base_url": extract_last_str_assignment(nb_agents_source, "base_url"),
        "username": extract_last_str_assignment(nb_agents_source, "username"),
        "password": extract_last_str_assignment(nb_agents_source, "password"),
    }


def fhir_get(fhir_config: dict, path: str) -> requests.Response:
    """GET `path` from the FHIR server using the notebook's URL and credentials."""
    return requests.get(
        fhir_config["base_url"] + path,
        headers={"Accept": "application/fhir+json"},
        auth=HTTPBasicAuth(fhir_config["username"], fhir_config["password"]),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


def latest_height_cm(fhir_config: dict) -> float:
    """The most recent body height recorded for Tish Lemke, straight from FHIR."""
    patients = fhir_get(
        fhir_config, f"Patient?given={FHIR_PATIENT_GIVEN}&family={FHIR_PATIENT_FAMILY}"
    ).json()
    if patients["total"] != 1:
        raise ValueError(
            f"Expected exactly one Patient {FHIR_PATIENT_GIVEN} {FHIR_PATIENT_FAMILY}, "
            f"found {patients['total']}."
        )
    patient_id = patients["entry"][0]["resource"]["id"]
    observations = fhir_get(
        fhir_config,
        f"Observation?patient={patient_id}&code={BODY_HEIGHT_LOINC}&_sort=-date&_count=1",
    ).json()
    if observations["total"] == 0:
        raise ValueError(f"Patient/{patient_id} has no body height Observation.")
    quantity = observations["entry"][0]["resource"]["valueQuantity"]
    if quantity["unit"] != "cm":
        raise ValueError(f"Expected height in cm, got {quantity['unit']!r}.")
    return quantity["value"]


def parker_ages(connection_args: dict) -> set:
    """Every age stored for a Parker in Sample.Person (2.1 inserts more than one)."""
    rows = run_query(
        connection_args,
        "SELECT Age FROM Sample.Person WHERE LastName = ?",
        [SPIDERMAN_LAST_NAME],
    )
    return {row[0] for row in rows}


class TestConnectionDetails:
    """Connection details hard-coded in the tool functions must be valid."""

    def test_connection_args_match_vector_search_notebook(
        self, connection_args, nb_vector_search_source
    ):
        """The agent reads the vector table the other notebook wrote; same instance."""
        vector_args = extract_all_dict_literals(nb_vector_search_source, "connection_args")[0]
        assert connection_args == vector_args, (
            f"agents-and-tools CONNECTION_ARGS {connection_args} differ from "
            f"vector-search connection_args {vector_args}."
        )

    def test_iris_connection_is_accepted(self, connection_args):
        try:
            rows = run_query(connection_args, "SELECT 1")
        except Exception as exc:
            pytest.fail(
                f"Could not connect with CONNECTION_ARGS {connection_args}.\n"
                "Check the container is running and the superserver port mapping in "
                f"docker-iris-fhir/docker-compose.yml.\nError: {exc}"
            )
        assert rows == [(1,)]

    def test_fhir_base_url_and_credentials_work(self, fhir_config):
        try:
            res = fhir_get(fhir_config, "metadata")
        except requests.RequestException as exc:
            pytest.fail(
                f"Could not reach the fhir_query base_url {fhir_config['base_url']!r}.\n"
                f"Check the web server port mapping in docker-compose.yml.\nError: {exc}"
            )
        assert res.status_code == 200, (
            f"GET {fhir_config['base_url']}metadata returned {res.status_code} "
            f"(401 = bad credentials, 404 = wrong endpoint path).\nBody: {res.text[:500]}"
        )
        assert res.json()["resourceType"] == "CapabilityStatement"


class TestNotebookStructure:

    def test_dependencies_importable(self):
        pytest.importorskip("langchain", reason='pip install langchain "langchain[openai]"')
        pytest.importorskip("langchain_openai", reason='pip install "langchain[openai]"')
        pytest.importorskip("openai", reason="pip install openai")
        pytest.importorskip("dotenv", reason="pip install python-dotenv")

    def test_openai_api_key_is_configured(self):
        env_file = AI_DIR / ".env"
        assert env_file.exists(), (
            f"{env_file} does not exist. The notebook loads OPENAI_API_KEY from it."
        )
        assert dotenv_values(env_file)["OPENAI_API_KEY"], f"OPENAI_API_KEY in {env_file} is empty."

    def test_base64_helpers_round_trip_the_test_string(self, nb_agents_source):
        """The decode helper is the evaluation of the agent; it must invert encode exactly."""
        helpers = cell_namespace("def base64_encode")
        test_string = extract_last_str_assignment(nb_agents_source, "test_string")
        encoded = helpers["base64_encode"](test_string)
        assert helpers["base64_decode"](encoded) == test_string


class TestPrerequisiteData:
    """Data loaded by earlier notebooks, which the agent's tools read."""

    def test_sample_person_table_has_spiderman(self, connection_args):
        try:
            ages = parker_ages(connection_args)
        except Exception as exc:
            pytest.fail(
                "Could not read Sample.Person. Run 2-loading-data/2.1-load-csv-data.ipynb "
                f"first; the search_superheros tool reads it.\nError: {exc}"
            )
        assert ages, (
            f"Sample.Person has no {SPIDERMAN_LAST_NAME} row. Run 2.1 to load it; the "
            "'How old is Spiderman?' prompt depends on it."
        )

    def test_vector_store_is_populated(self, connection_args):
        try:
            rows = run_query(connection_args, f"SELECT COUNT(*) FROM {VECTOR_TABLE}")
        except Exception as exc:
            pytest.fail(
                f"Could not read {VECTOR_TABLE}. Run 4-ai/vector-search.ipynb (or "
                f"4-ai/setup_vector_store.py) first.\nError: {exc}"
            )
        assert rows[0][0] > 0, f"{VECTOR_TABLE} is empty."

    def test_fhir_patient_has_a_height_observation(self, fhir_config):
        try:
            height = latest_height_cm(fhir_config)
        except ValueError as exc:
            pytest.fail(
                "The 'How tall is Tish Lemke?' prompt needs the Synthea data from "
                f"2-loading-data/2.2-load-fhir-data.ipynb.\n{exc}"
            )
        assert height > 0


class TestToolsDirectly:
    """Call each tool function as the agent would, with no LLM involved."""

    @pytest.fixture(autouse=True)
    def notebook_env(self, monkeypatch):
        # The cells' load_dotenv() finds 4-ai/.env when run in the notebook, but
        # under exec it searches from this test file's directory instead. Load
        # the notebook's .env explicitly so the tools see the same key.
        monkeypatch.setenv("OPENAI_API_KEY", dotenv_values(AI_DIR / ".env")["OPENAI_API_KEY"])

    def test_search_superheros_returns_name_and_age_rows(self):
        rows = cell_namespace("def search_superheros")["search_superheros"]()
        assert rows, "search_superheros returned no rows."
        assert all(len(row) == 3 for row in rows), f"Expected (FirstName, LastName, Age) rows: {rows}"
        assert any(row[1] == SPIDERMAN_LAST_NAME for row in rows), (
            f"No {SPIDERMAN_LAST_NAME} in search_superheros output: {rows}"
        )

    def test_vector_search_tool_returns_relevant_text(self):
        tool = cell_namespace("CONNECTION_ARGS = {", "def vector_search_diabetes_text")[
            "vector_search_diabetes_text"
        ]
        result = tool("Is exercise good for diabetes?")
        assert isinstance(result, str) and result, f"Expected non-empty text, got {result!r}"

    def test_fhir_query_tool_finds_the_patient(self):
        fhir_query = cell_namespace("def fhir_query")["fhir_query"]
        body = fhir_query("Patient", f"family={FHIR_PATIENT_FAMILY}&given={FHIR_PATIENT_GIVEN}")
        assert body["resourceType"] == "Bundle", f"fhir_query did not return a Bundle: {body}"
        assert body["total"] >= 1, f"fhir_query found no {FHIR_PATIENT_GIVEN} {FHIR_PATIENT_FAMILY}."


@pytest.fixture(scope="module")
def executed():
    """The notebook executed once, shared by every execution-dependent test."""
    pytest.importorskip("langchain_openai", reason="langchain_openai is required to execute")
    return execute_notebook(NOTEBOOK_AGENTS)


def final_answer(cell) -> str:
    """The agent's final reply, which the prompt cells print after two blank lines."""
    text = cell_text(cell)
    marker = "\n\n "
    if marker not in text:
        raise ValueError(f"No final answer found in cell output:\n{text[:2000]}")
    return text.split(marker, 1)[1]


class TestNotebookExecution:
    """Execute the notebook and check each agent answer against the real data."""

    def test_no_cell_raises(self, executed):
        assert_no_cell_errors(executed)

    def test_api_key_found(self, executed):
        cell = find_cell(executed, 'os.environ["OPENAI_API_KEY"]')
        assert "API key Found" in cell_text(cell)

    def test_agent_with_tool_calls_base64_encode(self, executed):
        cell = find_cell(executed, "agent_with_tool.invoke")
        text = cell_text(cell)
        assert "Tool Message" in text and "base64_encode" in text, (
            f"The trace does not show the agent calling base64_encode:\n{text[:2000]}"
        )

    def test_agent_with_tool_encodes_exactly(self, executed, nb_agents_source):
        """The tutorial's claim: with the tool, the encoding is perfect.

        Trailing whitespace is ignored: test_string ends the prompt, and the model
        strips that trailing space before passing the text to the tool.
        """
        test_string = extract_last_str_assignment(nb_agents_source, "test_string")
        cell = find_cell(executed, "agent_with_tool.invoke")
        decoded = cell_text(cell).split("Decoding the final response gives: \n\n", 1)[1]
        assert decoded.rstrip() == test_string.rstrip(), (
            f"Decoded tool-assisted answer differs from the original.\n"
            f"Expected: {test_string!r}\nGot:      {decoded!r}"
        )

    def test_fhir_prompt_calls_fhir_and_reports_true_height(self, executed, fhir_config):
        cell = find_cell(executed, "How tall is Tish Lemke")
        text = cell_text(cell)
        assert "Print calling FHIR Server at" in text, f"fhir_query was never called:\n{text[:2000]}"
        height = latest_height_cm(fhir_config)
        answer = final_answer(cell)
        assert f"{height:g}" in answer, (
            f"Expected the recorded height {height:g} cm in the answer. Got:\n{answer}"
        )

    def test_sql_prompt_calls_tool_and_reports_a_true_age(self, executed, connection_args):
        cell = find_cell(executed, "How old is Spiderman?")
        text = cell_text(cell)
        assert "Getting info on superheros" in text, f"search_superheros was never called:\n{text}"
        ages = parker_ages(connection_args)
        answer = final_answer(cell)
        assert any(str(age) in answer for age in ages), (
            f"Expected one of the stored Parker ages {sorted(ages)} in the answer. Got:\n{answer}"
        )

    def test_vector_prompt_uses_vector_search(self, executed):
        cell = find_cell(executed, "four major groups of anti-diabetic agents")
        text = cell_text(cell)
        assert "Performing Vector search" in text and "response from vector search" in text, (
            f"vector_search_diabetes_text was never called:\n{text[:2000]}"
        )
