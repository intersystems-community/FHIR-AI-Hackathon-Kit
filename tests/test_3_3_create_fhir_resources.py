"""Tests for Tutorials/3-fhir/3.3-create-fhir-resources.ipynb.

* `TestNotebookStructure` -- dependencies are importable and the notebook
  defines its variables before using them.
* `TestNotebookExecution` -- the notebook runs top to bottom with no cell
  raising, and each POST returns the status the tutorial teaches (including the
  deliberate 400 for the malformed DocumentReference).
* `TestUploadedDataVisibleOnServer` -- the resources it creates are on the server.

Needs a running FHIR server. The notebook creates its own Patient, so it does not
depend on 3.1 having been run.
"""

import re

import pytest
import requests
from requests.auth import HTTPBasicAuth

from conftest import (
    NOTEBOOK_3_3,
    assert_no_cell_errors,
    cell_text,
    code_cells,
    execute_notebook,
    find_cell,
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


class TestFhirEndpoint:
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
        """Catches the classic notebook bug of a cell depending on a later cell."""
        nb = read_notebook(NOTEBOOK_3_3)
        assigned = set(dir(__builtins__)) | {"__builtins__"}
        problems = []
        for index, cell in enumerate(code_cells(nb)):
            source = cell.source
            assigned |= set(re.findall(r"^\s*(\w+)\s*=[^=]", source, re.MULTILINE))
            assigned |= set(re.findall(r"^\s*(?:import|from)\s+(\w+)", source, re.MULTILINE))
            assigned |= set(re.findall(r"\bimport\s+(?:\w+\s+as\s+)?(\w+)", source))
            assigned |= set(re.findall(r"^\s*(?:def|class)\s+(\w+)", source, re.MULTILINE))
            assigned |= set(re.findall(r"\bfor\s+([\w, ]+?)\s+in\b", source))
            for name in ("baseURL", "endpoint", "headers", "get_headers", "username",
                         "password", "superman", "batman", "note_resource", "patient_id"):
                if re.search(rf"\b{name}\b", source) and name not in assigned:
                    problems.append(
                        f"Cell {index} (id={cell.get('id')}) uses {name!r} before any "
                        "earlier cell assigns it."
                    )
        assert not problems, "\n".join(problems)


@pytest.fixture(scope="module")
def executed():
    """Notebook 3.3 executed once, shared by every execution-dependent test."""
    pytest.importorskip(
        "fhir.resources",
        reason="fhir.resources is required to execute 3.3 (pip install fhir.resources)",
    )
    return execute_notebook(NOTEBOOK_3_3)


class TestNotebookExecution:
    """Execute 3.3 end to end and check its outputs against the server."""

    def test_no_cell_raises(self, executed):
        assert_no_cell_errors(executed)

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
        cell = find_cell(executed, "DocumentReference?patient=")
        assert "<Response [200]>" in cell_text(cell)

    def test_note_is_decoded_from_the_attachment(self, executed):
        """The last cell hex-decodes the attachment and prints the clinical note."""
        cell = find_cell(executed, "bytes.fromhex(")
        text = cell_text(cell)
        assert "Clark Kent" in text, (
            f"The decoded DocumentReference attachment did not contain the note. Got:\n{text[:1000]}"
        )


class TestUploadedDataVisibleOnServer:
    """After executing the notebook, the data it created must be queryable."""

    def test_notebook_created_patients_are_on_the_server(self, executed, fhir_config):
        res = fhir_get(fhir_config, "Patient?family=Kent&given=Clark")
        assert res.status_code == 200, f"Patient search failed: {res.status_code} {res.text[:300]}"
        assert res.json()["total"] >= 1, (
            "The Clark Kent Patient the notebook POSTs is not on the server."
        )
