FROM python:3.9-buster

RUN pip install pydantic pytest requests

COPY aleph_message /opt/aleph_message
WORKDIR /opt