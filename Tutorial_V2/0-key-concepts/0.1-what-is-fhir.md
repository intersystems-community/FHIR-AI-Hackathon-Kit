# Brief Intro to FHIR

Fast Healthcare Interoperability Resources (FHIR) is a global Healthcare data standard that is increasingly widely used. It is the most recent of a number of healthcare standards produced by HL7. 

FHIR is based on `Resources` , these are small packets of specific information that are important to healthcare uses. These are modular units of structured data, each representing a specific healthcare concept (e.g. Patient, Observation, medication). They are easily parsed, validated and exchanged between systems and machines.

For example a Patient resource may contain:
 - Patients Name
 - Address
 - Date of birth
 - Gender
 
 but no clinical information like Allergies. Allergies would be stored in a separate resource called AllergyIntolerance. This would have

 - Intolerance Type, including medical codes
 - Date of last reaction
 - Subject reference (i.e. patient ID)

as well as some other specific information about that allergy. 

## Bundles

FHIR resources are designed to be combined into Bundles, this is a set of related resources which can be sent together. For example, the result of an X-Ray may be sent from the Radiologist lab to a surgeon via a bundle of FHIR resources containing the following resources (as a made-up example):

- Patient (contains patient information)
- ImagingStudy (contains information about the imaging)
- Binary (contains the images collected)
- DiagnosticReport (Summary of findings)
- Practitioner (contains radiologist information)
- Organization (Hospital details)


## REST

FHIR data is stored on a FHIR server, which can be accessed by Representational State Transfer, or REST. This is a standard internet protocol, which you may be more familiar with than you think you are. 

Each FHIR resource has a specific location, or URL. A FHIR server can be queried using HTTP requests like GET, POST, PUT and DELETE. Search parameters can also be added to the URL to allow you to search for specific resources. 

FHIR data is generally sent in JSON or XML format. 

## More Info:

- [HL7 FHIR: What is it really? (VIDEO)](https://www.youtube.com/watch?v=AkqNuxVBQKY)
- [HL7 FHIR website](https://www.hl7.org/fhir/)
- [List of FHIR resources](https://www.hl7.org/fhir/resourcelist.html)
- [SMART tools and information](https://smarthealthit.org/)
- [Tools for validating and working with FHIR](https://www.hl7.org/fhir/tools.html)