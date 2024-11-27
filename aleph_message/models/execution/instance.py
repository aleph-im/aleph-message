from __future__ import annotations

from typing import Self

from aleph_message.models import PaymentType
from pydantic import Field, validator, root_validator

from aleph_message.models.abstract import HashableModel

from .abstract import BaseExecutableContent
from .environment import InstanceEnvironment
from .volume import ParentVolume, PersistentVolumeSizeMib, VolumePersistence


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

    environment: InstanceEnvironment = Field(
        description="Properties of the instance execution environment"
    )
    rootfs: RootfsVolume = Field(
        description="Root filesystem of the system, will be booted by the kernel"
    )

    @root_validator(pre=True)
    def check_gpu_requirement(self) -> Self:
        if self.requirements and self.requirements.gpus:
            if self.payment and not self.payment.is_stream:
                raise ValueError('Stream payment type is needed for GPU requirement')
        return self
