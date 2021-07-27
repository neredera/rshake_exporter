FROM python:3-slim

COPY install-packages.sh .
RUN ./install-packages.sh

RUN pip3 install prometheus_client PyParsing

ADD exporter.py /usr/local/bin/rshake_exporter

EXPOSE 9984/tcp

ENTRYPOINT [ "/usr/local/bin/rshake_exporter" ]
