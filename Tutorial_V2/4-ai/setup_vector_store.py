"""
Skip-setup script for the vector-search.ipynb tutorial.

Run this once to recreate the Diabetes.VectorStore table and populate it
with both the sample diabetes texts and the PDF papers, so you can jump
straight to the "Search" section of the notebook without re-running setup.
"""

import os

import iris
import pymupdf
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI

load_dotenv()

connection_args = {
    "hostname": "localhost",
    "port": 32782,
    "namespace": "FHIRSERVER",
    "username": "SuperUser",
    "password": "SYS",
}

client = OpenAI()


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    separators=[". ", " ", ""],  # prefer splitting between sentences, then between words
    keep_separator="end",  # keep the full stop at the end of the sentence it belongs to
)


def get_chunks(doc_path: str):
    with pymupdf.open(doc_path) as doc:
        text = " ".join(page.get_text("text") for page in doc)

    text = " ".join(text.split())  # sanitize: collapse whitespace/newlines into single spaces

    chunks = text_splitter.split_text(text)

    return doc_path, chunks


diabetes_texts = [
    "Managing blood glucose levels is an important part of living with diabetes, helping reduce symptoms and lower the risk of serious long-term health complications.",
    "Insulin helps move sugar from the bloodstream into the body's cells, where it can be converted into energy or stored for use at a later time.",
    "Type 1 diabetes occurs when the immune system attacks insulin-producing cells, leaving the body able to produce very little or no insulin of its own.",
    "People with type 2 diabetes may develop resistance to insulin, meaning their cells respond poorly to the hormone and glucose remains elevated in the bloodstream.",
    "Frequent thirst and urination can be warning signs of high blood sugar, particularly when accompanied by tiredness, blurred vision, or unexplained weight loss.",
    "A balanced diet containing vegetables, fibre, protein, and suitable portions of carbohydrates can help maintain glucose levels within a healthier and more stable range.",
    "Regular physical activity may improve the body's response to insulin, allowing muscles to use glucose more effectively while also supporting cardiovascular health and weight management.",
    "A glucose monitor measures the amount of sugar currently in the blood, providing information that can guide decisions about food, medication, exercise, and insulin doses.",
    "Hypoglycaemia describes a blood sugar level that is too low, which may cause sweating, shaking, confusion, hunger, dizziness, or difficulty concentrating on everyday tasks.",
    "Hyperglycaemia is the medical term for excessively high blood glucose, which can develop when the body has insufficient insulin or cannot use insulin effectively.",
    "Some people control type 2 diabetes through dietary adjustments, increased physical activity, weight management, and oral medication prescribed by a qualified healthcare professional.",
    "Insulin injections may be required when the body cannot regulate glucose effectively, replacing or supplementing the insulin that would normally be produced by the pancreas.",
    "Long-term poor glucose control can damage the eyes, kidneys, nerves, blood vessels, and heart, increasing the likelihood of several serious diabetes-related health complications.",
    "Gestational diabetes develops during pregnancy when hormonal changes affect insulin function, and although it often resolves after birth, continued monitoring may still be recommended.",
    "An HbA1c test estimates average blood glucose over the previous few months, giving a broader view of glucose management than a single daily blood sugar measurement.",
]

print("Creating Diabetes.VectorStore table...")

conn = iris.connect(**connection_args)
cursor = conn.cursor()

sql_create = """CREATE TABLE Diabetes.VectorStore (
                Source VARCHAR(100),
                Text VARCHAR(10000),
                Embedding VECTOR(DOUBLE, 1536)
                )"""

cursor.execute("DROP TABLE IF EXISTS Diabetes.VectorStore")
cursor.execute(sql_create)
conn.close()

print(f"Embedding and inserting {len(diabetes_texts)} sample diabetes texts...")

insert_query = "INSERT INTO Diabetes.VectorStore (Source, Text, Embedding) VALUES (?, ?, TO_VECTOR(?))"

conn = iris.connect(**connection_args)
cursor = conn.cursor()

for i, text in enumerate(diabetes_texts):
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    embedding = response.data[0].embedding

    cursor.execute(insert_query, ["Raw_text", text, str(embedding)])
    print(f"  inserted text {i + 1}/{len(diabetes_texts)}")

conn.close()

pdfs = ["papers/" + x for x in os.listdir("papers") if x[-4:] == ".pdf"]
print(f"Embedding and inserting chunks from {len(pdfs)} PDFs: {pdfs}")

conn = iris.connect(**connection_args)
cursor = conn.cursor()

for pdf in pdfs:
    doc_path, chunks = get_chunks(pdf)
    print(f"  {doc_path}: {len(chunks)} chunks")

    for i, chunk in enumerate(chunks):
        response = client.embeddings.create(input=chunk, model="text-embedding-3-small")
        embedding = response.data[0].embedding

        cursor.execute(insert_query, [doc_path, chunk, str(embedding)])
        print(f"    inserted chunk {i + 1}/{len(chunks)}")

conn.close()

print("Done. Diabetes.VectorStore is ready to search.")
