import requests
from requests.auth import HTTPBasicAuth
from fastmcp import FastMCP

mcp = FastMCP("FHIR MCP Server")

# General FHIR query tool
@mcp.tool
def fhir_query(endpoint:str, search_params:str ) -> str:
    """
    Query FHIR data directly. 

    Parameters are endpoint and query, such that the request to the FHIR Server API is as follows: 

    GET /<endpoint>?<search_params> 

    Returns: FHIR/JSON response body
    """
    ## Credentials
    username = "SuperUser"
    password = "SYS"
    
    ## FHIR server location
    base_url = "http://localhost:32783/fhir/r4/"
    
    headers ={    "Accept": "application/fhir+json"}

    url = base_url+endpoint+"?"+search_params
    
    print(f"Print calling FHIR Server at {url} \n\n")
    
    res = requests.get(url, headers=headers, auth=HTTPBasicAuth(username,password))
    res.raise_for_status()

    return res.text


if __name__=="__main__":
    mcp.run(
        transport = "streamable-http", 
        host = "127.0.0.1",
        port = 8001

    )