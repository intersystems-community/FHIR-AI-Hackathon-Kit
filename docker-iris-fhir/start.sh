#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMEOUT_SECONDS=500

docker compose -f "$SCRIPT_DIR/docker-compose.yml" up --build -d

start=$SECONDS
until MSYS_NO_PATHCONV=1 docker exec iris-fhir iris session IRIS -U %SYS "write ""ready"",!" >/dev/null 2>&1; do
  if [ "$(docker inspect -f '{{.State.Running}}' iris-fhir 2>/dev/null)" != "true" ]; then
    echo "ERROR: container iris-fhir is not running. Check: docker logs iris-fhir" >&2
    exit 1
  fi
  if [ $((SECONDS - start)) -ge $TIMEOUT_SECONDS ]; then
    echo "ERROR: IRIS not ready after ${TIMEOUT_SECONDS}s. Check: docker logs iris-fhir" >&2
    exit 1
  fi
  echo "Waiting for IRIS... ($((SECONDS - start))s)"
  sleep 2
done

# Override with e.g. PYTHON=py ./start.sh. Otherwise take the first candidate that actually runs
# (this skips the Windows Store python3 stub, which exists on PATH but does not run Python).
if [ -z "${PYTHON:-}" ]; then
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "" >/dev/null 2>&1; then
      PYTHON="$candidate"
      break
    fi
  done
fi
if [ -z "${PYTHON:-}" ]; then
  echo "ERROR: no working python3 or python found on PATH. Set PYTHON=<executable>." >&2
  exit 1
fi

# The setup script needs the intersystems-irispython package, so run it from the repo's .venv
# (the same one the tutorials use), creating it if needed.
VENV="$SCRIPT_DIR/../.venv"
[ -d "$VENV" ] || "$PYTHON" -m venv "$VENV"
if [ -f "$VENV/Scripts/python.exe" ]; then VENV_PYTHON="$VENV/Scripts/python.exe"; else VENV_PYTHON="$VENV/bin/python"; fi
"$VENV_PYTHON" -m pip install -q intersystems-irispython

"$VENV_PYTHON" "$SCRIPT_DIR/fhir_server_setup_native.py"
