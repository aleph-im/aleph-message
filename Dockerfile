FROM python:3.9-bullseye

COPY aleph_message /opt/aleph_message
RUN pip install /opt/aleph-message[testing]
WORKDIR /opt
