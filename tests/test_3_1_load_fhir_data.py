"""Tests for Tutorials/3-fhir/3.1-load-fhir-data.ipynb.

Layered the same way as the 2.1 tests:

* `TestFhirEndpointAndCredentials` -- the base URL and basic-auth credentials
  written into the notebook actually reach a FHIR server. These are the tests
  that catch a changed web server port, a re-pointed FHIR endpoint path, or a
  changed IRIS password.
* `TestNotebookStructure` -- dependencies are importable and the notebook
  defines its variables before using them.
* `TestNotebookExecution` -- the notebook runs top to bottom with no cell
  raising, and the Synthea bundles it POSTs come back out of the server.
  Missing input files (Synthea bundles) surface here as cell errors.

3.1 only POSTs the Synthea bundles; the Bulk Load section is markdown and is not
executed. Creating resources and transaction bundles are covered by
test_3_3_create_fhir_resources.py and test_3_4_transaction_bundles.py.
"""

import re

import pytest
import requests
from requests.auth import HTTPBasicAuth

from conftest import (
    NOTEBOOK_3_1,
    assert_no_cell_errors,
    cell_text,
    code_cells,
    execute_notebook,
    find_cell,
    notebook_source,
    read_notebook,
)

REQUEST_TIMEOUT_SECONDS = 60


def fhir_get(fhir_config: dict, path: str) -> requests.Response:
    """GET `path` from the FHIR server using the notebook's URL and credentials."""
    return requests.get(
        fhir_config["base_url"] + path,
        headers={"Accept": "application/fhir+json"},
        auth=HTTPBasicAuth(fhir_config["username"], fhir_config["password"]),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


class TestFhirEndpointAndCredentials:
    """The FHIR endpoint and credentials written into notebook 3.1 must work."""

    def test_post_and_get_urls_agree(self, fhir_config):
        """3.1 sets `server_url`, 3.3 sets `baseURL`; they must match."""
        assert fhir_config["server_url"] == fhir_config["base_url"], (
            "The bundle-upload URL in 3.1 and the resource URL in 3.3 point at different "
            f"servers: {fhir_config['server_url']!r} vs {fhir_config['base_url']!r}."
        )

    def test_base_url_is_reachable(self, fhir_config):
        """Catches a wrong host, a wrong web server port, or a stopped container."""
        try:
            res = fhir_get(fhir_config, "metadata")
        except requests.RequestException as exc:
            pytest.fail(
                f"Could not reach the FHIR base URL written in 3.1 "
                f"({fhir_config['base_url']!r}).\n"
                "Check the container is running and the web server port mapping in "
                f"docker-iris-fhir/docker-compose.yml.\nError: {exc}"
            )
        assert res.status_code != 404, (
            f"GET {fhir_config['base_url']}metadata returned 404. The FHIR endpoint "
            "path in the notebook does not exist on this server. Check the endpoint "
            "the FHIR server was installed at (docker-iris-fhir/fhir_server_setup.py)."
        )

    def test_credentials_are_accepted(self, fhir_config):
        """Catches a changed username/password -- IRIS answers 401 for bad basic auth."""
        res = fhir_get(fhir_config, "metadata")
        assert res.status_code != 401, (
            f"The FHIR server rejected the credentials written in 3.1 "
            f"(username={fhir_config['username']!r}). Update the notebook or the "
            "IRIS user's password."
        )

    def test_metadata_returns_a_capability_statement(self, fhir_config):
        """A working FHIR endpoint returns a CapabilityStatement from /metadata."""
        res = fhir_get(fhir_config, "metadata")
        assert res.status_code == 200, (
            f"GET {fhir_config['base_url']}metadata returned {res.status_code}.\n"
            f"Body: {res.text[:500]}"
        )
        body = res.json()
        assert body["resourceType"] == "CapabilityStatement", (
            f"Expected a CapabilityStatement, got resourceType={body['resourceType']!r}."
        )

    def test_patient_search_returns_a_bundle(self, fhir_config):
        """The Patient endpoint the notebook reads from must answer a searchset Bundle."""
        res = fhir_get(fhir_config, "Patient?_count=1")
        assert res.status_code == 200, (
            f"GET {fhir_config['base_url']}Patient returned {res.status_code}.\n"
            f"Body: {res.text[:500]}"
        )
        body = res.json()
        assert body["resourceType"] == "Bundle"
        assert body["type"] == "searchset"


class TestNotebookStructure:
    """The notebook's dependencies are importable and its cells are self-consistent."""

    def test_dependencies_importable(self):
        pytest.importorskip("requests", reason="requests is not installed")

    def test_no_variable_is_used_before_it_is_assigned(self):
        """Catches the classic notebook bug of a cell depending on a later cell.

        Cells run in document order during the test, so a name that is only
        assigned further down the notebook is a genuine defect, not a false
        positive from out-of-order manual execution.
        """
        nb = read_notebook(NOTEBOOK_3_1)
        assigned = set(dir(__builtins__)) | {"__builtins__"}
        problems = []
        for index, cell in enumerate(code_cells(nb)):
            source = cell.source
            # Names assigned anywhere in this cell count as available to it.
            assigned |= set(re.findall(r"^\s*(\w+)\s*=[^=]", source, re.MULTILINE))
            assigned |= set(re.findall(r"^\s*(?:import|from)\s+(\w+)", source, re.MULTILINE))
            assigned |= set(re.findall(r"\bimport\s+(?:\w+\s+as\s+)?(\w+)", source))
            assigned |= set(re.findall(r"^\s*(?:def|class)\s+(\w+)", source, re.MULTILINE))
            assigned |= set(re.findall(r"\bfor\s+([\w, ]+?)\s+in\b", source))
            for name in ("server_url", "endpoint", "username", "password"):
                if re.search(rf"\b{name}\b", source) and name not in assigned:
                    problems.append(
                        f"Cell {index} (id={cell.get('id')}) uses {name!r} before any "
                        "earlier cell assigns it."
                    )
        assert not problems, "\n".join(problems)


@pytest.fixture(scope="module")
def executed():
    """Notebook 3.1 executed once, shared by every execution-dependent test."""
    return execute_notebook(NOTEBOOK_3_1)


class TestNotebookExecution:
    """Execute 3.1 end to end and check its outputs against the server."""

    def test_no_unexpected_cell_raises(self, executed):
        assert_no_cell_errors(executed)

    def test_bundle_uploads_all_succeed(self, executed):
        """The upload loop prints one response per file; none may be an error status."""
        cell = find_cell(executed, "requests.post( server_url")
        text = cell_text(cell)
        statuses = [int(code) for code in re.findall(r"<Response \[(\d+)\]>", text)]
        assert statuses, f"The bundle upload loop printed no responses. Output:\n{text[:1000]}"
        bad = [code for code in statuses if code >= 300]
        assert not bad, (
            f"{len(bad)} of {len(statuses)} bundle uploads failed with status(es) {bad}.\n"
            f"Output:\n{text[:2000]}"
        )

    def test_patient_listing_shows_uploaded_synthea_patients(self, executed):
        """The check-the-upload cell should list patients from the Synthea bundles."""
        cell = find_cell(executed, "## Get the last 5 entries")
        text = cell_text(cell)
        assert "<Response [200]>" in text, f"Patient search did not return 200. Got:\n{text}"
        assert re.search(r"'family':", text), (
            f"No patient names were listed by the Patient search. Got:\n{text[:1000]}"
        )


class TestUploadedDataVisibleOnServer:
    """After executing the notebook, the data it uploaded must be queryable.

    Depends on the `executed` fixture so the notebook has actually run first.
    """

    def test_synthea_patients_are_on_the_server(self, executed, fhir_config):
        res = fhir_get(fhir_config, "Patient?family=Walsh511")
        assert res.status_code == 200, f"Patient search failed: {res.status_code} {res.text[:300]}"
        body = res.json()
        assert body["total"] >= 1, (
            "The Synthea patient 'Walsh511' from data/fhir is not on the server, so "
            "the bundle upload loop did not take effect."
        )
