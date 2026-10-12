#!/usr/bin/env bash

# The files start.sh and start.ps1 (powershell equivalent) start up the environment.
# The code in these files looks messy because it handles being run from other directories, 
# different python executables (`python` vs `python3`), windows/unix differences and other sources of errors.
# However, the actual start up is simple. This script shows the steps without the robust error handling. 

# This script is for educational purposes, for error free start-up, run start.sh or start.ps1


# 1: Build and Setup InterSystems IRIS For Health Container
# Docker build includes copying sample FHIR data (./data/fhir) into container
# And unexpires user passwords

docker compose up --build -d 

# 2: Create Python Virtual Environment 
# This is created in the root directory 
 
python3 -m venv ../.venv 


# 3. Activate virtual environment 
# The syntax of this differs between Unix and Windows  
source activate ../.venv/bin/activate


# 4. Install intersystems-irispython 

pip install intersystems-irispython

# 5. Wait for IRIS to be ready 
# After the container starts up, IRIS takes a bit of time to start up. This loop just polls to see if it is ready. 
# Note - this version will loop infinitely if start up fails. Version in start.sh has better handling of this. 
until docker-compose exec iris iris session IRIS -U %SYS "write ""ready"",!" >/dev/null 2>&1; do
  echo "Waiting for IRIS..."
  sleep 2
done


# 6. Run fhir_server_setup_native.py Script
# Python script using native API connection to connect to IRIS for health 
# And run the setup scripts 

python3 fhir_server_setup_native.py