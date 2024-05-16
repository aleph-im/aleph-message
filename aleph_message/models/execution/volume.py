from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import ConstrainedInt, Extra

from ...utils import Gigabytes, gigabyte_to_mebibyte
from ..abstract import HashableModel
from ..item_hash import ItemHash


class AbstractVolume(HashableModel, ABC):
    comment: Optional[str] = None
    mount: Optional[str] = None

    @abstractmethod
    def is_read_only(self): ...

    class Config:
        extra = Extra.forbid


class ImmutableVolume(AbstractVolume):
    ref: ItemHash
    use_latest: bool = True

    def is_read_only(self):
        return True


class EphemeralVolumeSize(ConstrainedInt):
    gt = 0
    le = 1000  # Limit to 1 GiB
    strict = True


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


class PersistentVolumeSizeMib(ConstrainedInt):
    gt = 0
    le = gigabyte_to_mebibyte(Gigabytes(100))
    strict = True  # Limit to 100 GiB


class PersistentVolume(AbstractVolume):
    parent: Optional[ParentVolume]
    persistence: VolumePersistence
    name: str
    size_mib: PersistentVolumeSizeMib

    def is_read_only(self):
        return False


class RootfsVolume(HashableModel):
    """
    Root file system of a VM instance.

    The root file system of an instance is built as a copy of a reference image, named parent
    image. The user determines a custom size and persistence model.
    """

    parent: ParentVolume
    persistence: VolumePersistence
    # Use the same size constraint as persistent volumes for now
    size_mib: PersistentVolumeSizeMib


MachineVolume = Union[ImmutableVolume, EphemeralVolume, PersistentVolume]
