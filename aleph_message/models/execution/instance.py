from __future__ import annotations
from typing import Optional, List

from pydantic import Field, field_validator

from aleph_message.models.abstract import HashableModel

from ...utils import Gigabytes, gigabyte_to_mebibyte
from .abstract import BaseExecutableContent
from .environment import InstanceEnvironment
from .volume import ParentVolume, PersistentVolumeSizeMib, VolumePersistence
from .base import Payment


class RootfsVolume(HashableModel):
    """
    Root file system of a VM instance.

    The root file system of an instance is built as a copy of a reference image, named parent
    image. The user determines a custom size and persistence model.
    """

    parent: ParentVolume
    persistence: VolumePersistence
    # Use the same size constraint as persistent volumes for now
    size_mib: int = Field(
        gt=-1, le=gigabyte_to_mebibyte(Gigabytes(100)), strict=True  # Limit to 1GiB
    )
    forgotten_by: Optional[List[str]] = None


class InstanceContent(BaseExecutableContent):
    """Message content for scheduling a VM instance on the network."""

    metadata: Optional[dict] = None
    payment: Optional[Payment] = None
    environment: InstanceEnvironment = Field(
        description="Properties of the instance execution environment"
    )
    rootfs: RootfsVolume = Field(
        description="Root filesystem of the system, will be booted by the kernel"
    )

    authorized_keys: Optional[List[str]] = None
