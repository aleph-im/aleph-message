from enum import Enum


class Chain(str, Enum):
    """Supported chains"""

    ARBITRUM = "ARB"
    AURORA = "AURORA"
    AVAX = "AVAX"
    BASE = "BASE"
    BLAST = "BLAST"
    BOB = "BOB"
    BSC = "BSC"
    CSDK = "CSDK"
    CYBER = "CYBER"
    DOT = "DOT"
    ECLIPSE = "ES"
    ETH = "ETH"
    ETHERLINK = "ETHERLINK"
    FRAXTAL = "FRAX"
    HYPE = "HYPE"
    INK = "INK"
    LENS = "LENS"
    LINEA = "LINEA"
    LISK = "LISK"
    METIS = "METIS"
    MODE = "MODE"
    NEO = "NEO"
    NULS = "NULS"
    NULS2 = "NULS2"
    OPTIMISM = "OP"
    POL = "POL"
    SOL = "SOL"
    SOMNIA = "STT"
    SONIC = "SONIC"
    TEZOS = "TEZOS"
    UNICHAIN = "UNICHAIN"
    WORLDCHAIN = "WLD"
    ZORA = "ZORA"


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
