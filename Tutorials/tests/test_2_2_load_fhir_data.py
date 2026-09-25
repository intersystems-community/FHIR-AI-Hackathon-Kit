"""Tests for Tutorial_V2/2-loading-data/2.2-load-fhir-data.ipynb.

Layered the same way as the 2.1 tests:

* `TestFhirEndpointAndCredentials` -- the base URL and basic-auth credentials
  written into the notebook actually reach a FHIR server. These are the tests
  that catch a changed web server port, a re-pointed FHIR endpoint path, or a
  changed IRIS password.
* `TestNotebookStructure` -- dependencies are importable and the notebook
  defines its variables before using them.
* `TestNotebookExecution` -- the notebook runs top to bottom with no unexpected
  cell raising, and the resources it POSTs come back out of the server.
  Missing input files (Synthea bundles, clinical note) surface here as cell
  errors.
"""

import re

import pytest
import requests
from requests.auth import HTTPBasicAuth

from conftest import (
    NOTEBOOK_2_2,
    assert_no_cell_errors,
    cell_text,
    code_cells,
    execute_notebook,
    find_cell,
    notebook_source,
    read_notebook,
)

REQUEST_TIMEOUT_SECONDS = 60

# The tutorial deliberately shows this cell failing: it calls res.json() on the
# empty body of a successful 201 POST to make the point that the error-inspection
# trick only works when there *is* an error.
DELIBERATE_ERROR_CELL_IDS = frozenset({"cb56dc36-ab6f-4b8f-baaa-f5be3a11e09b"})


def fhir_get(fhir_config: dict, path: str) -> requests.Response:
    """GET `path` from the FHIR server using the notebook's URL and credentials."""
    return requests.get(
        fhir_config["base_url"] + path,
        headers={"Accept": "application/fhir+json"},
        auth=HTTPBasicAuth(fhir_config["username"], fhir_config["password"]),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


class TestFhirEndpointAndCredentials:
    """The FHIR endpoint and credentials written into notebook 2.2 must work."""

    def test_post_and_get_urls_agree(self, fhir_config):
        """The notebook sets `server_url` and `baseURL` separately; they must match."""
        assert fhir_config["server_url"] == fhir_config["base_url"], (
            "The bundle-upload URL and the resource URL in 2.2 point at different "
            f"servers: {fhir_config['server_url']!r} vs {fhir_config['base_url']!r}."
        )

    def test_base_url_is_reachable(self, fhir_config):
        """Catches a wrong host, a wrong web server port, or a stopped container."""
        try:
            res = fhir_get(fhir_config, "metadata")
        except requests.RequestException as exc:
            pytest.fail(
                f"Could not reach the FHIR base URL written in 2.2 "
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
            f"The FHIR server rejected the credentials written in 2.2 "
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

    def test_documentreference_search_endpoint_works(self, fhir_config):
        """The notebook reads DocumentReference back by patient reference."""
        res = fhir_get(fhir_config, "DocumentReference?_count=1")
        assert res.status_code == 200, (
            f"GET {fhir_config['base_url']}DocumentReference returned "
            f"{res.status_code}.\nBody: {res.text[:500]}"
        )
        assert res.json()["resourceType"] == "Bundle"


class TestNotebookStructure:
    """The notebook's dependencies are importable and its cells are self-consistent."""

    def test_dependencies_importable(self):
        pytest.importorskip("requests", reason="requests is not installed")
        pytest.importorskip(
            "fhir.resources",
            reason="fhir.resources is not installed (pip install fhir.resources)",
        )

    def test_no_variable_is_used_before_it_is_assigned(self):
        """Catches the classic notebook bug of a cell depending on a later cell.

        Cells run in document order during the test, so a name that is only
        assigned further down the notebook is a genuine defect, not a false
        positive from out-of-order manual execution.
        """
        nb = read_notebook(NOTEBOOK_2_2)
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
            for name in ("baseURL", "server_url", "endpoint", "headers", "get_headers",
                         "username", "password", "superman", "batman", "note_resource"):
                if re.search(rf"\b{name}\b", source) and name not in assigned:
                    problems.append(
                        f"Cell {index} (id={cell.get('id')}) uses {name!r} before any "
                        "earlier cell assigns it."
                    )
        assert not problems, "\n".join(problems)


@pytest.fixture(scope="module")
def executed():
    """Notebook 2.2 executed once, shared by every execution-dependent test."""
    pytest.importorskip(
        "fhir.resources",
        reason="fhir.resources is required to execute 2.2 (pip install fhir.resources)",
    )
    return execute_notebook(NOTEBOOK_2_2)


class TestNotebookExecution:
    """Execute 2.2 end to end and check its outputs against the server."""

    def test_no_unexpected_cell_raises(self, executed):
        assert_no_cell_errors(executed, allowed_error_cell_ids=DELIBERATE_ERROR_CELL_IDS)

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

    def test_patient_post_returns_201(self, executed):
        """POSTing the superman Patient resource must be created, not rejected."""
        cell = find_cell(executed, "data=superman.model_dump_json()")
        text = cell_text(cell)
        assert "<Response [201]>" in text, (
            f"Expected a 201 Created for the Patient POST. Got:\n{text}"
        )

    def test_second_patient_post_returns_201(self, executed):
        cell = find_cell(executed, "data= batman.model_dump_json()")
        assert "<Response [201]>" in cell_text(cell)

    def test_malformed_documentreference_is_rejected_with_400(self, executed):
        """The tutorial teaches server-side validation via a deliberate 400."""
        cell = find_cell(executed, 'baseURL+"DocumentReference", data=note_resource.model_dump_json()')
        text = cell_text(cell)
        assert "<Response [400]>" in text, (
            "The tutorial's teaching point is that the server rejects the malformed "
            f"subject reference with a 400. Got:\n{text}"
        )
        assert "MalformedRelativeReference" in text or "malformed" in text.lower()

    def test_validation_issues_are_printed(self, executed):
        cell = find_cell(executed, 'for issue in res.json()["issue"]')
        text = cell_text(cell)
        assert "subject" in text, (
            f"Expected the malformed subject issue to be printed. Got:\n{text}"
        )

    def test_fixed_documentreference_is_accepted(self, executed):
        """After fixing the subject reference, the POST must return 201."""
        cells = [
            cell
            for cell in code_cells(executed)
            if 'baseURL+"DocumentReference"' in cell.source and "requests.post" in cell.source
        ]
        assert len(cells) >= 2, "Expected a failing and a fixed DocumentReference POST cell."
        text = cell_text(cells[-1])
        assert "<Response [201]>" in text, (
            f"The corrected DocumentReference POST did not return 201. Got:\n{text}"
        )

    def test_documentreference_read_back_returns_200(self, executed):
        cell = find_cell(executed, 'DocumentReference?patient=')
        assert "<Response [200]>" in cell_text(cell)

    def test_note_is_decoded_from_the_attachment(self, executed):
        """The last cell hex-decodes the attachment and prints the clinical note."""
        cell = find_cell(executed, "bytes.fromhex(")
        text = cell_text(cell)
        assert "Clark Kent" in text, (
            f"The decoded DocumentReference attachment did not contain the note. Got:\n{text[:1000]}"
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
    """After executing the notebook, the data it created must be queryable.

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

    def test_notebook_created_patients_are_on_the_server(self, executed, fhir_config):
        res = fhir_get(fhir_config, "Patient?family=Kent&given=Clark")
        assert res.status_code == 200, f"Patient search failed: {res.status_code} {res.text[:300]}"
        assert res.json()["total"] >= 1, (
            "The Clark Kent Patient the notebook POSTs is not on the server."
        )
