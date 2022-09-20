#!/bin/sh

set -euf

podman build --loglevel 3 -t aleph-message .
podman run --rm -ti -v $(pwd)/aleph_message:/opt/aleph_message aleph-message pytest -vv
podman run --rm -ti -v $(pwd)/aleph_message:/opt/aleph_message aleph-message mypy --ignore-missing-imports aleph_message
