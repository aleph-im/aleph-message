FROM python:3.12
RUN apt-get update && apt-get install -y python3-pip

RUN pip install types-requests mypy twine typing-extensions hatch
COPY . /opt/aleph-message
WORKDIR /opt/aleph-message
RUN pip install .
