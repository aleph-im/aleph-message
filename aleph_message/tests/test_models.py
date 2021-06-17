import json
import os.path
from os import listdir
from os.path import join, isdir
from pprint import pprint

import pytest as pytest
import requests
from pydantic import ValidationError

from aleph_message.models import MessagesResponse, Message, ProgramMessage
from aleph_message.tests.download_messages import MESSAGES_STORAGE_PATH

ALEPH_API_SERVER = "https://api2.aleph.im"

HASHES_TO_IGNORE = (
    "2fe5470ebcc5b6168b778ca3baadfd1618dc3acdb0690478760d21ff24b03164",
    "1c0ce828b272fd9929e1dd6f665a4f845110b72a6aba74daa84a17e89da3718c",
)


def test_message_response_aggregate():
    path = "/api/v0/messages.json?hashes=9b21eb870d01bf64d23e1d4475e342c8f958fcd544adc37db07d8281da070b00&chain=ETH&addresses=0xa1B3bb7d2332383D96b7796B908fB7f7F3c2Be10&msgType=AGGREGATE"
    data_dict = requests.get(f"{ALEPH_API_SERVER}{path}").json()

    response = MessagesResponse(**data_dict)
    assert response


def test_message_response_post():
    path = "/api/v0/messages.json?hashes=6e5d0c7dce83bfd4c5d113ef67fbc0411f66c9c0c75421d61ace3730b0d1dd0b&chain=ETH&addresses=0xa1B3bb7d2332383D96b7796B908fB7f7F3c2Be10&msgType=POST"
    data_dict = requests.get(f"{ALEPH_API_SERVER}{path}").json()

    response = MessagesResponse(**data_dict)
    assert response


def test_message_response_store():
    path = "/api/v0/messages.json?hashes=53c9317457d2d3caa205748917bc116921f4e8313e830c1c05c6eb6e2d9d9305&chain=ETH&addresses=0x231a2342b7918129De0b910411378E22379F69b8&msgType=STORE"
    data_dict = requests.get(f"{ALEPH_API_SERVER}{path}").json()

    response = MessagesResponse(**data_dict)
    assert response


def test_messages_last_page():
    path = "/api/v0/messages.json"

    page = 1
    response = requests.get(f"{ALEPH_API_SERVER}{path}?page={page}")
    response.raise_for_status()
    data_dict = response.json()

    for message_dict in data_dict["messages"]:
        if message_dict["item_hash"] in HASHES_TO_IGNORE:
            continue
        try:
            message = Message(**message_dict)
            assert message
        except:
            raise


def test_message_machine():
    path = os.path.abspath(os.path.join(__file__, "../messages/machine.json"))
    with open(path) as fd:
        message_raw = json.load(fd)

    message_raw['item_content'] = json.dumps(message_raw['content'])
    message = ProgramMessage(**message_raw)
    assert message

    assert hash(message.content)


@pytest.mark.skipif(not isdir(MESSAGES_STORAGE_PATH), reason="No file on disk to test")
def test_messages_from_disk():
    for messages_page in listdir(MESSAGES_STORAGE_PATH):
        with open(join(MESSAGES_STORAGE_PATH, messages_page)) as page_fd:
            data_dict = json.load(page_fd)
        for message_dict in data_dict["messages"]:
            try:
                message = Message(**message_dict)
                assert message
            except ValidationError as e:
                pprint(message_dict)
                print(e.json())
                raise
