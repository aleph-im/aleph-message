from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from aleph_message.models.abstract import HashableModel
from aleph_message.models.item_hash import ItemHash
from .abstract import BaseExecutableContent
from .volume import VolumePersistence, PersistentVolumeSizeMib


class RootfsVolume(HashableModel):
    """
    Root file system of a VM instance.

    The root file system of an instance is built as a copy of a reference image, named parent
    image. The user determines a custom size and persistence model.
    """
    parent: ItemHash
    persistence: VolumePersistence
    # Use the same size constraint as persistent volumes for now
    size_mib: PersistentVolumeSizeMib
    # Whether the volume must be based on the latest version of the parent volume or
    # on the original. We use the original by default for consistency with programs.
    use_latest: bool = False


class InstanceContent(BaseExecutableContent):
    """Message content for scheduling a VM instance on the network."""

    rootfs: RootfsVolume = Field(
        description="Root filesystem of the system, will be booted by the kernel"
    )
    cloud_config: Dict[str, Any] = Field(
        description="Cloud-init configuration, see https://cloudinit.readthedocs.io/en/latest/"
    )
