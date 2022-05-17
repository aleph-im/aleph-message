import json
from copy import copy
from typing import List, Dict, Any, Optional, Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import BaseModel, Extra, Field, validator

from aleph_message.types import Chain, MessageType, ItemType, MongodbId
from .abstract import BaseContent
from .program import ProgramContent


class ChainRef(BaseModel):
    """Some POST messages have a 'ref' field referencing other content"""

    chain: Chain
    channel: Optional[str] = None
    item_content: str
    item_hash: str
    item_type: ItemType
    sender: str
    signature: str
    time: float
    type = "POST"


class MessageConfirmationHash(BaseModel):
    binary: str = Field(alias="$binary")
    type: str = Field(alias="$type")

    class Config:
        extra = Extra.forbid


class MessageConfirmation(BaseModel):
    """Format of the result when a message has been confirmed on a blockchain"""

    chain: Chain
    height: int
    hash: Union[str, MessageConfirmationHash]

    class Config:
        extra = Extra.forbid


class AggregateContentKey(BaseModel):
    name: str

    class Config:
        extra = Extra.forbid


class PostContent(BaseContent):
    """Content of a POST message"""

    content: Optional[Any] = Field(
        default=None, description="User-generated content of a POST message"
    )
    ref: Optional[Union[str, ChainRef]] = Field(
        default=None,
        description="Other message referenced by this one",
    )
    type: str = Field(description="User-generated 'content-type' of a POST message")

    @validator("type")
    def check_type(cls, v, values):
        if v == "amend":
            ref = values.get("ref")
            if not ref:
                raise ValueError("A 'ref' is required for POST type 'amend'")
        return v

    class Config:
        extra = Extra.forbid


class AggregateContent(BaseContent):
    """Content of an AGGREGATE message"""

    key: Union[str, AggregateContentKey] = Field(
        description="The aggregate key can be either a string of a dict containing the key in field 'name'"
    )
    content: Union[Dict, List, str, int, float, bool, None] = Field(
        description="The content of an aggregate must be a dict"
    )

    class Config:
        extra = Extra.forbid


class StoreContent(BaseContent):
    """Content of a STORE message"""

    item_type: ItemType
    item_hash: str
    size: Optional[int] = None  # Generated by the node on storage
    content_type: Optional[str] = None  # Generated by the node on storage
    ref: Optional[str] = None

    class Config:
        extra = Extra.allow


class ForgetContent(BaseContent):
    """Content of a FORGET message"""

    hashes: List[str]
    reason: Optional[str] = None

    def __hash__(self):
        # Convert List to Tuple for hashing
        values = copy(self.__dict__)
        values["hashes"] = tuple(values["hashes"])
        return hash(self.__class__) + hash(values.values())


class BaseMessage(BaseModel):
    """Base template for all messages"""

    id_: Optional[MongodbId] = Field(
        alias="_id", default=None, description="MongoDB metadata"
    )
    chain: Chain = Field(description="Blockchain used for this message")

    sender: str = Field(description="Address of the sender")
    type: MessageType = Field(description="Type of message (POST, AGGREGATE or STORE)")
    channel: Optional[str] = Field(
        default=None,
        description="Channel of the message, one application ideally has one channel",
    )
    size: Optional[int] = Field(
        default=None, description="Size of the content"
    )  # Almost always present
    time: float = Field(description="Unix timestamp when the message was published")
    item_type: ItemType = Field(description="Storage method used for the content")

    content: BaseContent = Field(description="Content of the message, ready to be used")

    class Config:
        extra = Extra.forbid


class PostMessage(BaseMessage):
    """Unique data posts (unique data points, events, ...)"""

    type: Literal[MessageType.post]
    content: PostContent


class AggregateMessage(BaseMessage):
    """A key-value storage specific to an address"""

    type: Literal[MessageType.aggregate]
    content: AggregateContent


class StoreMessage(BaseMessage):
    type: Literal[MessageType.store]
    content: StoreContent


class ForgetMessage(BaseMessage):
    type: Literal[MessageType.forget]
    content: ForgetContent


class ProgramMessage(BaseMessage):
    type: Literal[MessageType.program]
    content: ProgramContent


def Message(
    **message_dict: Dict,
) -> Union[PostMessage, AggregateMessage, StoreMessage, ProgramMessage]:
    """Returns the message class corresponding to the type of message."""
    for raw_type, message_class in {
        MessageType.post: PostMessage,
        MessageType.aggregate: AggregateMessage,
        MessageType.store: StoreMessage,
        MessageType.program: ProgramMessage,
        MessageType.forget: ForgetMessage,
    }.items():
        if message_dict["type"] == raw_type:
            return message_class(**message_dict)
    else:
        raise ValueError(f"Unknown message type")
