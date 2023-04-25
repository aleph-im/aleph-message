FROM python:3.9-bullseye

RUN pip install pydantic pytest pytest-cov mypy requests twine typing-extensions
RUN mypy --install-types aleph_message

COPY aleph_message /opt/aleph_message
WORKDIR /opt
