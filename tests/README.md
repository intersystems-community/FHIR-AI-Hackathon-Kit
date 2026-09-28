# Notebook tests

Tests that execute the Tutorials notebooks against a live IRIS instance and
assert they produce roughly the documented output without erroring.

Their main job is to catch drift: if a port mapping in
`docker-iris-fhir/docker-compose.yml` changes, the FHIR endpoint path moves, or
an IRIS password changes, the notebooks silently stop working for anyone
following the tutorial. These tests read the connection details out of the
notebook source and check them against the running server, so the failure is
reported against the notebook rather than discovered by a user.

## Running

Start the IRIS container first (`docker-iris-fhir/start.sh` or `start.ps1`), then:

    cd tests
    python -m pytest

Test modules are named after the notebook they cover (`test_3_1_...` tests
`Tutorials/3-fhir/3.1-...`), so they run in tutorial order. `test_4_1` and
`test_5_1` call OpenAI and need `OPENAI_API_KEY` in the repository-root `.env`.

Requirements: `pytest`, `nbformat`, `nbclient`, `ipykernel`, plus the notebooks'
own dependencies (`intersystems-irispython`, `pandas`, `requests`,
`fhir.resources`).

    pip install pytest nbformat nbclient ipykernel intersystems-irispython pandas requests fhir.resources

Notebook `pip install` cells are stripped before execution (they are slow and
would mutate the test environment). Instead, each test module has a
`test_dependencies_importable` test that skips if a package is missing.

## Layers

Each module has three groups of tests, cheapest first:

- **Connection / endpoint tests** -- the hostname, port, namespace, credentials
  and FHIR base URL written in the notebook are valid against the live server.
  Fast, and the ones that catch configuration drift.
- **Structure tests** -- the data files the notebook reads exist and have the
  expected shape; the notebook still contains the cells the narrative describes.
- **Execution tests** -- the notebook is run top to bottom with `nbclient` and
  every cell is checked for errors and for its expected output. `2.1` also
  queries IRIS afterwards to confirm the row counts.

## Deliberate errors

`3.1` teaches FHIR server-side validation by POSTing a `DocumentReference` with
a malformed subject reference, seeing a 400, then fixing it. The
400 is asserted as the expected outcome. One cell (`cb56dc36-...`) deliberately
raises by calling `.json()` on an empty 201 body; its id is listed in
`DELIBERATE_ERROR_CELL_IDS` so it is excluded from the no-errors check. If you
change that cell, update the constant.

## Current status

`2.1` passes. `2.2` fails, as expected -- these tests were written to document
the known breakage:

- `baseURL` in 2.2 is `http://localhost:32783/csp/healthshare/demo/fhir/r4/`,
  but the FHIR server in this repo is installed at `/fhir/r4` (see
  `docker-iris-fhir/fhir_server_setup.py`). The documented URL returns 404.
- The credentials are `_SYSTEM` / `ISCDEMO`; the instance uses `SuperUser` / `SYS`.
- The notebook posts the same `username`/`password` under two spellings
  (`_SYSTEM` and `_System`) and sets the target URL twice (`server_url` and
  `baseURL`).
- `./output/fhir` and `note_data/clinical_note.txt` do not exist under
  `2-loading-data/`; copies live in `Additional-demos/`.
- Cell `f3d4a43a` uses `baseURL`, `endpoint` and `get_headers` before any earlier
  cell assigns them, so the notebook cannot run top to bottom as written.

Fixing the notebook should make the whole suite green with no test changes.
