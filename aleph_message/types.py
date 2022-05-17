from enum import Enum

from pydantic import BaseModel, Field, Extra


class Chain(str, Enum):
    """Supported chains"""
    AVAX = "AVAX"
    CSDK = "CSDK"
    DOT = "DOT"
    ETH = "ETH"
    NEO = "NEO"
    NULS = "NULS"
    NULS2 = "NULS2"
    SOL = "SOL"


class HashType(str, Enum):
    """Supported hash functions"""
    sha256 = "sha256"


class MessageType(str, Enum):
    """Message types supported by Aleph"""
    post = "POST"
    aggregate = "AGGREGATE"
    store = "STORE"
    program = "PROGRAM"
    forget = "FORGET"


class ItemType(str, Enum):
    """Item storage options"""
    inline = "inline"
    storage = "storage"
    ipfs = "ipfs"


class MongodbId(BaseModel):
    """PyAleph returns an internal MongoDB id"""
    oid: str = Field(alias="$oid")

    class Config:
        extra = Extra.forbid
