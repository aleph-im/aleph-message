from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Annotated, Literal, Optional, Union

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


EphemeralVolumeSize = Annotated[
    int,
    Field(
        gt=0,
        le=1000,  # Limit to 1 GiB
        strict=True,
    ),
]


class EphemeralVolume(AbstractVolume):
    ephemeral: Literal[True] = True
    size_mib: EphemeralVolumeSize

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


# Define a type for persistent volume size with constraints
PersistentVolumeSizeMib = Annotated[
    int,
    Field(
        gt=0,
        le=gigabyte_to_mebibyte(Gigabytes(2048)),
        strict=True,  # Limit to 2048 GiB
    ),
]


class PersistentVolume(AbstractVolume):
    parent: Optional[ParentVolume] = None
    persistence: Optional[VolumePersistence] = None
    name: Optional[str] = None
    size_mib: PersistentVolumeSizeMib

    def is_read_only(self):
        return False


MachineVolume = Union[ImmutableVolume, EphemeralVolume, PersistentVolume]
