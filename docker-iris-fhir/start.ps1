$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TimeoutSeconds = 300

docker compose -f "$ScriptDir\docker-compose.yml" up --build -d
if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose failed (exit $LASTEXITCODE)"
    exit 1
}

$sw = [System.Diagnostics.Stopwatch]::StartNew()
while (-not (docker exec iris-fhir iris session IRIS -U %SYS "write ""ready"",!" 2>$null)) {
    if ((docker inspect -f '{{.State.Running}}' iris-fhir 2>$null) -ne "true") {
        Write-Error "Container iris-fhir is not running. Check: docker logs iris-fhir"
        exit 1
    }
    if ($sw.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
        Write-Error "IRIS not ready after $TimeoutSeconds s. Check: docker logs iris-fhir"
        exit 1
    }
    Write-Host "Waiting for IRIS... ($([int]$sw.Elapsed.TotalSeconds)s)"
    Start-Sleep -Seconds 2
}

# Override with e.g. $env:PYTHON = "py". Otherwise take the first candidate that actually runs
# (this skips the Windows Store python3 stub, which exists on PATH but does not run Python).
$Python = $env:PYTHON
if (-not $Python) {
    foreach ($candidate in "python", "py", "python3") {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            & $candidate -c "pass" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $Python = $candidate
                break
            }
        }
    }
}
if (-not $Python) {
    Write-Error "No working python, py or python3 found on PATH. Set `$env:PYTHON to the executable."
    exit 1
}

& $Python "$ScriptDir\fhir_server_setup_native.py"
if ($LASTEXITCODE -ne 0) {
    Write-Error "fhir_server_setup_native.py failed (exit $LASTEXITCODE)"
    exit 1
}
