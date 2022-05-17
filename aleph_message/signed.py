import json
from hashlib import sha256
from json import JSONDecodeError
from typing import Optional, List, Dict, Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import Field, BaseModel, Extra, validator
from .types import HashType
from .message import (
    BaseMessage,
    MessageConfirmation,
    PostMessage,
    AggregateMessage,
    StoreMessage,
    ForgetMessage,
    ProgramMessage,
    MessageType,
    ItemType,
)


class SignedBaseMessage(BaseMessage):
    signature: str = Field(
        description="Cryptographic signature of the message by the sender"
    )
    item_content: Optional[str] = Field(
        default=None,
        description="JSON serialization of the message when 'item_type' is 'inline'",
    )
    hash_type: Optional[HashType] = Field(
        default=None, description="Hashing algorithm used to compute 'item_hash'"
    )
    item_hash: str = Field(description="Hash of the content (sha256 by default)")
    confirmations: Optional[List[MessageConfirmation]] = Field(
        default=None, description="Blockchain confirmations of the message"
    )
    confirmed: Optional[bool] = Field(
        default=None,
        description="Indicates that the message has been confirmed on a blockchain",
    )

    @validator("item_content")
    def check_item_content(cls, v: Optional[str], values):
        item_type = values["item_type"]
        if item_type == ItemType.inline:
            try:
                json.loads(v)
            except JSONDecodeError:
                raise ValueError(
                    "Field 'item_content' does not appear to be valid JSON"
                )
        else:
            if v is not None:
                raise ValueError(
                    f"Field 'item_content' cannot be defined when 'item_type' == '{item_type}'"
                )
        return v

    @validator("item_hash")
    def check_item_hash(cls, v, values):
        item_type = values["item_type"]
        if item_type == ItemType.inline:
            item_content: str = values["item_content"]

            # Double check that the hash function is supported
            hash_type = values["hash_type"] or HashType.sha256
            assert hash_type.value == HashType.sha256

            computed_hash: str = sha256(item_content.encode()).hexdigest()
            if v != computed_hash:
                raise ValueError(
                    f"'item_hash' do not match 'sha256(item_content)'"
                    f", expecting {computed_hash}"
                )
        elif item_type == ItemType.ipfs:
            # TODO: CHeck that the hash looks like an IPFS multihash
            pass
        else:
            assert item_type == ItemType.storage
        return v

    @validator("confirmed")
    def check_confirmed(cls, v, values):
        confirmations = values["confirmations"]
        if v != bool(confirmations):
            raise ValueError("Message cannot be 'confirmed' without 'confirmations'")
        return v


class SignedPostMessage(PostMessage, SignedBaseMessage):
    pass


class SignedAggregateMessage(AggregateMessage, SignedBaseMessage):
    pass


class SignedStoreMessage(StoreMessage, SignedBaseMessage):
    pass


class SignedForgetMessage(ForgetMessage, SignedBaseMessage):
    pass


class SignedProgramMessage(ProgramMessage, SignedBaseMessage):
    pass

    # @validator("content")
    # def check_content(cls, v, values):
    #     item_type = values["item_type"]
    #     if item_type == ItemType.inline:
    #         item_content = json.loads(values["item_content"])
    #         if v.dict(exclude_none=True) != item_content:
    #             # Print differences
    #             vdict = v.dict()
    #             for key, value in item_content.items():
    #                 if vdict[key] != value:
    #                     print(f"{key}: {vdict[key]} != {value}")
    #             raise ValueError("Content and item_content differ")
    #     return v


def SignedMessage(
    **message_dict: Dict,
) -> Union[
    SignedPostMessage, SignedAggregateMessage, SignedStoreMessage, SignedProgramMessage
]:
    """Returns the message class corresponding to the type of message."""
    for raw_type, message_class in {
        MessageType.post: SignedPostMessage,
        MessageType.aggregate: SignedAggregateMessage,
        MessageType.store: SignedStoreMessage,
        MessageType.program: SignedProgramMessage,
        MessageType.forget: SignedForgetMessage,
    }.items():
        if message_dict["type"] == raw_type:
            print(raw_type, json.dumps(message_dict, indent=4))
            return message_class(**message_dict)
    else:
        raise ValueError(f"Unknown message type")


class SignedMessagesResponse(BaseModel):
    """Response from an Aleph node API."""

    messages: List[Union[SignedPostMessage, SignedAggregateMessage, SignedStoreMessage, SignedProgramMessage]]
    pagination_page: int
    pagination_total: int
    pagination_per_page: int
    pagination_item: str

    class Config:
        extra = Extra.forbid
