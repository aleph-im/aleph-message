FROM ubuntu:20.04
RUN apt-get update && apt-get install -y python3-pip

RUN pip install pytest requests types-requests pytest-cov mypy twine typing-extensions
COPY . /opt/aleph-message
WORKDIR /opt/aleph-message
RUN pip install -e .
RUN pip install mypy ruff black