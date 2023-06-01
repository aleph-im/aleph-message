from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from aleph_message.models.abstract import HashableModel
from aleph_message.models.item_hash import ItemHash
from .abstract import BaseExecutableContent
from .volume import VolumePersistence, PersistentVolumeSizeMib, ParentVolume


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


class InstanceContent(BaseExecutableContent):
    """Message content for scheduling a VM instance on the network."""

    rootfs: RootfsVolume = Field(
        description="Root filesystem of the system, will be booted by the kernel"
    )

