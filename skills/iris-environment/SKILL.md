---
name: iris-environment
description: Start, stop, inspect and troubleshoot the kit's InterSystems IRIS for Health Docker container (iris-fhir), its ports, credentials, URLs, Python env and skip-setup scripts. Use when setting up the hackathon environment, when a connection to IRIS or the FHIR server fails, or when a later tutorial needs tables that an earlier one builds.
---

# IRIS for Health dev environment (FHIR AI Hackathon Kit)

Source tutorials: `Tutorials/1-setup/1.1-setup-iris-and-fhir.md`, `Tutorials/6-extras/CreateAFHIRServerIn5Minutes.md`.

## Facts (check `docker-iris-fhir/docker-compose.yml` if anything looks off)

| Thing | Value |
|---|---|
| Container name / compose service | `iris-fhir` / `iris` |
| Superserver (Python `iris` driver, SQL) | host `localhost`, port `32782` (container 1972) |
| Web server (FHIR REST, portal, Swagger) | `http://localhost:32783` (container 52773) |
| Credentials | `SuperUser` / `SYS` (dev only) |
| Namespace for tutorial data + FHIR | `FHIRSERVER` |
| FHIR base URL | `http://localhost:32783/fhir/r4` |
| FHIR capability statement | `http://localhost:32783/fhir/r4/metadata` |
| Management Portal | `http://localhost:32783/csp/sys/UtilHome.csp` |
| SQL explorer (FHIRSERVER) | `http://localhost:32783/csp/sys/exp/%25CSP.UI.Portal.SQL.Home.zen?$NAMESPACE=FHIRSERVER` |
| Swagger UI | `http://localhost:32783/fhir/swagger-ui/index.html` |

Default IRIS ports 1972/52773 are NOT used on the host. Only the standalone container from `CreateAFHIRServerIn5Minutes.md` uses them.

## Lifecycle

```sh
./docker-iris-fhir/start.sh            # PowerShell: .\docker-iris-fhir\start.ps1
./docker-iris-fhir/stop_and_remove.sh  # PowerShell: .\docker-iris-fhir\stop_and_remove.ps1
docker compose -f docker-iris-fhir/docker-compose.yml down -v   # full wipe incl. data volume
```

- `start.sh` builds the image, waits for IRIS, then runs `fhir_server_setup.py` inside the container (creates FHIR server, bulk-loads Synthea bundles from `docker-iris-fhir/data/fhir`). First start is slow (minutes).
- Data lives in named volume `iris-data`, so it survives restarts. Re-running `start.sh` on an existing volume re-POSTs the bundles and duplicates patients. Wipe with `down -v` for a clean state.
- Readiness check: `docker ps` shows `(healthy)`; `curl -u SuperUser:SYS http://localhost:32783/fhir/r4/metadata` returns 200.

## Shells inside the container

```sh
docker exec -it iris-fhir iris session iris     # IRIS terminal (ObjectScript), exit with: halt
docker exec -it iris-fhir bash                  # OS shell
docker cp ./local/file iris-fhir:/path/in/container
```

Use `docker exec` / `docker cp` with the container name. `docker compose exec` expects the service name (`iris`), not `iris-fhir`.

## Python env

```sh
python -m venv .venv
source .venv/Scripts/activate      # Git Bash on Windows; PowerShell: .\.venv\Scripts\Activate.ps1; mac/linux: source .venv/bin/activate
pip install -r requirements.txt    # run from repo root
cp .env.example .env               # then set OPENAI_API_KEY (needed for vector search and agents)
```

`.env` lives only at repo root. Code calls bare `load_dotenv()`, which walks up from cwd. Do not add per-folder `.env` files.

## Skip-setup scripts (recreate state that earlier tutorials build)

```sh
python Tutorials/setup-scripts/setup_csv_data.py      # Sample.Person, Sample.HealthCareData (drop + recreate)
python Tutorials/setup-scripts/setup_vector_store.py  # Diabetes.VectorStore from Tutorials/data/papers (needs OPENAI_API_KEY, paid API calls)
```

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Connection refused on 1972 / 52773 | Wrong port. Use 32782 / 32783. |
| License / connection limit errors | Community Edition caps connections. Close cursors and connections (`cursor.close(); conn.close()`), restart the Jupyter kernel holding stale ones. Failing this, restart the container with `docker restart iris-fhir`  |
| HTTP 401 from FHIR | Missing Basic auth. HTTP 403 = authenticated but not permitted. |
| `Table 'SAMPLE.PERSON' not found` (SQLCODE -30) | Table not created yet or wrong namespace. Run the skip-setup script, confirm namespace `FHIRSERVER`. |
| Portal blank right after start | IRIS still starting. Wait, refresh. |
| Embedded Python fails in container | `merge.cpf` must enable `%Service_CallIn` (already set in the kit). |

When an MCP server for IRIS is configured (`.iris-agentic-dev.toml`), prefer it for inspecting live state over guessing.
