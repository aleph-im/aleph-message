from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import ConfigDict, Field

from ...utils import Gigabytes, gigabyte_to_mebibyte
from ..abstract import HashableModel
from ..item_hash import ItemHash


class AbstractVolume(HashableModel, ABC):
    comment: Optional[str] = None
    mount: Optional[str] = None

    @abstractmethod
    def is_read_only(self): ...

    model_config = ConfigDict(extra="forbid")


class ImmutableVolume(AbstractVolume):
    ref: Optional[ItemHash] = None
    use_latest: bool = True

    def is_read_only(self):
        return True


class EphemeralVolume(AbstractVolume):
    ephemeral: Literal[True] = True
    size_mib: int = Field(
        gt=0, le=gigabyte_to_mebibyte(Gigabytes(1)), strict=True  # Limit to 1GiB
    )

    def is_read_only(self):
        return False


class ParentVolume(HashableModel):
    """
    A reference volume to copy as a persistent volume.
    """

    ref: ItemHash
    use_latest: bool = True


class VolumePersistence(str, Enum):
    host = "host"
    store = "store"


class PersistentVolume(AbstractVolume):
    parent: Optional[ParentVolume] = None
    persistence: Optional[VolumePersistence] = None
    name: Optional[str] = None
    size_mib: int = Field(
        gt=0, le=gigabyte_to_mebibyte(Gigabytes(100)), strict=True  # Limit to 100GiB
    )

    def is_read_only(self):
        return False


MachineVolume = Union[ImmutableVolume, EphemeralVolume, PersistentVolume]
