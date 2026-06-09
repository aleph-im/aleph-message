import base64

import pytest
from pydantic import ValidationError

from aleph_message.models import StoreContent

IPNS_NAME = "k51qzi5uqu5dlvj2baxnqndepeb86cbk3ng7n3i46uzyxzyqj2xjonzllnv0v8"
ADDRESS = "0xA07B1214bAe0D5ccAA25449C3149c0aC83658874"
FILE_CID = "QmPZ9gcCEpqKTo6aq61g2nXGUhM4iCL3ewB6LDXZCtioEB"
RECORD_B64 = base64.b64encode(b"\x0a\x01fake-ipns-record").decode()


def _ipns_content(**overrides):
    fields = {
        "address": ADDRESS,
        "time": 1780000000.0,
        "item_type": "ipns",
        "item_hash": IPNS_NAME,
        "max_size_mib": 100,
    }
    fields.update(overrides)
    return StoreContent.model_validate(fields)


def test_ipns_store_with_record():
    content = _ipns_content(ipns_record=RECORD_B64)
    assert content.ipns_record == RECORD_B64
    assert content.max_size_mib == 100


def test_ipns_store_track_only():
    content = _ipns_content()
    assert content.ipns_record is None


def test_ipns_store_requires_max_size_mib():
    with pytest.raises(ValidationError, match="max_size_mib"):
        _ipns_content(max_size_mib=None)


def test_ipns_store_forbids_ref():
    with pytest.raises(ValidationError, match="ref"):
        _ipns_content(ref="7f2d09b2c4e1a8f3d6b5c2e9a1f4d7b8e3c6a9f2d5b8e1c4a7f0d3b6e9c2a5f8")


def test_ipns_record_must_be_base64():
    with pytest.raises(ValidationError, match="base64"):
        _ipns_content(ipns_record="not!base64@@")


def test_ipns_record_size_cap():
    huge = base64.b64encode(b"x" * 10241).decode()
    with pytest.raises(ValidationError, match="size"):
        _ipns_content(ipns_record=huge)


def test_non_ipns_store_forbids_ipns_fields():
    fields = {
        "address": ADDRESS,
        "time": 1780000000.0,
        "item_type": "ipfs",
        "item_hash": FILE_CID,
    }
    with pytest.raises(ValidationError):
        StoreContent.model_validate({**fields, "ipns_record": RECORD_B64})
    with pytest.raises(ValidationError):
        StoreContent.model_validate({**fields, "max_size_mib": 100})


def test_plain_store_unaffected():
    content = StoreContent.model_validate(
        {
            "address": ADDRESS,
            "time": 1780000000.0,
            "item_type": "ipfs",
            "item_hash": FILE_CID,
        }
    )
    assert content.ipns_record is None
    assert content.max_size_mib is None
