"""Tests for Tutorials/3-fhir/3.4-create-transaction-bundles.ipynb.

Needs a running FHIR server with at least one Patient (loaded by the docker setup
or by notebook 3.1): the notebook looks up the first patient to refer to.
"""

import re

import pytest
import requests
from requests.auth import HTTPBasicAuth

from conftest import (
    NOTEBOOK_3_4,
    assert_no_cell_errors,
    cell_text,
    execute_notebook,
    extract_last_str_assignment,
    find_cell,
)

REQUEST_TIMEOUT_SECONDS = 60
ENCOUNTER_REFERENCE_RE = re.compile(r'"reference": "Encounter/(\d+)"')


class TestNotebookStructure:
    def test_dependencies_importable(self):
        pytest.importorskip("requests", reason="requests is not installed")
        pytest.importorskip(
            "fhir.resources.R4B",
            reason="fhir.resources is not installed (pip install fhir.resources)",
        )

    def test_base_url_matches_notebook_3_3(self, nb_3_3_source, nb_3_4_source):
        assert extract_last_str_assignment(nb_3_4_source, "baseURL") == extract_last_str_assignment(
            nb_3_3_source, "baseURL"
        )


@pytest.fixture(scope="module")
def executed():
    """Notebook 3.4 executed once, shared by every execution-dependent test."""
    pytest.importorskip(
        "fhir.resources.R4B",
        reason="fhir.resources is required to execute 3.4 (pip install fhir.resources)",
    )
    return execute_notebook(NOTEBOOK_3_4)


class TestNotebookExecution:
    def test_no_cell_raises(self, executed):
        assert_no_cell_errors(executed)

    def test_transaction_post_returns_200(self, executed):
        cell = find_cell(executed, "requests.post(baseURL")
        assert "<Response [200]>" in cell_text(cell)

    def test_response_is_a_transaction_response_with_two_created_entries(self, executed):
        cell = find_cell(executed, "json.dumps(res.json()")
        text = cell_text(cell)
        assert '"type": "transaction-response"' in text, f"Not a transaction-response:\n{text[:1000]}"
        statuses = re.findall(r'"status": "(\d+)', text)
        assert len(statuses) == 2 and all(s == "201" for s in statuses), (
            f"Expected two entries with status 201, got {statuses}.\n{text[:1000]}"
        )

    def test_observation_refers_to_a_real_encounter_id(self, executed):
        text = cell_text(find_cell(executed, "obs_url = "))
        assert ENCOUNTER_REFERENCE_RE.search(text), (
            f"The Observation does not reference a real Encounter id. Got:\n{text[:1000]}"
        )
        assert "urn:uuid" not in text, "The Observation still refers to a urn:uuid placeholder."


class TestCreatedDataVisibleOnServer:
    def test_encounter_exists_on_the_server(self, executed, fhir_config):
        text = cell_text(find_cell(executed, "obs_url = "))
        encounter_id = ENCOUNTER_REFERENCE_RE.search(text).group(1)
        res = requests.get(
            fhir_config["base_url"] + f"Encounter/{encounter_id}",
            headers={"Accept": "application/fhir+json"},
            auth=HTTPBasicAuth(fhir_config["username"], fhir_config["password"]),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        assert res.status_code == 200, f"Encounter/{encounter_id} not found: {res.status_code}"
        assert res.json()["resourceType"] == "Encounter"
