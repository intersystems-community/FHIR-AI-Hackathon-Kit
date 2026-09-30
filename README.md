
# Welcome to the InterSystems FHIR/AI Hackathon Kit 

This kit is a set of tutorials to demonstrate how users can build applications with InterSystems IRIS for Health, using FHIR data, Python and AI Agents. This is designed to be a fast entrypoint to using InterSystems IRIS with Python and AI. 

# What's New

This tutorial series has undergone a complete re-write since version 1 (published October 2025), although still covers similar ground. The previous version is still available in the V1 branch, and features the building of a patient chatbot with Vector Search on Patient vectorized and embedded Patient data. It also made use of On-device local AI with Ollama. 

V2 features more standalone tutorials on using InterSystems IRIS for Health with tabular data, FHIR data and Vector data. It also covers building AI Agents and MCP servers in Python. 

This re-write was driven by the desire to cover more up-to-date features in the Agentic AI world, as well as a desire to replace extremely computationally heavy, slow and ineffective local AI Models with fast and cheap OpenAI models. 

## What this tutorial series is

This is a series of interactive tutorials on building applications using **Python** and **InterSystems IRIS For Health** server as the backend data platform. There is a docker template which sets up InterSystems IRIS For Health with a **FHIR server**. This is followed by a series of tutorials on how to access or add data to the FHIR Server or to the SQL database from Python Application. 

The tutorials also cover using **vector data** for fast semantic matching. This is a very effective way to build searches against unlabelled, unstructured data. It is particularly effective when combined with AI Agents. 

Finally, the tutorials cover building basic **AI Agents** which can access the data from the InterSystems IRIS for Health instance, including building **MCP servers** to provide access to existing agents. 

These tutorials are designed to be a rapid quickstart for you to include InterSystems IRIS into your applications.

## What this tutorial series is *not*

This series is not an in-depth look at InterSystems IRIS. The inner workings of InterSystems IRIS are extensive and powerful. There are industry-leading features for integrating healthcare systems and transforming data that are not touched upon in this series. There is also a suite for creating analytics dashboards directly on the data being used. 

In-depth programming with all of the features of InterSystems IRIS benefits from knowledge of InterSystems IRIS Classes and some knowledge of ObjectScript. However, there are still many valuable aspects of InterSystems IRIS that can be accessed through external applications as shown here. 

If you are interested in going into depth with InterSystems IRIS, there are many learning courses available on the [InterSystems Learning Services platform](https://learning.intersystems.com). It's a steep learning curve, but highly fulfilling and provides access to an incredibly powerful data platform. 

AI coding agents are also able to flatten this learning curve, so if you do need features revolving around connecting different health systems or transforming data in a structured and audited way, do not be afraid to ask your coding agent of choice for help on this. The effectiveness of coding agents can also be dramatically improved by equipping it with the [iris-agentic-dev](https://github.com/intersystems-community/iris-agentic-dev) MCP Server to give access to InterSystems IRIS. This will be less useful for the Python uses shown in this tutorial series though. 


## Setup

### Pre-requisites

- Python
- [Docker](https://www.docker.com/get-started/) 
- An [OpenAI API Key](https://platform.openai.com/api-keys) with some credit. Running every step of these tutorials with the current models should cost less than $0.01. You can use other LLM/embedding providers, although information on switching is not provided.  

### Start InterSystems IRIS for Health 

**Before running any of the tutorials, you will need to have Docker installed and running on your system**. You can then begin by running the InterSystems IRIS for Health container by executing the setup script available at [docker-iris-fhir/start.sh](./docker-iris-fhir/start.sh) (or the equivalent PowerShell script if you are a Windows Powershell user). 

```sh
./docker-iris-fhir/start.sh
```

You will also need Python installed on your system, and need to install the required libraries. It's recommended that you use a virtual environment for this: 

- Linux/Mac users: 
```
python3 -m venv .venv
source .venv/bin/activate
```

- Windows PowerShell Users

```
python3 -m venv .venv
./.venv/Scripts/activate
```

- Windows GitBash Users:

```
python3 -m venv .venv 
source .venv/Scripts/activate
```

Then install dependencies: 

```sh
pip install -r requirements.txt
```

Finally, copy [.env.example](./.env.example) to a file called `.env` in the root of this repository and replace the placeholder with your OpenAI API key. All the tutorials and scripts that call OpenAI read the key from this file.

```sh
cp .env.example .env
```

## Tutorial Series Overview

This tutorial series spans 3 main data-types: 
- Tabular Data (CSVs and SQL)
- FHIR Data (healthcare data standard)
- Vector data (for use with Vector search)

For CSV and FHIR data, there are separate tutorials to cover the loading of data into InterSystems IRIS, and the querying of this data. For Vector data, this is combined into a single tutorial on vector search. 

Following the data loading there are also tutorials on using AI Agents and creating MCP servers around our data access. These later tutorials make use of the data created in earlier tutorials, so you should either run through the earlier tutorials, or run the Python table [setup scripts](./Tutorials/setup-scripts/) which perform the same steps. 

Each of the tutorials are IPython (Jupyter) notebooks. These are notebooks which use a continuous Python kernel with executable "cells" containing code. The variables created in this notebook stay in memory, meaning the tutorial can be run interactively, with instructions in-line with code. 


# Table Of Contents

### 0. Key Concepts
- [0.0 Introduction to InterSystems IRIS](./Tutorials/0-key-concepts/0-what-is-IRIS.md)
- [0.1 Brief Intro to FHIR](./Tutorials/0-key-concepts/0.1-what-is-fhir.md)
- [0.2 What are Docker Containers?](./Tutorials/0-key-concepts/0.2-what-is-docker.md)
- [0.3 Brief Introduction to Retrieval Augmented Generation](./Tutorials/0-key-concepts/0.3-what-is-vector-search.md)

### 1. Setup
- [1.1 Setting Up the Environment](./Tutorials/1-setup/1.1-setup-iris-and-fhir.md)

### 2. Tabular Data
- [2.1 Load CSV Data to InterSystems IRIS with Python](./Tutorials/2-tabular/2.1-load-csv-data.ipynb)
- [2.2 Querying SQL Data with Python](./Tutorials/2-tabular/2.2-querying-sql-tables-with-python.ipynb)

### 3. FHIR Data
- [3.1 Adding FHIR data to a FHIR server](./Tutorials/3-fhir/3.1-load-fhir-data.ipynb)
- [3.2 Accessing FHIR resources](./Tutorials/3-fhir/3.2-querying-fhir-data-with-python.ipynb)
- [3.3 Viewing the FHIR Specification with Swagger](./Tutorials/3-fhir/3.3-viewing-fhir-specification-with-swagger.md)
- [3.4 Creating Synthetic FHIR data](./Tutorials/6-extras/create-synthetic-fhir-data.md)

### 4. Vector Search
- [4.1 Vector Search](./Tutorials/4-vector-search/4.1-vector-search.ipynb)

### 5. AI
- [5.1 Creating agents](./Tutorials/5-ai/5.1-agents-and-tools.ipynb)
- [5.2 Building MCP Servers](./Tutorials/5-ai/5.2-mcp-server.ipynb)

### 6. Extras
- [Create a FHIR Server in 5 minutes with IRIS Health Community](./Tutorials/6-extras/CreateAFHIRServerIn5Minutes.md)

- [Integrated Machine Learning Quickstart](./Tutorials/6-extras/ML-predictions-made-simple.md)

