import json
from enum import Enum
from hashlib import sha256
from json import JSONDecodeError
from pprint import pprint
from typing import List, Dict, Any, Optional, Union, Literal

from pydantic import BaseModel, Extra, Field, AnyUrl, validator


class ChainEmum(str, Enum):
    "Supported chains"
    ETH = "ETH"
    CSDK = "CSDK"
    NULS = "NULS"
    NULS2 = "NULS2"
    SOL = "SOL"
    DOT = "DOT"
    NEO = "NEO"


class HashType(str, Enum):
    "Supported hash functions"
    sha256 = "sha256"


class RawTypeEnum(str, Enum):
    aggregate = "AGGREGATE"
    post = "POST"
    store = "STORE"


class StorageItemTypeEnum(str, Enum):
    inline = "inline"
    storage = "storage"
    ipfs = "ipfs"


class PostContentTypeEnum(str, Enum):
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
    oid: str = Field(alias="$oid")

    class Config:
        extra = Extra.forbid


class StorageEngineInfo(BaseModel):
    Blocks: int
    CumulativeSize: int
    Hash: str  # IPFS Hash
    Size: int
    Type: str

    class Config:
        extra = Extra.forbid


class StoreNft(BaseModel):
    contract_address: str
    metadata_url: str
    source_url: Union[AnyUrl, str]
    token_id: str

    class Config:
        extra = Extra.forbid


class ChainRef(BaseModel):
    chain: ChainEmum
    channel: Optional[str]
    item_content: str
    item_hash: str
    item_type: StorageItemTypeEnum
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
    chain: ChainEmum
    height: int
    hash: Union[str, MessageConfirmationHash]

    class Config:
        extra = Extra.forbid


class AggregateContentKey(BaseModel):
    name: str

    class Config:
        extra = Extra.forbid


class BaseContent(BaseModel):
    address: str
    time: float

    class Config:
        extra = Extra.forbid


class AggregateContent(BaseContent):
    key: Union[str, AggregateContentKey]
    content: Optional[Any]

    class Config:
        extra = Extra.forbid


class PostContent(BaseContent):
    content: Optional[Any]
    ref: Optional[Union[str, ChainRef]]
    type: PostContentTypeEnum

    class Config:
        extra = Extra.forbid


class StoreContent(BaseContent):
    item_type: StorageItemTypeEnum
    item_hash: str
    ref: Optional[str]
    source_chain: Optional[ChainEmum]
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
    id_: Optional[MongodbId] = Field(alias="_id")
    chain: ChainEmum

    sender: str
    type: RawTypeEnum
    channel: Optional[str]
    confirmed: Optional[bool]
    confirmations: Optional[List[MessageConfirmation]]
    content: BaseContent
    signature: str
    size: Optional[int]  # Almost always present
    time: float
    item_type: StorageItemTypeEnum
    item_content: Optional[str] = Field(
        description="JSON serialization of the message when 'item_type' is 'inline'")
    hash_type: Optional[HashType]
    item_hash: str = Field(description="Hash of the content (sha256)")

    @validator('item_content')
    def check_item_content(cls, v: Optional[str], values):
        item_type = values['item_type']
        if item_type == StorageItemTypeEnum.inline:
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
        if item_type == StorageItemTypeEnum.inline:
            item_content: str = values['item_content']

            # Double check that the hash function is supported
            hash_type = values['hash_type'] or HashType.sha256
            assert hash_type.value == HashType.sha256

            computed_hash: str = sha256(item_content.encode()).hexdigest()
            if v != computed_hash:
                raise ValueError(f"'item_hash' do not match 'sha256(item_content)'")
        elif item_type == StorageItemTypeEnum.ipfs:
            # TODO: CHeck that the hash looks like an IPFS multihash
            pass
        else:
            assert item_type == StorageItemTypeEnum.storage
            content = values['content']
            if not content:
                raise ValueError("Field 'content' is required when 'item_type' == 'storage'")


    class Config:
        extra = Extra.forbid


class PostMessage(BaseMessage):
    """Unique data posts (unique data points, events, ...)"""
    type: Literal[RawTypeEnum.post]
    content: PostContent


class AggregateMessage(BaseMessage):
    """A key-value storage specific to an address"""
    type: Literal[RawTypeEnum.aggregate]
    content: AggregateContent


class StoreMessage(BaseMessage):
    type: Literal[RawTypeEnum.store]
    content: StoreContent


def Message(**message_dict: Dict):
    for raw_type, message_class in {
        RawTypeEnum.post: PostMessage,
        RawTypeEnum.aggregate: AggregateMessage,
        RawTypeEnum.store: StoreMessage,
    }.items():
        if message_dict['type'] == raw_type:
            return message_class(**message_dict)
    else:
        raise ValueError


class MessagesResponse(BaseModel):
    messages: List[Union[PostMessage, AggregateMessage, StoreMessage]]
    pagination_page: int
    pagination_total: int
    pagination_per_page: int
    pagination_item: str

    class Config:
        extra = Extra.forbid
