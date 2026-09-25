# Introduction to the InterSystems FHIR/AI Hackathon Kit 


This kit is a set of tutorials to demonstrate how users can build applications with InterSystems IRIS for Health, using FHIR data, Python and AI Agents. This is designed to be a fast entrypoint to using InterSystems IRIS with Python and AI. 

## Introduction to InterSystems IRIS 

InterSystems IRIS is a data platform, meaning it is a platform to build applications around data. Data is stored within one of the fastest, most efficient and flexible databases available. The flexibility from IRIS comes from the native multi-model data structure, meaning it can act as a SQL database, but can also store data as objects, key-value pairs, documents, vectors and more. 

InterSystems IRIS for Health is an extension to InterSystems IRIS, providing additional support for HealthCare data and systems. This includes a FHIR Server, as well as support for HL7, CDA, X12 and many other types. 

All of these features are built with security, concurrency, auditing and support for many users to access the data simultaneously. Making it a powerful platform to build to the worlds most important applications. 

This series uses the Community Edition of InterSystems IRIS for Health, which is free to use and has no major code differences to the licensed version. It does come with [limits on its use](). 

## What this tutorial series is

This tutorial series is a demonstration of how to build applications using Python which include an InterSystems IRIS For Health server as the backend. There is a docker template which sets up InterSystems IRIS For Health with a **FHIR server**. This is followed by a series of tutorials on how to access or add data to the FHIR Server or to the SQL database from Python Application. 

The tutorials also cover using **vector data** for fast semantic matching. This is a very effective way to build searches against unlabelled, unstructured data. It is particularly effective when combined with AI Agents. 

Finally, the tutorials cover building basic AI Agents which can access the data from the InterSystems IRIS for Health instance, including building MCP servers to provide access to existing agents. 

These tutorials are designed to be a rapid quickstart for you to include InterSystems IRIS into your applications.

## What this tutorial series is **Not**

This series is not an in-depth look at InterSystems IRIS. The inner workings of InterSystems IRIS are extensive and powerful. There are industry-leading features for integrating healthcare systems and transforming data that are not touched upon in this series. There is also a suite for creating analytics dashboards directly on the data being used. 

In-depth programming with all of the features InterSystems IRIS provides benefits from knowledge InterSystems IRIS Classes and some knowledge of ObjectScript. However, there are still many valuable aspects of InterSystems IRIS that can be accessed through external applications as shown here. 

If you are interested in going into depth with InterSystems IRIS, there are many learning courses available on the [InterSystems Learning Services platform](https://learning.intersystems.com). Its a steep learning curve, but highly fulfilling and provides access to an incredibly powerful data platform. 

AI coding agents are also able to flatten this learning curve, so if you do need features revolving around connecting different health systems or transforming data in a structured and audited way, do not be afraid to ask you coding agent of choice for help on this. The effectiveness of coding agents can also be dramatically improved by equipping it the [iris-agentic-dev](https://github.com/intersystems-community/iris-agentic-dev) MCP Server to give access to InterSystems IRIS. This will be less useful for the Python uses shown in this tutorial series though. 


## Setup

### Pre-requisites

- Python
- [Docker]() 
- An [OpenAI API Key]() with some credit. Running every step of these tutorials with the current models should cost less than $0.01. You can use other LLM/embedding providers, although information on switching is not provided.  

Before running any of the tutorials, you will need to have Docker installed and running on your system. You can then begin by running the InterSystems IRIS for Health container by executing the setup script available at (docker-iris-fhir/setup.sh)[./docker-iris-fhir/setup.sh] (or the equivalent PowerShell script if you are a Windows Powershell user). 

```sh
./docker-iris-fhir/setup.sh
```

You will also need Python installed on your system, and need to install the required libraries. Its recommended that you use a virtual environment for this: 

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

## Tutorial Series Overview

This tutorial series spans 3 main data-types: 
- Tabular Data (CSVs and SQL)
- FHIR Data (healthcare data standard)
- Vector data (for use with Vector search)

For CSV and FHIR data, there are separate tutorials to cover the loading of data into InterSystems IRIS, and the querying of this data. For Vector data, this is combined into a single tutorial on vector search. 

Following the data loading there are also tutorials on using AI Agents and creating MCP servers around our data access. These later tutorials make use of the data created in earlier tutorials, so you should either run through the earlier tutorials, or run the Python table Setup scripts which perform the same steps. 

Each of the tutorials are IPython (Jupyter) notebooks. These are notebooks which use a continuous Python kernel with executable "cells" containing code. The variables created in this notebook stay in memory, meaning the tutorial can be run interactively, with instructions in-line with code. 
