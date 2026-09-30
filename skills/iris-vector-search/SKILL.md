---
name: iris-vector-search
description: Store text embeddings in an InterSystems IRIS VECTOR column and run semantic similarity search with SQL (TO_VECTOR, VECTOR_COSINE). Covers table DDL, chunking PDFs with pymupdf and langchain-text-splitters, embedding with OpenAI text-embedding-3-small, inserting, and a reusable search function for RAG or agent tools. Use for any vector / semantic search / RAG task against IRIS.
---

# Vector search in IRIS

Source tutorial: `Tutorials/4-vector-search/4.1-vector-search.ipynb`, skip-setup `Tutorials/setup-scripts/setup_vector_store.py` (builds `Diabetes.VectorStore` from `Tutorials/data/papers/*.pdf`).

Deps: `intersystems-irispython openai python-dotenv pymupdf langchain-text-splitters`. `OPENAI_API_KEY` in repo-root `.env`, loaded with `load_dotenv()`. Connection args: see `iris-sql-python` skill.

## Table

```sql
CREATE TABLE Diabetes.VectorStore (
    Source    VARCHAR(100),
    Text      VARCHAR(10000),
    Embedding VECTOR(DOUBLE, 1536)
)
```

Dimension must equal the embedding model's output: `text-embedding-3-small` = 1536.

## Chunk documents

```python
import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=100,
    separators=[". ", " ", ""],   # prefer sentence boundaries, then words
    keep_separator="end",
)

def get_chunks(pdf_path: str) -> list[str]:
    with pymupdf.open(pdf_path) as doc:
        text = " ".join(page.get_text("text") for page in doc)
    return splitter.split_text(" ".join(text.split()))   # collapse whitespace first
```

Keep chunk length under the `Text` column size.

## Embed and insert

Embeddings go in as a string (`str(list_of_floats)`) wrapped in `TO_VECTOR(?)`.

```python
from openai import OpenAI
client = OpenAI()

def embed(texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(input=texts, model="text-embedding-3-small")   # batch: one call, many texts
    return [d.embedding for d in resp.data]

insert = "INSERT INTO Diabetes.VectorStore (Source, Text, Embedding) VALUES (?, ?, TO_VECTOR(?))"
for n, (source, chunks) in enumerate(chunks_by_doc.items(), 1):
    vectors = embed(chunks)
    cursor.executemany(insert, [[source, c, str(v)] for c, v in zip(chunks, vectors)])
    print(f"[{n}/{len(chunks_by_doc)}] {source}: {len(chunks)} chunks")
```

Embedding calls cost money; batch them and log progress. The tutorial stores `Source` as `../data/papers/<file>.pdf`.

## Search

```python
def vector_search(prompt: str, top_k: int = 3) -> list:
    """Return (Source, Text) rows most similar to prompt."""
    query_vec = embed([prompt])[0]
    conn = iris.connect(**connection_args)
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"SELECT TOP {int(top_k)} Source, Text FROM Diabetes.VectorStore "
            "ORDER BY VECTOR_COSINE(Embedding, TO_VECTOR(?, DOUBLE)) DESC",
            [str(query_vec)],
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
```

- `VECTOR_COSINE` = cosine similarity (higher is closer, sort `DESC`). `VECTOR_DOT_PRODUCT` also available; for normalised OpenAI embeddings they rank the same.
- Query and stored vectors must come from the same model.
- Combine with normal SQL filters: `WHERE Source LIKE '%Retinopathy%' ORDER BY VECTOR_COSINE(...) DESC`.
- Return the score for thresholding: `SELECT TOP 3 Text, VECTOR_COSINE(Embedding, TO_VECTOR(?, DOUBLE)) AS Score ...` (bind the vector twice if also ordering by it, or `ORDER BY Score DESC`).

This function is ready to hand to an agent as a tool; see the `iris-ai-agents` skill.
