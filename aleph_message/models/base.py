from enum import Enum


class Chain(str, Enum):
    """Supported chains"""

    AVAX = "AVAX"
    BSC = "BSC"
    CSDK = "CSDK"
    DOT = "DOT"
    ETH = "ETH"
    NEO = "NEO"
    NULS = "NULS"
    NULS2 = "NULS2"
    SOL = "SOL"
    TEZOS = "TEZOS"


class HashType(str, Enum):
    """Supported hash functions"""

    sha256 = "sha256"


class MessageType(str, Enum):
    """Message types supported by Aleph"""

    post = "POST"
    aggregate = "AGGREGATE"
    store = "STORE"
    program = "PROGRAM"
    instance = "INSTANCE"
    forget = "FORGET"
