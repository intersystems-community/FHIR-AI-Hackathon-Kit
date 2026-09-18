FROM intersystems/irishealth-community:latest-cd



ENV IRISINSTALLDIR=/usr/irissys
ENV PATH="${PATH}:${IRISINSTALLDIR}/bin"
ENV PYTHONPATH="${IRISINSTALLDIR}/lib/python"
ENV IRISNAMESPACE=USER
ENV IRISUSERNAME=SuperUser
ENV IRISPASSWORD=SYS

RUN echo 'alias python="irispython"' >> ~/.bashrc


RUN mkdir -p /home/irisowner/dev
WORKDIR /home/irisowner/dev
COPY . .

USER root

RUN mkdir -p /durable && \
    chown irisowner:irisowner /durable/ -R

RUN mkdir /opt/fhir && \ 
    chown irisowner:irisowner /opt/fhir -R

USER irisowner

COPY ./data/fhir /opt/fhir/data/


RUN iris start IRIS &&\
    iris merge IRIS merge.cpf && \
    iris stop IRIS quietly

