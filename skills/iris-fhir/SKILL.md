---
name: iris-fhir
description: Load, create, validate and query FHIR R4 data on the InterSystems IRIS for Health FHIR server from Python, using requests (REST), fhir.resources (building resources) and fhirpy (client). Covers posting Synthea bundles, creating Patient/DocumentReference resources, handling OperationOutcome validation errors, search parameters, paging, and generating synthetic data. Use for any FHIR task in this kit.
---

# FHIR on IRIS for Health

Source tutorials: `Tutorials/3-fhir/3.1-load-fhir-data.ipynb`, `3.2-querying-fhir-data-with-python.ipynb`, `3.3-viewing-fhir-specification-with-swagger.md`, `3.4-create-synthetic-fhir-data.md`.

Base URL `http://localhost:32783/fhir/r4/`, Basic auth `SuperUser` / `SYS`, namespace `FHIRSERVER`. Swagger UI (pre-authenticated) at `http://localhost:32783/fhir/swagger-ui/index.html` is the fastest way to try an endpoint by hand.

## Common setup

```python
import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:32783/fhir/r4/"
AUTH = HTTPBasicAuth("SuperUser", "SYS")
GET_HEADERS = {"Accept": "application/fhir+json"}
POST_HEADERS = {"Content-Type": "application/fhir+json"}
```

Status codes: 200 ok, 201 created, 400 invalid (body is an OperationOutcome), 401 no/bad auth, 403 forbidden, 404 not found.

## Load bundles (e.g. Synthea output)

POST a transaction Bundle to the base URL; the server routes each entry.

```python
from pathlib import Path
import json

files = sorted(Path("Tutorials/data/fhir").glob("*.json"))
# Synthea patient bundles reference hospital/practitioner bundles: load those first
files.sort(key=lambda p: not p.name.startswith(("hospitalInformation", "practitionerInformation")))
for i, path in enumerate(files, 1):
    bundle = json.loads(path.read_text(encoding="utf-8"))
    res = requests.post(BASE_URL, json=bundle, headers=POST_HEADERS, auth=AUTH)
    print(f"[{i}/{len(files)}] {path.name}: {res.status_code}")
    res.raise_for_status()
```

POSTing the same bundle twice creates duplicates.

Generate synthetic data (writes `./output/fhir/*.json`, `-p` = patient count):

```sh
docker run --rm -v $PWD/output:/output --name synthea-docker intersystemsdc/irisdemo-base-synthea:version-1.3.4 -p 100
```

## Build resources with fhir.resources

```python
from fhir.resources.patient import Patient

patient = Patient.model_validate({
    "name": [{"use": "official", "family": "Kent", "given": ["Clark"]}],   # given is a list
    "birthDate": "1965-02-12",
    "gender": "male",
})
body = patient.model_dump_json()     # JSON string; send as data=, not json= (datetimes break json=)
```

`model_construct()` skips validation (set fields afterwards). `fhir.resources` validation is partial; the server validates more strictly (references, required elements).

## Create and capture the server id

```python
res = requests.post(BASE_URL + "Patient", data=body, headers=POST_HEADERS, auth=AUTH)
if res.status_code != 201:
    raise RuntimeError(res.text)
patient_id = res.headers["Location"].split("/Patient/")[1].split("/")[0]
```

POST assigns the id; never hardcode ids from a previous run. Use `PUT {BASE_URL}Patient/{id}` to create/update with your own id.

## References and attachments (DocumentReference)

```python
import base64
from fhir.resources.documentreference import DocumentReference

doc = DocumentReference.model_validate({
    "status": "current",
    "subject": {"reference": f"Patient/{patient_id}"},     # must be ResourceType/id, bare "500" is rejected
    "content": [{"attachment": {
        "contentType": "text/plain; charset=utf-8",
        "data": base64.b64encode(note.encode("utf-8")).decode("ascii"),   # FHIR attachment.data is base64Binary
    }}],
})
```

Note: the 3.1 notebook encodes attachment data as hex, which the server accepts but does not match the spec. If you read notes written by the tutorial, decode with `bytes.fromhex(...)`; otherwise use base64.

## Handle validation errors

```python
if res.status_code == 400:
    for issue in res.json()["issue"]:
        print(issue["severity"], issue["details"]["text"])
```

## Search over REST

```python
res = requests.get(BASE_URL + "Patient", params={"family": "Lemke", "given": "Tish"}, headers=GET_HEADERS, auth=AUTH)
res.raise_for_status()
bundle = res.json()
patients = [e["resource"] for e in bundle["entry"]] if bundle["total"] else []
```

- URL form is `Patient?name=...` (no slash before `?`).
- `name` is fuzzy (matches substrings of any name part); use `family`/`given`/`birthdate` for precision.
- Unknown search params are silently ignored (verified: 200 with all results). A typo'd param looks like "no filter", not an error. Check names at `https://build.fhir.org/<resource>-search.html`.
- Results are paged. Follow `link` with `relation == "next"` until absent. `_count=N` sets page size; `_summary=count` returns only `total`.
- Sort: `_sort=-date` (minus = descending). Latest items: `_sort=-_lastUpdated&_count=5`.
- Clinical resources by patient: `Condition?patient=<id>`, `Observation?patient=<id>&code=29463-7` (LOINC body weight), `Procedure?patient=<id>`, `DocumentReference?patient=<id>`.

## Search with fhirpy

```python
from fhirpy import SyncFHIRClient
import base64

token = base64.b64encode(b"SuperUser:SYS").decode("utf-8")
client = SyncFHIRClient("http://localhost:32783/fhir/r4/", authorization=f"Basic {token}")

matches = client.resources("Patient").search(family="Lemke", given="Tish", birthdate="1978-06-25").fetch()
if len(matches) != 1:
    raise ValueError(f"Expected 1 patient, got {len(matches)}")
tish = matches[0]
print(tish.id, tish.name[0].family, tish.name[0].given[0], tish.birthDate)

conditions = client.resources("Condition").search(patient=tish.id).sort("-recorded-date").fetch()
weights = client.resources("Observation").search(patient=tish.id, code="29463-7").sort("-date").fetch_all()
series = [(o.effectiveDateTime, o.valueQuantity.value, o.valueQuantity.unit) for o in weights]
```

- `.fetch()` returns the first page only; `.fetch_all()` follows paging.
- `resource.serialize()` gives the full dict; use it to learn an unfamiliar resource's shape before writing accessors.
- Search param names (`recorded-date`, `birthdate`) differ from element names (`recordedDate`, `birthDate`).

For population-level analytics prefer projecting FHIR to SQL (FHIR SQL Builder) and using the `iris-sql-python` skill over paging through REST.
