$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

docker compose -f "$ScriptDir\docker-compose.yml" down iris -v
