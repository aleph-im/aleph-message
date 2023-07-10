FROM python:3.9-bullseye

COPY . /opt/aleph-message
RUN cd /opt/aleph-message && pip install -e .[testing]
WORKDIR /opt
