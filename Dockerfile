FROM python:3.9-bullseye

COPY aleph_message /opt/aleph_message
RUN cd /opt/aleph_message && pip install .[testing]
WORKDIR /opt
