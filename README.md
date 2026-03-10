# Using IRIS with Python for FHIR and AI applications

This repository contains tutorials for how to use InterSystems IRIS with an external Python Application to combine FHIR data with generative AI methods. 

## Contents 

This repo has 4 main sections: 
- **Tutorial**: contains several markdown and ipython notebook files:
    - How to set up a FHIR server with Docker
    - How to create SQL tables from a FHIR Server with FHIR-SQL Builder
    - Implementing a vector search
    - Creating a chatbot
- **Additional Demos** - Some additional tutorials with other ways to use the IRIS FHIR server with Python. This includes: 
    - [Accessing FHIR resources directly](./Additional-demos/Accessing-FHIR-resources.ipynb)
    - [Adding data to the FHIR server](./Additional-demos/Adding-FHIR-data-to-IRIS-health.ipynb)
    - [Generating Synthetic data](./Additional-demos/Making-synthetic-fhir-data.md)
    - [Integrated Machine Learning in IRIS](./Additional-demos/integratedML.md)
    - [Creating a FHIR server From Scratch](./Additional-demos/CreateAFHIRServerIn5Minutes.md)

- **Resources** - Some brief introductions that may be useful to get started quickly. These include: 
    - [What is InterSystems IRIS](./Reference/what-is-IRIS.md)
    - [What is FHIR](./Reference/what-is-FHIR.md)
    - [What is Retrieval augmented generation (RAG)](./Reference/what-is-RAG.md)

- **Dockerfhir** - Files to create a local IRIS-health-community instance and FHIR server with Docker. The [main tutorial](./Tutorial/0-FHIR-server-setup.md) covers how this should be used. 

## Requirements 

- **Python** - The tutorial is Python based, so will need Python installed on your computer

- **Docker** - The IRIS-health instance and FHIR server in all examples are run in a docker container, for this you will need to install [Docker](https://www.docker.com/)

- **Ollama** - One of the main tutorial steps is to query a local Large Language model, which is done with Ollama. If you are interested in using a local chatbot, you're best to install Ollama which can be done from their [website](https://ollama.com/).
 
- **Python Packages** - Various other python packages are used throughout, these are listed in the requirements.txt file and can be installed easily: `pip install -r requirements.txt`. It is stated whenever a new pacakage is used throughout the demos, so if you'd rather only install the packages you need you can skip this and install the remaining packages when you need them.

# FHIR + AI Chatbot Demo

## Introduction

The main tutorial demonstrates how FHIR data can be combined with IRIS vector search capabilities to build a powerful tool for medical professionals wanting to quickly understand the medical history of a patient. 

We are going to take the data from 'DocumentReference' resources, these consist of clinical notes attached in plain text. This plain text is encoded within the resource and will need to be decoded.

This tutorial is based on a [demo created by Simon Sha](https://community.intersystems.com/post/demo-video-fhir-powered-ai-healthcare-assistant) for the 2025 InterSystems Demo Games. His demonstration is shown here: 

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/P5JcdjLNvbc/0.jpg)](https://www.youtube.com/watch?v=P5JcdjLNvbc)


## Tutorial

This is a start-to-finish tutorial which goes through:

#### [0 - FHIR server set-up](./Tutorial/0-FHIR-server-setup.md)
1. Create instance of IRIS-health and FHIR server
2. Load Data into FHIR Server

#### [1 - Create SQL projection](./Tutorial/1-Using-FHIR-SQL-Builder.ipynb)
1. Use the IRIS FHIR-SQL builder to create a SQL table from the FHIR data
2. Query this SQL table from Python

#### [2 - Vector Search](./Tutorial/2-Creating-Vector-DB.ipynb)
1. Fetch data using SQL queries.
2. Decode Clinical Notes to plain text
3. Use a text-embedding model to encode the Clinical Notes to Vectors
4. Create a new table in IRIS with these Vectors
5. Perform a rapid vector search to find related notes

#### [3 - Prompt a Local LLM](./Tutorial/3-LLM-Prompting.ipynb)
1. Create a prompt that includes system instructions,  relevant notes, and a user query
2. Pass prompt to a Large Language Model
3. Return output to user

#### [4 - Making it Agentic](./Tutorial/4-Making-It-Agentic.ipynb)
1. Use OpenAI call with langchain to create an agent
2. Bind tools to agent so it can query the vector database autonomously to retrieve relevant information