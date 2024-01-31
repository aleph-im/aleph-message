from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Literal, Optional, Union, get_args

from pydantic import ConstrainedInt, Extra

from ...utils import Gigabytes, gigabyte_to_mebibyte
from ..abstract import HashableModel
from ..item_hash import ItemHash


class AbstractVolume(HashableModel, ABC):
    comment: Optional[str] = None
    mount: Optional[str] = None

    @abstractmethod
    def is_read_only(self):
        ...

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


MachineVolume = Union[ImmutableVolume, EphemeralVolume, PersistentVolume]


def parse_volume(volume_dict: Union[Dict, MachineVolume]) -> MachineVolume:
    if isinstance(volume_dict, MachineVolume):
        return volume_dict
    for volume_type in get_args(MachineVolume):
        try:
            return volume_type.parse_obj(volume_dict)
        except ValueError:
            continue
    else:
        raise ValueError(f"Could not parse volume: {volume_dict}")
