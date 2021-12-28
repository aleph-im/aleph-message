import json
import os.path
from hashlib import sha256
from os import listdir
from os.path import join, isdir
from pprint import pprint

import pytest
import requests
from pydantic import ValidationError

from aleph_message.models import MessagesResponse, Message, ProgramMessage, ForgetMessage, \
    PostContent
from aleph_message.tests.download_messages import MESSAGES_STORAGE_PATH

ALEPH_API_SERVER = "https://api2.aleph.im"

HASHES_TO_IGNORE = (
    "2fe5470ebcc5b6168b778ca3baadfd1618dc3acdb0690478760d21ff24b03164",
    "1c0ce828b272fd9929e1dd6f665a4f845110b72a6aba74daa84a17e89da3718c",
)


def test_message_response_aggregate():
    path = "/api/v0/messages.json?hashes=9b21eb870d01bf64d23e1d4475e342c8f958fcd544adc37db07d8281da070b00&addresses=0xa1B3bb7d2332383D96b7796B908fB7f7F3c2Be10&msgType=AGGREGATE"
    data_dict = requests.get(f"{ALEPH_API_SERVER}{path}").json()

    response = MessagesResponse(**data_dict)
    assert response


def test_message_response_post():
    path = "/api/v0/messages.json?hashes=6e5d0c7dce83bfd4c5d113ef67fbc0411f66c9c0c75421d61ace3730b0d1dd0b&addresses=0xa1B3bb7d2332383D96b7796B908fB7f7F3c2Be10&msgType=POST"
    data_dict = requests.get(f"{ALEPH_API_SERVER}{path}").json()

    response = MessagesResponse(**data_dict)
    assert response


def test_message_response_store():
    path = "/api/v0/messages.json?hashes=53c9317457d2d3caa205748917bc116921f4e8313e830c1c05c6eb6e2d9d9305&addresses=0x231a2342b7918129De0b910411378E22379F69b8&msgType=STORE"
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


def test_post_content():
    """Test that a mistake in the validation of the POST content 'type' field is fixed.
     Issue reported on 2021-10-21 on Telegram.
     """
    custom_type = "arbitrary_type"
    p1 = PostContent(
        type=custom_type,
        address="0x1",
        content={"blah": "bar"},
        time=1.,
    )
    assert p1.type == custom_type

    with pytest.raises(ValueError):
        PostContent(
            type="amend",
            address="0x1",
            content={"blah": "bar"},
            time=1.,
            # 'ref' field is missing from an amend
        )

    # 'ref' field is present on an amend
    PostContent(
        type="amend",
        address="0x1",
        content={"blah": "bar"},
        time=1.,
        ref='0x123',
    )


def test_message_machine():
    path = os.path.abspath(os.path.join(__file__, "../messages/machine.json"))
    with open(path) as fd:
        message_raw = json.load(fd)

    message_raw['item_hash'] = sha256(json.dumps(message_raw['content']).encode()).hexdigest()
    message_raw['item_content'] = json.dumps(message_raw['content'])
    message = ProgramMessage(**message_raw)
    assert message

    message2 = Message(**message_raw)
    assert message == message2

    assert hash(message.content)


def test_message_machine_named():
    path = os.path.abspath(os.path.join(__file__, "../messages/machine_named.json"))
    with open(path) as fd:
        message_raw = json.load(fd)

    message_raw['item_hash'] = sha256(json.dumps(message_raw['content']).encode()).hexdigest()
    message_raw['item_content'] = json.dumps(message_raw['content'])
    message = ProgramMessage(**message_raw)
    assert message.content.metadata['version'] == '10.2'


def test_message_forget():
    path = os.path.abspath(os.path.join(__file__, "../messages/forget.json"))
    with open(path) as fd:
        message_raw = json.load(fd)

    message_raw['item_hash'] = sha256(json.dumps(message_raw['content']).encode()).hexdigest()
    message_raw['item_content'] = json.dumps(message_raw['content'])
    message = ForgetMessage(**message_raw)
    assert message
    message2 = Message(**message_raw)
    assert message == message2

    assert hash(message.content)

    # A FORGET message may not be forgotten:
    message_raw["forgotten_by"] = ['abcde']
    with pytest.raises(ValueError) as e:
        ForgetMessage(**message_raw)
    assert e.value.args[0][0].exc.args == ("This type of message may not be forgotten", )


def test_message_forgotten_by():
    path = os.path.abspath(os.path.join(__file__, "../messages/machine.json"))
    with open(path) as fd:
        message_raw = json.load(fd)
    message_raw['item_hash'] = sha256(json.dumps(message_raw['content']).encode()).hexdigest()
    message_raw['item_content'] = json.dumps(message_raw['content'])

    # Test different values for field 'forgotten_by'
    _ = ProgramMessage(**message_raw)
    _ = ProgramMessage(**message_raw, forgotten_by=None)
    _ = ProgramMessage(**message_raw, forgotten_by=['abcde'])
    _ = ProgramMessage(**message_raw, forgotten_by=['abcde', 'fghij'])


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
