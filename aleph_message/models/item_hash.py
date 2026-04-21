from enum import Enum
from functools import lru_cache
from typing import Any

from pydantic_core import core_schema

from ..exceptions import UnknownHashError

# SHA-256 hex digest used as the `storage` item hash.
_HEX_LOWER = frozenset("0123456789abcdef")
# Base58btc excludes 0, O, I and l to avoid visually-ambiguous characters.
_BASE58BTC = frozenset("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
# Base32 (RFC 4648, lowercase, no padding), the encoding used by the
# `bafy` CIDv1 prefix.
_BASE32_LOWER = frozenset("abcdefghijklmnopqrstuvwxyz234567")


class ItemType(str, Enum):
    """Item storage options"""

    inline = "inline"
    storage = "storage"
    ipfs = "ipfs"

    @classmethod
    @lru_cache
    def from_hash(cls, item_hash: str) -> "ItemType":
        # https://docs.ipfs.io/concepts/content-addressing/#identifier-formats
        if (
            item_hash.startswith("Qm")
            and 44 <= len(item_hash) <= 46
            and _BASE58BTC.issuperset(item_hash[2:])
        ):
            return cls.ipfs
        if (
            item_hash.startswith("bafy")
            and len(item_hash) == 59
            and _BASE32_LOWER.issuperset(item_hash[4:])
        ):
            return cls.ipfs
        if len(item_hash) == 64 and _HEX_LOWER.issuperset(item_hash):
            return cls.storage
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
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: core_schema.ValidatorFunctionWrapHandler
    ) -> core_schema.CoreSchema:
        """Pydantic v2 - Validation Schema"""
        return core_schema.no_info_after_validator_function(
            cls.validate, core_schema.str_schema()
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, schema) -> dict[str, Any]:
        """Pydantic v2 - JSON Schema Generation"""
        return {"type": "string"}

    @classmethod
    def validate(cls, v: Any) -> "ItemHash":
        if not isinstance(v, str):
            raise TypeError("Item hash must be a string")
        return cls(v)  # Convert to ItemHash

    def __repr__(self) -> str:
        return f"<ItemHash value={super().__repr__()} item_type={self.item_type!r}>"
