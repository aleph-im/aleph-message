from enum import Enum
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Extra, Field


class ChainEmum(str, Enum):
    "Supported chains"
    ETH = "ETH"
    CSDK = "CSDK"
    NULS2 = "NULS2"
    SOL = "SOL"


class TypeEnum(str, Enum):
    aggregate = "AGGREGATE"
    post = "POST"
    store = "STORE"


class ItemTypeEnum(str, Enum):
    inline = "inline"
    storage = "storage"
    ipfs = "ipfs"


class MongodbId(BaseModel):
    oid: str = Field(alias="$oid")


class MessageConfirmation(BaseModel):
    chain: ChainEmum
    height: int
    hash: str


class MessageContent(BaseModel):
    key: str
    address: str
    content: Any
    time: float

    class Config:
        extra = Extra.forbid


class Message(BaseModel):
    id_: Optional[MongodbId] = Field(alias="_id")
    chain: ChainEmum
    item_hash: str
    sender: str
    type: TypeEnum
    channel: Optional[str]
    confirmed: Optional[bool]
    confirmations: Optional[List[MessageConfirmation]]
    content: Dict
    item_content: Optional[str]
    item_type: ItemTypeEnum
    signature: str
    size: int
    time: float

    class Config:
        extra = Extra.forbid


class MessagesResponse(BaseModel):
    messages: List[Message]
    pagination_page: int
    pagination_total: int
    pagination_per_page: int
    pagination_item: str

    class Config:
        extra = Extra.forbid
