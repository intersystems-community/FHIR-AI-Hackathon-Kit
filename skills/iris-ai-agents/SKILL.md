---
name: iris-ai-agents
description: Build LLM agents over InterSystems IRIS data - LangChain create_agent with Python function tools (SQL, FHIR REST, vector search), and exposing the same tools as MCP servers with FastMCP (streamable HTTP or stdio) for Claude Code or other MCP clients. Use when wiring IRIS / FHIR / vector data into an AI agent, chatbot, or MCP server.
---

# AI agents and MCP over IRIS data

Source tutorials: `Tutorials/5-ai/5.1-agents-and-tools.ipynb`, `5.2-mcp-server.ipynb`, examples in `Tutorials/5-ai/mcp-examples/` (`mcp-fhir-http.py`, `mcp-vector-stdio.py`, `.mcp.json`).

Deps: `langchain "langchain[openai]" "langchain[mcp]" fastmcp python-dotenv`. `OPENAI_API_KEY` in repo-root `.env`. Tool bodies reuse patterns from the `iris-sql-python`, `iris-fhir` and `iris-vector-search` skills.

## Tools are plain functions

The model sees the function name, type hints and docstring. Make docstrings say what the tool returns and when to use it. Tools make deterministic work (encoding, lookups, maths) reliable instead of "vibe" answers.

```python
import iris, requests
from requests.auth import HTTPBasicAuth

CONNECTION_ARGS = {"hostname": "localhost", "port": 32782, "namespace": "FHIRSERVER",
                   "username": "SuperUser", "password": "SYS"}

def search_superheros() -> list:
    """Returns first name, last name and age of every superhero in Sample.Person."""
    conn = iris.connect(**CONNECTION_ARGS)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT FirstName, LastName, Age FROM Sample.Person")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def fhir_query(endpoint: str, search_params: str) -> str:
    """Query the FHIR R4 server: GET /<endpoint>?<search_params>. Returns the FHIR JSON bundle as text."""
    url = "http://localhost:32783/fhir/r4/" + endpoint + "?" + search_params
    res = requests.get(url, headers={"Accept": "application/fhir+json"},
                       auth=HTTPBasicAuth("SuperUser", "SYS"))
    res.raise_for_status()
    return res.text
```

Let tool errors raise; the agent framework reports them to the model. Returning an error string hides failures.

## LangChain agent

```python
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI

load_dotenv()

model = ChatOpenAI(model="gpt-5-nano", reasoning_effort="medium")
agent = create_agent(
    model=model,
    tools=[fhir_query, search_superheros, vector_search_diabetes_text],
    system_prompt=("You are an InterSystems IRIS data agent. Use the tools to find data in IRIS "
                   "and answer only from tool results."),
)

result = agent.invoke({"messages": [HumanMessage("How tall is Tish Lemke? Use FHIR data")]})
for m in result["messages"]:
    m.pretty_print()          # shows tool calls + tool outputs, useful for debugging
answer = result["messages"][-1].content
```

- Small models plus a generic `fhir_query` can be flaky on multi-hop questions (find patient, then Observation by LOINC code). Raise reasoning effort, add hints to the system prompt (e.g. "body height is Observation code 8302-2"), or add narrower tools.
- Cap tool output size (TOP n, `_count`, `_elements`) to protect the context window.

## MCP server with FastMCP

```python
from fastmcp import FastMCP

mcp = FastMCP("IRIS Tools")

@mcp.tool
def sql_query(query: str) -> dict:
    """Run a read-only SELECT against IRIS (namespace FHIRSERVER). Returns up to 50 rows."""
    if not query.lstrip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT statements are allowed")
    conn = iris.connect(**CONNECTION_ARGS)
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        rows = [list(r) for r in cursor.fetchmany(50)]
        truncated = cursor.fetchone() is not None
        return {"columns": [d[0] for d in cursor.description], "data": rows,
                "row_count": len(rows), "truncated": truncated}
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8001)   # endpoint http://127.0.0.1:8001/mcp
    # or: mcp.run(transport="stdio")  - client launches the process itself
```

- A prefix check is not real protection. For anything beyond a local demo, connect as an IRIS user with SELECT-only privileges.
- HTTP transport: start the server yourself before the client connects. Stdio: the client spawns it, so paths/env must resolve from the client's cwd (the kit's stdio example loads `.env` via `Path(__file__)`).
- Inside Jupyter, run the HTTP server in a daemon `threading.Thread` so the kernel stays usable (see 5.2).

## Register with Claude Code / MCP clients (`.mcp.json`)

```json
{
  "mcpServers": {
    "FHIR-Server": {"type": "http", "url": "http://localhost:8001/mcp"},
    "VectorSearch": {"type": "stdio", "command": "uv", "args": ["run", "mcp-vector-stdio.py"]}
  }
}
```

`uv run` reads the PEP 723 `# /// script` dependency block at the top of the stdio script. Without uv use `"command": "python"` pointing at the venv interpreter and an absolute script path.

## Use MCP tools from a LangChain agent

```python
from langchain.agents import create_agent
from langchain.mcp import MCPAdapter      # beta API in langchain 1.x, may change

mcp_client = MCPAdapter("http://localhost:8001/mcp")

async def ask(prompt: str):
    async with mcp_client:
        tools = await mcp_client.list_tools()
        agent = create_agent(model="openai:gpt-5-nano", tools=tools)
        return await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})   # MCP tools require async
```

In a notebook use top-level `await ask(...)`; in a script `asyncio.run(ask(...))`.
