from __future__ import annotations

from pydantic import Field, root_validator

from aleph_message.models.abstract import HashableModel

from .abstract import BaseExecutableContent
from .environment import InstanceEnvironment, HypervisorType
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

    @root_validator()
    def check_gpu_requirement(cls, values):
        if values.get("requirements") and values.get("requirements").gpu:
            if values.get("payment") and not values.get("payment").is_stream:
                raise ValueError("Stream payment type is needed for GPU requirement")

            if (
                values.get("environment")
                and values.get("environment").hypervisor != HypervisorType.qemu
            ):
                raise ValueError("GPU option is only supported for QEmu hypervisor")
        return values
