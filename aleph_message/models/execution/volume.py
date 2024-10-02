from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import Field, ConfigDict, BaseModel, field_validator

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


class EphemeralVolumeSize(BaseModel):
    ephemeral_volume_size: int = Field(gt=-1, le=1000, strict=True)  # Limit to 1GiB

    def __hash__(self):
        return hash(self.ephemeral_volume_size)


class EphemeralVolume(AbstractVolume):
    ephemeral: Literal[True] = True
    size_mib: EphemeralVolumeSize = EphemeralVolumeSize(ephemeral_volume_size=0)

    @field_validator("size_mib", mode="before")
    def convert_size_mib(cls, v):
        if isinstance(v, int):
            return EphemeralVolumeSize(ephemeral_volume_size=v)
        return v

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


class PersistentVolumeSizeMib(BaseModel):
    persistent_volume_size: int = Field(
        gt=-1, le=gigabyte_to_mebibyte(Gigabytes(100)), strict=True  # Limit to 1GiB
    )

    def __hash__(self):
        return hash(self.persistent_volume_size)


class PersistentVolume(AbstractVolume):
    parent: Optional[ParentVolume] = None
    persistence: Optional[VolumePersistence] = None
    name: Optional[str] = None
    size_mib: Optional[PersistentVolumeSizeMib] = PersistentVolumeSizeMib(
        persistent_volume_size=0
    )

    @field_validator("size_mib", mode="before")
    def convert_size_mib(cls, v):
        if isinstance(v, int):
            return PersistentVolumeSizeMib(persistent_volume_size=v)
        return v

    def is_read_only(self):
        return False


MachineVolume = Union[ImmutableVolume, EphemeralVolume, PersistentVolume]
