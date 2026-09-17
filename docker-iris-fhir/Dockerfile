FROM intersystems/irishealth-community:latest-cd

COPY ./data/fhir /tmp/fhir

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

USER irisowner


RUN iris start IRIS &&\
    iris merge IRIS merge.cpf && \
    iris stop IRIS quietly

