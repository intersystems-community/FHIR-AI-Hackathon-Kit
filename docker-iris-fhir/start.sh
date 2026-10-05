#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker compose -f "$SCRIPT_DIR/docker-compose.yml" up --build -d

until MSYS_NO_PATHCONV=1 docker exec iris-fhir iris session IRIS -U %SYS "write ""ready"",!" >/dev/null 2>&1; do
  echo "Waiting for IRIS..."
  sleep 2
done


docker exec iris-fhir irispython fhir_server_setup.py