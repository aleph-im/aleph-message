FROM python:3.9-bullseye

RUN pip install pydantic pytest pytest-cov mypy requests twine typing-extensions types-requests

COPY aleph_message /opt/aleph_message
WORKDIR /opt
