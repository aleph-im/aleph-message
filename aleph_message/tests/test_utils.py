from datetime import datetime, date, time

import pytest
from pydantic import BaseModel

from aleph_message.utils import Gigabytes, gigabyte_to_mebibyte, extended_json_encoder, dump_content


def test_gigabyte_to_mebibyte():
    assert gigabyte_to_mebibyte(Gigabytes(1)) == 954
    assert gigabyte_to_mebibyte(Gigabytes(100)) == 95368


def test_extended_json_encoder():
    now = datetime.now()
    today = date.today()
    now_time = time(hour=1, minute=2, second=3, microsecond=4)
    assert extended_json_encoder(now) == now.timestamp()
    assert extended_json_encoder(today) == today.toordinal()
    assert extended_json_encoder(now_time) == 3723.000004


def test_dump_content():
    class TestModel(BaseModel):
        address: str
        time: float

    assert dump_content({"address": "0x1", "time": 1.0}) == '{"address":"0x1","time":1.0}'
    assert dump_content(TestModel(address="0x1", time=1.0)) == '{"address":"0x1","time":1.0}'


@pytest.mark.parametrize(
    "content",
    [
        1,
        "test",
        None,
        True,
    ],
)
def test_dump_content_invalid(content):
    with pytest.raises(TypeError):
        dump_content(content)
