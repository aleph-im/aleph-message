from enum import Enum
from functools import lru_cache

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from ..exceptions import UnknownHashError


class ItemType(str, Enum):
    """Item storage options"""

    inline = "inline"
    storage = "storage"
    ipfs = "ipfs"

    @classmethod
    @lru_cache
    def from_hash(cls, item_hash: str) -> "ItemType":
        # https://docs.ipfs.io/concepts/content-addressing/#identifier-formats
        if item_hash.startswith("Qm") and 44 <= len(item_hash) <= 46:  # CIDv0
            return cls.ipfs
        elif item_hash.startswith("bafy") and len(item_hash) == 59:  # CIDv1
            return cls.ipfs
        elif len(item_hash) == 64:
            return cls.storage
        else:
            raise UnknownHashError(f"Could not determine hash type: '{item_hash}'")

    @classmethod
    def is_storage(cls, item_hash: str):
        return cls.from_hash(item_hash) == cls.storage

    @classmethod
    def is_ipfs(cls, item_hash: str):
        return cls.from_hash(item_hash) == cls.ipfs


class ItemHash(str):
    item_type: ItemType

    # When overriding str, override __new__ instead of __init__.
    def __new__(cls, value: str):
        item_type = ItemType.from_hash(value)

        obj = str.__new__(cls, value)
        obj.item_type = item_type
        return obj

    @classmethod
    def __get_validators__(cls):
        # one or more validators may be yielded which will be called in the
        # order to validate the input, each validator will receive as an input
        # the value returned from the previous validator
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError("Item hash must be a string")

        return cls(v)

    def __repr__(self):
        return f"<ItemHash value={super().__repr__()} item_type={self.item_type!r}>"
