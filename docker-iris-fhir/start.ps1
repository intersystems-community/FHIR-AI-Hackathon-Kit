$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path


docker compose -f "$ScriptDir\docker-compose.yml" up --build -d


while (-not (docker exec iris-fhir iris session IRIS -U %SYS "write ""ready"",!" 2>$null)) {
    Write-Host "Waiting for IRIS..."
    Start-Sleep -Seconds 2
}

docker exec iris-fhir irispython fhir_server_setup.py
