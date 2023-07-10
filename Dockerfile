FROM python:3.9-bullseye

RUN pip install pytest pytest-cov mypy twine typing-extensions
COPY . /opt/aleph-message
WORKDIR /opt/aleph-message
RUN pip install -e .
