# Brief introduction to InterSystems IRIS

InterSystems IRIS is a data-platform that has data stored in multi-dimensional arrays called Globals. Globals are hierarchical key-value data structures that allow extremely fast access and updates. They underpin all data models in IRIS and are particularly well-suited for high-throughput transactional systems. These arrays are multi-model as they can be viewed in a relational table format (queried with Structured Query Language, SQL) or natively through an object model. 

IRIS includes many features and tools that are operational close to the database, meaning they function very well. IRIS is excellent at creating Interoperability productions, which ingest data from one point, process it based on some rules, and perform downstream operations. There are also built in tools for machine learning, and performing rapid vector searching on the database which is a key part of creating [RAG chatbots](what-is-RAG.md).

IRIS has server-side support for its own language, ObjectScript as well as Embedded Python. Using IRIS in this way allows the application to be very close to the data, making it perform efficiently and well. 

IRIS can be also accessed externally by multiple languages as well as REST APIs. There are currently software development kits (SDKs) for Python, .Net and Java. This repository is focussed on using IRIS with external Python applications, but equivalents can be made with the other languages listed



## IRIS for Health

IRIS for health extends InterSystems IRIS with built-in healthcare functionality. This includes creating and managing FHIR servers, and working with many different healthcare data formats at the same time. There are many features built into IRIS for Health which makes it such an effective data platform for healthcare data. These features are why solutions based on InterSystems technology currently manage over a Billion patients healthcare records. 


## More info 


For more information visit: 

- https://www.intersystems.com/
- [What is IRIS? (VIDEO)](https://www.youtube.com/watch?v=w2OeWx3WNOs)


For Healthcare specific information: 

- https://www.intersystems.com/products/intersystems-iris-for-health/
- [what is IRIS for health? (VIDEO)](https://www.youtube.com/watch?v=drdAp2V5U8A)

For Developer Specific information:

- [Developer onboarding](https://developer.intersystems.com/intersystems-iris-getting-started/)
- [Developer Community](https://community.intersystems.com/)
- [Documentation](https://docs.intersystems.com)
- [Intersystems Courses](https://learning.intersystems.com)
- [Community Applications](https://openexchange.intersystems.com/)