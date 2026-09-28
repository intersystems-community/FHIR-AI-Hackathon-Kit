# Create a FHIR Server in 5 minutes with IRIS Health Community

This article provides a programmatic way to rapidly create a local FHIR server with the Community edition of IRIS Health, pre-loaded with synthetic data from Synthea. 

The only requirement for this is having [Docker](https://www.docker.com/) installed. While I include instructions for downloading IRIS Health Community locally with docker, the rest of the process would apply to any other instance of IRIS Health.

Please note, if using the existing template the FHIR server is set up for you, so this isn't necessary unless you need a second FHIR Repository. 

## Create Synthetic data

Before setting up IRIS health and the FHIR Server, we can create synthetic data with [Synthea](https://synthetichealth.github.io/synthea/). The [InterSystems Developer Community](https://github.com/intersystems-community/irisdemo-base-synthea/tree/master) has helpfully created a docker image to simplify this process to a single command:

```
docker run --rm -v $PWD/output:/output --name synthea-docker intersystemsdc/irisdemo-base-synthea:version-1.3.4 -p 100
```

This creates a folder in the current directory called `output`, it then runs Synthea to create 100 patient records (`-p 100`). The docker container is removed when the process is finished, leaving 100 patient records in `output/fhir`.

## Download IRIS Health Community

To download and run IRIS health community edition with docker , you can just run: 
```
docker run -d --name iris-health-community --publish 1972:1972 --publish 52773:52773 -v $PWD/output:/usr/irissys/output intersystems/irishealth-community:latest-em
```

To break this down:

- `docker run` Runs a docker image. If you have not downloaded the image, it will automatically do so. 
- `--name` gives running container a name (iris-health-community) 
- The IRIS Health Community ports 1972 and 52773 have been mapped to the equivalent local ports (`--publish <local>:<container>`).
- The `output` directory containing the FHIR data has been mounted to the IRIS health container with the `-v $PWD/output:/usr/irissys/output` flag. 
- `-d` flag detaches the terminal, meaning we can carry on using the same terminal window.
- `intersystems/irishealth-community` is the docker image being downloaded from [docker hub](https://hub.docker.com/r/intersystems/irishealth-community)


## Create FHIR Server

Start an IRIS terminal: 

```
docker exec -it iris-health-community iris session iris
``` 

#### Unexpire passwords

By default, Community editions of IRIS health have the password SYS for every account, but these have expired, meaning you will be prompted to change the passwords on first login with the management portal. Authorization with other methods might fail due to an unexpired password. Obviously, this is only suitable for development environments, while authorization should be more robust for production environments.

```
set $NAMESPACE = "%SYS"
do ##class(Security.Users).UnExpireUserPasswords("*")
```


#### Create a new namespace for your FHIR server


```
set $NAMESPACE = "HSLIB"
do:'##class(%SYS.Namespace).Exists("fhirdemo") ##class(HS.Util.Installer.Foundation).Install("fhirdemo")
set $NAMESPACE = "fhirdemo"
```

#### Install the FHIR server

```
// Make the path prefix for the FHIR server
set fhirServerPath = "/demo/fhir"

// Create Strategy 
set strategyClass = "HS.FHIRServer.Storage.Json.InteractionsStrategy"

// Create metadata info for FHIR version r4
set metadataPackage = "hl7.fhir.r4.core@4.0.1"

// You can allow metadata packages for multiple FHIR versions with the following: 
// set metadataPackage = $LISTBUILD("hl7.fhir.r4.core@4.0.1","hl7.fhir.us.core@3.1.0")

// Ensure namespace is FHIR enabled
do ##class(HS.FHIRServer.Installer).InstallNamespace()
do ##class(HS.FHIRServer.Installer).InstallInstance(fhirServerPath, strategyClass, metadataPackage)
```

#### Limit max search results

These lines set limits on the amount of results yielded from a search of our FHIR endpoint. Setting limits is recommended to avoid transferring huge amounts of data.

```
set strategy = ##class(HS.FHIRServer.API.InteractionsStrategy).GetStrategyForEndpoint(fhirServerPath)
set configData = strategy.GetServiceConfigData()
set configData.DefaultSearchPageSize = 1000
set configData.MaxSearchPageSize = 10000
set configData.MaxSearchResults = 10000
do strategy.SaveServiceConfigData(configData)
```

#### Add FHIR resources to the FHIR Server
```
// Location of our FHIR data
set fhirdata = "/usr/irissys/output/fhir"

// Load FHIR resource files
do ##class(HS.FHIRServer.Tools.DataLoader).SubmitResourceFiles(fhirdata, "FHIRServer", fhirServerPath, 1, "^fhirlogs")
```
The `SubmitResourceFiles` method submits the files to the fhir server. The arguments given are as follows: 
 - Location of the FHIR data
 - The type of service required (FHIRServer or HTTP)
 - The FHIR server location path
 - Display progress - yes (1) or no (0)
 - Log process to a global (`^fhirlogs`)


#### Check endpoint

We can check that the endpoint is running by visiting: 

[http://localhost:52773/demo/fhir/metadata](http://localhost:52773/demo/fhir/metadata)

It should download a metadata xml file.

## Querying FHIR Endpoint

Now that we have loaded the data, we can query the endpoint with an HTTP request: 

```http
GET http://localhost:52773/demo/fhir/Patient/1
Authorization: Basic SuperUser SYS
Accept: application/fhir+json
```

This request gets the Patient resource for Patient ID 1 and can be sent (in a similar format) from any HTTP client.

Depending on HTTP client in use, credentials may need to be encoded. Examples are shown using Python's Requests library and `Curl` in Windows Powershell:

```Powershell
$pair = "SuperUser:SYS"
$encoded = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
curl -Uri "http://localhost:52773/demo/fhir/Patient" `
    -Headers @{
        Authorization = "Basic $encoded"
        Accept = "application/fhir+json"
    } `
    -Method GET `
    -OutFile "response.json"
```

```python
import requests
from requests.auth import HTTPBasicAuth

headers = {"Content-Type": "application/fhir+json"}
uri = "http://localhost:52773/demo/fhir/Patient/1"

username = "_SYSTEM"
password = "SYS"
res = requests.get(uri, headers=headers, auth=HTTPBasicAuth(username, password))
print(res)
print(res.json())
```
