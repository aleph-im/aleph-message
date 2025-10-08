import json
import os.path
from os import listdir
from os.path import isdir, join
from pathlib import Path
from unittest import mock

import pytest
import requests
from pydantic import ValidationError
from rich.console import Console

from aleph_message.exceptions import UnknownHashError
from aleph_message.models import (
    AggregateMessage,
    ForgetMessage,
    InstanceContent,
    InstanceMessage,
    ItemType,
    MessagesResponse,
    MessageType,
    PaymentType,
    PostContent,
    PostMessage,
    ProgramMessage,
    add_item_content_and_hash,
    create_message_from_file,
    create_message_from_json,
    create_new_message,
    parse_message,
)
from aleph_message.models.execution.environment import AMDSEVPolicy, HypervisorType
from aleph_message.tests.download_messages import MESSAGES_STORAGE_PATH

console = Console(color_system="windows")

ALEPH_API_SERVER = "https://api2.aleph.im"

HASHES_TO_IGNORE = (
    "2fe5470ebcc5b6168b778ca3baadfd1618dc3acdb0690478760d21ff24b03164",
    "1c0ce828b272fd9929e1dd6f665a4f845110b72a6aba74daa84a17e89da3718c",
)


def test_message_response_aggregate():
    path = (
        "/api/v0/messages.json?hashes=9b21eb870d01bf64d23e1d4475e342c8f958fcd544adc37db07d8281da070b00"
        "&addresses=0xa1B3bb7d2332383D96b7796B908fB7f7F3c2Be10&msgType=AGGREGATE"
    )
    data_dict = requests.get(f"{ALEPH_API_SERVER}{path}").json()

    message = data_dict["messages"][0]
    AggregateMessage.model_validate(message)

    response = MessagesResponse.model_validate(data_dict)
    assert response


def test_message_response_post():
    path = (
        "/api/v0/messages.json?hashes=6e5d0c7dce83bfd4c5d113ef67fbc0411f66c9c0c75421d61ace3730b0d1dd0b"
        "&addresses=0xa1B3bb7d2332383D96b7796B908fB7f7F3c2Be10&msgType=POST"
    )
    data_dict = requests.get(f"{ALEPH_API_SERVER}{path}").json()

    response = MessagesResponse.model_validate(data_dict)
    assert response


def test_message_response_store():
    path = (
        "/api/v0/messages.json?hashes=53c9317457d2d3caa205748917bc116921f4e8313e830c1c05c6eb6e2d9d9305"
        "&addresses=0x231a2342b7918129De0b910411378E22379F69b8&msgType=STORE"
    )
    data_dict = requests.get(f"{ALEPH_API_SERVER}{path}").json()

    response = MessagesResponse.model_validate(data_dict)
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

        message = parse_message(message_dict)
        assert message


def test_post_content():
    """Test that a mistake in the validation of the POST content 'type' field is fixed.
    Issue reported on 2021-10-21 on Telegram.
    """
    custom_type = "arbitrary_type"
    p1 = PostContent(
        type=custom_type,
        address="0x1",
        content={"blah": "bar"},
        time=1.0,
    )
    assert p1.type == custom_type
    assert p1.model_dump() == {
        "address": "0x1",
        "time": 1.0,
        "content": {"blah": "bar"},
        "ref": None,
        "type": "arbitrary_type",
    }

    with pytest.raises(ValueError):
        PostContent(
            type="amend",
            address="0x1",
            content={"blah": "bar"},
            time=1.0,
            # 'ref' field is missing from an amend
        )

    # 'ref' field is present on an amend
    PostContent(
        type="amend",
        address="0x1",
        content={"blah": "bar"},
        time=1.0,
        ref="0x123",
    )


def test_message_machine():
    path = Path(__file__).parent / "messages/machine.json"
    message = create_message_from_file(path, factory=ProgramMessage)

    assert isinstance(message, ProgramMessage)
    assert hash(message.content)

    assert create_message_from_file(path)


def test_instance_message_machine():
    path = Path(__file__).parent / "messages/instance_machine.json"
    message = create_message_from_file(path, factory=InstanceMessage)

    assert isinstance(message, InstanceMessage)
    assert hash(message.content)


def test_instance_message_machine_with_confidential_options():
    path = Path(__file__).parent / "messages/instance_confidential_machine.json"
    message = create_message_from_file(path, factory=InstanceMessage)

    assert isinstance(message, InstanceMessage)
    assert hash(message.content)
    assert message.content.environment.trusted_execution
    assert message.content.environment.trusted_execution.policy == AMDSEVPolicy.NO_DBG
    assert (
        message.content.environment.trusted_execution.firmware
        == "e258d248fda94c63753607f7c4494ee0fcbe92f1a76bfdac795c9d84101eb317"
    )
    assert message.content.requirements and message.content.requirements.node
    assert (
        message.content.requirements.node.node_hash
        == "4d4db19afca380fdf06ba7f916153d0f740db9de9eee23ad26ba96a90d8a2920"
    )


def test_validation_on_confidential_options():
    """Ensure that a trusted environment is only allowed for QEmu."""
    path = Path(__file__).parent / "messages/instance_confidential_machine.json"
    message_dict = json.loads(path.read_text())
    # Patch the hypervisor to be something other than QEmu
    message_dict["content"]["environment"]["hypervisor"] = HypervisorType.firecracker
    try:
        _ = create_new_message(message_dict, factory=InstanceMessage)
        raise AssertionError("An exception should have been raised before this point.")
    except ValidationError as e:
        assert e.errors()[0]["loc"] == ("content", "environment", "trusted_execution")
        assert (
            e.errors()[0]["msg"]
            == "Value error, Trusted Execution Environment is only supported for QEmu"
        )


def test_instance_message_machine_with_gpu_options():
    path = Path(__file__).parent / "messages/instance_gpu_machine.json"
    message = create_message_from_file(path, factory=InstanceMessage)

    assert isinstance(message, InstanceMessage)
    assert hash(message.content)
    assert message.content.payment
    assert message.content.payment.type == PaymentType.superfluid
    assert message.content.environment.hypervisor == HypervisorType.qemu


def test_validation_on_gpu_payment_options():
    """Ensure that a gpu option is only allowed for stream payments."""
    path = Path(__file__).parent / "messages/instance_gpu_machine.json"
    message_dict = json.loads(path.read_text())
    # Patch the gpu field with some info
    message_dict["content"]["payment"]["type"] = "hold"
    message_dict["content"]["payment"]["receiver"] = None
    message = create_new_message(message_dict, factory=InstanceMessage)

    assert isinstance(message, InstanceMessage)
    assert hash(message.content)
    assert message.content.payment
    assert message.content.payment.type == PaymentType.hold
    assert message.content.environment.hypervisor == HypervisorType.qemu

    # Require node_hash field for GPU support
    message_dict["content"]["requirements"]["node"] = None
    try:
        _ = create_new_message(message_dict, factory=InstanceMessage)
        raise AssertionError("An exception should have been raised before this point.")
    except ValidationError as e:
        assert e.errors()[0]["loc"] in [("content",), ("content", "__root__")]

        error_msg = e.errors()[0]["msg"]
        assert (
            "Node hash assignment is needed for GPU support" in error_msg
        )  # Ignore "Value error, ..."


def test_validation_on_gpu_hypervisor_options():
    """Ensure that a gpu option is only allowed for Qemu hypervisor."""
    path = Path(__file__).parent / "messages/instance_gpu_machine.json"
    message_dict = json.loads(path.read_text())
    # Patch the gpu field with some info
    message_dict["content"]["environment"]["hypervisor"] = HypervisorType.firecracker
    try:
        _ = create_new_message(message_dict, factory=InstanceMessage)
        raise AssertionError("An exception should have been raised before this point.")
    except ValidationError as e:
        assert e.errors()[0]["loc"] in [("content",), ("content", "__root__")]

        error_msg = e.errors()[0]["msg"]
        assert (
            "GPU option is only supported for QEmu hypervisor" in error_msg
        )  # Ignore "Value error, ..."


def test_validation_on_payg_payment_options():
    """Ensure that a node_hash option is required for stream payments."""
    path = Path(__file__).parent / "messages/instance_gpu_machine.json"
    message_dict = json.loads(path.read_text())
    message_dict["content"]["requirements"]["gpu"] = None
    message = create_new_message(message_dict, factory=InstanceMessage)

    assert isinstance(message, InstanceMessage)
    assert hash(message.content)
    assert message.content.payment
    assert message.content.payment.type == PaymentType.superfluid
    assert message.content.environment.hypervisor == HypervisorType.qemu

    message_dict["content"]["requirements"]["node"] = None
    try:
        _ = create_new_message(message_dict, factory=InstanceMessage)
        raise AssertionError("An exception should have been raised before this point.")
    except ValidationError as e:
        assert e.errors()[0]["loc"] in [("content",), ("content", "__root__")]

        error_msg = e.errors()[0]["msg"]
        assert (
            "Node hash assignment is needed for PAYG or Credit payments" in error_msg
        )  # Ignore "Value error, ..."


def test_validation_on_credits_payment_options():
    """Ensure that a node_hash option is required for credit payments."""
    path = Path(__file__).parent / "messages/instance_gpu_machine.json"
    message_dict = json.loads(path.read_text())
    # Patch the gpu field with some info
    message_dict["content"]["payment"]["type"] = "credit"
    message_dict["content"]["payment"]["receiver"] = None
    message = create_new_message(message_dict, factory=InstanceMessage)

    assert isinstance(message, InstanceMessage)
    assert hash(message.content)
    assert message.content.payment
    assert message.content.payment.type == PaymentType.credit
    assert message.content.environment.hypervisor == HypervisorType.qemu

    # Remove gpu field with some info
    message_dict["content"]["requirements"]["gpu"] = None
    message = create_new_message(message_dict, factory=InstanceMessage)

    assert isinstance(message, InstanceMessage)
    assert hash(message.content)
    assert message.content.payment
    assert message.content.payment.type == PaymentType.credit
    assert message.content.environment.hypervisor == HypervisorType.qemu
    assert message.content.requirements.gpu is None

    message_dict["content"]["requirements"]["node"] = None
    try:
        _ = create_new_message(message_dict, factory=InstanceMessage)
        raise AssertionError("An exception should have been raised before this point.")
    except ValidationError as e:
        assert e.errors()[0]["loc"] in [("content",), ("content", "__root__")]

        error_msg = e.errors()[0]["msg"]
        assert (
            "Node hash assignment is needed for PAYG or Credit payments" in error_msg
        )  # Ignore "Value error, ..."


def test_message_machine_port_mapping():
    message_dict = {
        "chain": "ETH",
        "sender": "0x101d8D16372dBf5f1614adaE95Ee5CCE61998Fc9",
        "type": "PROGRAM",
        "time": "1625652287.017",
        "item_type": "inline",
        "content": {
            "address": "0x101d8D16372dBf5f1614adaE95Ee5CCE61998Fc9",
            "time": 1625652287.017,
            "type": "vm-function",
            "allow_amend": False,
            "code": {
                "encoding": "zip",
                "entrypoint": "example_fastapi_2:app",
                "ref": "7eb2eca2378ea8855336ed76c8b26219f1cb90234d04441de9cf8cb1c649d003",
                "use_latest": False,
            },
            "on": {
                "http": False,
            },
            "environment": {
                "reproducible": False,
                "internet": False,
                "aleph_api": False,
                "shared_cache": False,
            },
            "runtime": {
                "ref": "7eb2eca2378ea8855336ed76c8b26219f1cb90234d04441de9cf8cb1c649d003",
                "comment": "Dummy hash",
                "use_latest": True,
            },
            "resources": {
                "vcpus": 1,
                "memory": 128,
                "seconds": 1,
                "published_ports": [
                    {"protocol": "tcp", "port": 80},
                    {"protocol": "udp", "port": 53},
                ],
            },
            "volumes": [],
        },
        "signature": "0x123456789",  # Signature validation requires using aleph-client
    }

    new_message = create_new_message(message_dict, factory=ProgramMessage)
    assert new_message
    new_message = create_new_message(message_dict)
    assert new_message


def test_message_machine_named():
    path = Path(
        os.path.abspath(os.path.join(__file__, "../messages/machine_named.json"))
    )

    message = create_message_from_file(path, factory=ProgramMessage)
    assert isinstance(message, ProgramMessage)
    if message.content is not None:
        assert isinstance(message.content.metadata, dict)
        assert message.content.metadata["version"] == "10.2"


def test_message_forget():
    path = Path(os.path.abspath(os.path.join(__file__, "../messages/forget.json")))
    message = create_message_from_file(path, factory=ForgetMessage)
    assert hash(message.content)


def test_message_forget_cannot_be_forgotten():
    """A FORGET message may not be forgotten"""
    path = os.path.abspath(os.path.join(__file__, "../messages/forget.json"))
    with open(path) as fd:
        message_raw = json.load(fd)
    message_raw = add_item_content_and_hash(message_raw)

    message_raw["forgotten_by"] = ["abcde"]
    with pytest.raises(ValueError) as e:
        ForgetMessage.model_validate(message_raw)
    assert "This type of message may not be forgotten" in str(e.value)


def test_message_forgotten_by():
    path = os.path.abspath(os.path.join(__file__, "../messages/machine.json"))
    with open(path) as fd:
        message_raw = json.load(fd)
    message_raw = add_item_content_and_hash(message_raw)

    # Test different values for field 'forgotten_by'
    _ = ProgramMessage.model_validate(message_raw)
    _ = ProgramMessage.model_validate({**message_raw, "forgotten_by": None})
    _ = ProgramMessage.model_validate({**message_raw, "forgotten_by": ["abcde"]})
    _ = ProgramMessage.model_validate(
        {**message_raw, "forgotten_by": ["abcde", "fghij"]}
    )


def test_item_type_from_hash():
    assert (
        ItemType.from_hash("QmX8K1c22WmQBAww5ShWQqwMiFif7XFrJD6iFBj7skQZXW")
        == ItemType.ipfs
    )
    assert (
        ItemType.from_hash(
            "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
        )
        == ItemType.ipfs
    )
    assert (
        ItemType.from_hash(
            "01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b"
        )
        == ItemType.storage
    )

    with pytest.raises(UnknownHashError):
        ItemType.from_hash("INVALID")


def test_create_new_message():
    message_dict = {
        "chain": "ETH",
        "sender": "0x101d8D16372dBf5f1614adaE95Ee5CCE61998Fc9",
        "type": "POST",
        "time": "1625652287.017",
        "item_type": "inline",
        "content": {
            "address": "0x101d8D16372dBf5f1614adaE95Ee5CCE61998Fc9",
            "type": "test-message",
            "time": "1625652287.017",
            "content": {
                "hello": "world",
            },
        },
        "signature": "0x123456789",  # Signature validation requires using aleph-client
    }

    new_message_1 = create_new_message(message_dict, factory=PostMessage)
    assert new_message_1
    assert new_message_1.type == MessageType.post
    # Check that the time was converted to a datetime
    assert new_message_1.time.isoformat() == "2021-07-07T10:04:47.017000+00:00"

    # The time field can be either a float or a datetime as string
    message_dict["time"] = "2021-07-07T10:04:47.017000+00:00"
    new_message_2 = create_message_from_json(
        json.dumps(message_dict), factory=PostMessage
    )
    assert new_message_1 == new_message_2
    assert create_message_from_json(json.dumps(message_dict))


def test_program_message_content_and_item_content_differ() -> None:
    # Test that a ValidationError is raised if the content and item_content differ

    # Get a program message as JSON-compatible dict
    path = Path(__file__).parent / "messages/machine.json"
    with open(path) as fd:
        message_dict_original = json.load(fd)
    message_dict: dict = add_item_content_and_hash(message_dict_original, inplace=True)

    # patch hashlib.sha256 with a mock else this raises an error first
    mock_hash = mock.MagicMock()
    mock_hash.hexdigest.return_value = (
        "cafecafecafecafecafecafecafecafecafecafecafecafecafecafecafecafe"
    )
    message_dict["item_hash"] = (
        "cafecafecafecafecafecafecafecafecafecafecafecafecafecafecafecafe"
    )

    # Patch the content to differ from item_content
    message_dict["content"]["replaces"] = "does-not-exist"

    # Test that a ValidationError is raised if the content and item_content differ
    with mock.patch("aleph_message.models.sha256", return_value=mock_hash):
        with pytest.raises(ValidationError) as excinfo:
            ProgramMessage.model_validate(message_dict)
        assert "Content and item_content differ" in str(excinfo.value)


@pytest.mark.slow
@pytest.mark.skipif(not isdir(MESSAGES_STORAGE_PATH), reason="No file on disk to test")
def test_messages_from_disk():
    for messages_page in listdir(MESSAGES_STORAGE_PATH):
        with open(join(MESSAGES_STORAGE_PATH, messages_page)) as page_fd:
            data_dict = json.load(page_fd)
        for message_dict in data_dict["messages"]:
            try:
                message = parse_message(message_dict)
                assert message
            except ValidationError as e:
                console.print("-" * 79)
                console.print(message_dict)
                console.print_json(e.json())
                raise


def test_terms_and_conditions_only_for_payg_instances():
    """Ensure that only instance with PAYG and a node_hash can have a terms_and_conditions"""
    path = os.path.abspath(os.path.join(__file__, "../messages/instance_content.json"))
    with open(path) as fd:
        message_dict = json.load(fd)

    # this one is valid
    instance_message = create_message_from_json(
        json.dumps(message_dict), factory=InstanceMessage
    )

    assert isinstance(instance_message.content, InstanceContent)
    assert (
        instance_message.content.payment and instance_message.content.payment.is_stream
    )

    message_dict["content"]["payment"]["type"] = "hold"

    # can't have a terms_and_conditions with hold
    with pytest.raises(ValueError):
        instance_message = create_message_from_json(
            json.dumps(message_dict), factory=InstanceMessage
        )

    message_dict["content"]["payment"]["type"] = "superfluid"

    # a node_hash is needed for a terms_and_conditions
    del message_dict["content"]["requirements"]["node"]["node_hash"]
    with pytest.raises(ValueError):
        instance_message = create_message_from_json(
            json.dumps(message_dict), factory=InstanceMessage
        )
