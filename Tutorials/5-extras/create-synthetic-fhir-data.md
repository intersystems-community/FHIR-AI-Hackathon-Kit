# Creating Synthetic FHIR data

You can create synthetic FHIR data using [Synthea](https://synthetichealth.github.io/synthea/#home), this is a standard way to create genuine looking data without having to worry about protecting any personal information.

To make this very simple, the InterSystems Developer Community have put this into a docker container so it can be easily run from anywhere with docker. Just run: 

    docker run --rm -v $PWD/output:/output --name synthea-docker intersystemsdc/irisdemo-base-synthea:version-1.3.4 -p 100

where the -p flag denotes the number of synthetic patients to generate - in this case 100. 

The --rm flag tells docker to remove the container once it's run, so this can be used as a standalone command. 

The result is a new folder called output/fhir is generated wherever you ran the command, this is filled with patient bundles with complete (synthetic) medical histories, as well as the hospital and practitioner bundles that are referred to by the patient bundles. 

You can add these bundles onto the FHIR server using an HTTP request, which can be performed in Python (among other ways). Details are shown in [Adding-FHIR-data-to-IRIS-health](update-link) tutorial. 

