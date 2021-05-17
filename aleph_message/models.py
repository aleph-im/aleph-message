import json
from enum import Enum
from hashlib import sha256
from json import JSONDecodeError
from typing import List, Dict, Any, Optional, Union, Literal

from pydantic import BaseModel, Extra, Field, AnyUrl, validator


class Chain(str, Enum):
    "Supported chains"
    AVAX = "AVAX"
    CSDK = "CSDK"
    DOT = "DOT"
    ETH = "ETH"
    NEO = "NEO"
    NULS = "NULS"
    NULS2 = "NULS2"
    SOL = "SOL"


class HashType(str, Enum):
    "Supported hash functions"
    sha256 = "sha256"


class MessageType(str, Enum):
    "Message types supported by Aleph"
    post = "POST"
    aggregate = "AGGREGATE"
    store = "STORE"


class ItemType(str, Enum):
    "Item storage options"
    inline = "inline"
    storage = "storage"
    ipfs = "ipfs"


class PostContentType(str, Enum):
    "User-generated 'content-type' for POST messages"
    xchain_swap = "xchain-swap"
    staking_rewards_distribution = "staking-rewards-distribution"
    amend = "amend"
    note = "note"
    corechan_operation = "corechan-operation"
    file = "file"
    nfts = "nfts"
    chat = "chat"
    folder = "folder"
    quartz_archetype = "quartz_archetype"
    messages = "messages"
    channel_memberships = "channel_memberships"
    comment = "comment"
    blog_pers = "blog_pers"
    channels = "channels"
    nft_snapshot = "nft-snapshot"
    pancake_simple = "pancake-simple"
    pancake = "pancake"
    incentive_distribution = "incentive-distribution"
    vm_function = "vm-function"
    code = "code"
    timeline_post = "timeline-post"
    account = "account"
    media = "media"
    mytype = "mytype"
    scoring = "scoring"
    my_chat = "my_chat"
    dre_market_propfile = "dre.market/profile"
    evidenceUrl = "evidenceUrl"
    authorization = "authorization"
    did_verified = "did_verified"
    did_archive = "did_archive"
    testtype = "testtype"
    testmsg = "testmsg"
    doc = "doc"
    document = "document"
    test = "test"


class MongodbId(BaseModel):
    "PyAleph returns an internal MongoDB id"
    oid: str = Field(alias="$oid")

    class Config:
        extra = Extra.forbid


class StorageEngineInfo(BaseModel):
    "Some STORE messages have extra info about a 'storage engine'"
    Blocks: int
    CumulativeSize: int
    Hash: str  # IPFS Hash
    Size: int
    Type: str

    class Config:
        extra = Extra.forbid


class StoreNft(BaseModel):
    "Some STORE messages have extra info about NFT storage"
    contract_address: str
    metadata_url: Union[AnyUrl, str]  # A number is generally appended after the url
    source_url: Union[AnyUrl, str]
    token_id: str

    class Config:
        extra = Extra.forbid


class ChainRef(BaseModel):
    "Some POST messages have a 'ref' field referencing other content"
    chain: Chain
    channel: Optional[str]
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
    "Format of the result when a message has been confirmed on a blockchain"
    chain: Chain
    height: int
    hash: Union[str, MessageConfirmationHash]

    class Config:
        extra = Extra.forbid


class AggregateContentKey(BaseModel):
    name: str

    class Config:
        extra = Extra.forbid


class BaseContent(BaseModel):
    "Base template for message content"
    address: str
    time: float

    class Config:
        extra = Extra.forbid


class PostContent(BaseContent):
    "Content of a POST message"
    content: Optional[Any]
    ref: Optional[Union[str, ChainRef]]
    type: PostContentType

    class Config:
        extra = Extra.forbid


class AggregateContent(BaseContent):
    "Content of an AGGREGATE message"
    key: Union[str, AggregateContentKey] = Field(
        description="The aggregate key can be either a string of a dict containing the key in field 'name'")
    content: Optional[Any]

    class Config:
        extra = Extra.forbid


class StoreContent(BaseContent):
    "Content of a STORE message"
    item_type: ItemType
    item_hash: str
    ref: Optional[str]
    source_chain: Optional[Chain]
    source_contract: Optional[str]
    tx_hash: Optional[str]
    height: Optional[int]
    submitter: Optional[str]
    size: Optional[int]  # Almost always present
    content_type: Optional[str]  # Almost always present
    name: Optional[str]
    engine_info: Optional[StorageEngineInfo]
    nft: Optional[StoreNft]
    stored_field: Optional[str]
    sha256: Optional[str]
    senderId: Optional[int]
    content_type_: Optional[str] = Field(alias="content-type")

    class Config:
        extra = Extra.forbid


class BaseMessage(BaseModel):
    "Base template for all messages"
    id_: Optional[MongodbId] = Field(alias="_id", description="MongoDB metadata")
    chain: Chain = Field(description="Blockchain used for this message")

    sender: str = Field(description="Address of the sender")
    type: MessageType = Field(description="Type of message (POST, AGGREGATE or STORE)")
    channel: Optional[str] = Field(description="Channel of the message, one application ideally has one channel")
    confirmations: Optional[List[MessageConfirmation]] = Field(description="Blockchain confirmations of the message")
    confirmed: Optional[bool] = Field(description="Indicates that the message has been confirmed on a blockchain")
    content: BaseContent = Field(description="Content of the message, ready to be used")
    signature: str = Field(description="Cryptographic signature of the message by the sender")
    size: Optional[int] = Field(description="Size of the content") # Almost always present
    time: float = Field(description="Unix timestamp when the message was published")
    item_type: ItemType = Field(description="Storage method used for the content")
    item_content: Optional[str] = Field(
        description="JSON serialization of the message when 'item_type' is 'inline'")
    hash_type: Optional[HashType] = Field(description="Hashing algorithm used to compute 'item_hash'")
    item_hash: str = Field(description="Hash of the content (sha256 by default)")

    @validator('item_content')
    def check_item_content(cls, v: Optional[str], values):
        item_type = values['item_type']
        if item_type == ItemType.inline:
            try:
                json.loads(v)
            except JSONDecodeError:
                raise ValueError("Field 'item_content' does not appear to be valid JSON")
        else:
            if v != None:
                raise ValueError(
                    f"Field 'item_content' cannot be defined when 'item_type' == '{item_type}'")
        return v

    @validator('item_hash')
    def check_item_hash(cls, v, values):
        item_type = values['item_type']
        if item_type == ItemType.inline:
            item_content: str = values['item_content']

            # Double check that the hash function is supported
            hash_type = values['hash_type'] or HashType.sha256
            assert hash_type.value == HashType.sha256

            computed_hash: str = sha256(item_content.encode()).hexdigest()
            if v != computed_hash:
                raise ValueError(f"'item_hash' do not match 'sha256(item_content)'")
        elif item_type == ItemType.ipfs:
            # TODO: CHeck that the hash looks like an IPFS multihash
            pass
        else:
            assert item_type == ItemType.storage

    @validator('confirmed')
    def check_confirmed(cls, v, values):
        confirmations = values['confirmations']
        if v != bool(confirmations):
            raise ValueError("Message cannot be 'confirmed' without 'confirmations'")

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


def Message(**message_dict: Dict):
    "Returns the message class corresponding to the type of message."
    for raw_type, message_class in {
        MessageType.post: PostMessage,
        MessageType.aggregate: AggregateMessage,
        MessageType.store: StoreMessage,
    }.items():
        if message_dict['type'] == raw_type:
            return message_class(**message_dict)
    else:
        raise ValueError


class MessagesResponse(BaseModel):
    "Response from an Aleph node API."
    messages: List[Union[PostMessage, AggregateMessage, StoreMessage]]
    pagination_page: int
    pagination_total: int
    pagination_per_page: int
    pagination_item: str

    class Config:
        extra = Extra.forbid
