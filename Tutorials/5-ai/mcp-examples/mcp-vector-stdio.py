# /// script
# dependencies = [
#     "fastmcp",
#     "openai",
#     "python-dotenv",
#     "intersystems-irispython",
# ]
# ///
from pathlib import Path

import iris
from openai import OpenAI
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv(Path(__file__).resolve().parents[3] / ".env") # Read .env from the repository root

CONNECTION_ARGS = {
    "hostname": "localhost",
    "port": 32782,
    "namespace": "FHIRSERVER",
    "username": "SuperUser",
    "password": "SYS",
}

mcp = FastMCP("Vector Search Server")

@mcp.tool
def vector_search_diabetes_text(prompt:str) -> str:
    '''
    Performs a vector search for information about diabetes
    '''
    client = OpenAI()

    response = client.embeddings.create(
        input=prompt, model="text-embedding-3-small"
    )

    conn = iris.connect(**CONNECTION_ARGS)
    cursor = conn.cursor()


    sql_query = "SELECT TOP 3 text FROM Diabetes.VectorStore ORDER BY VECTOR_COSINE(embedding, TO_VECTOR(?, DOUBLE)) DESC"
    cursor.execute(sql_query, [str(response.data[0].embedding)])

    row = cursor.fetchall()

    cursor.close()
    conn.close()
    return row


if __name__=="__main__":
    mcp.run(transport ="stdio")
