from __future__ import annotations

from pydantic import Field, validator, root_validator

from aleph_message.models.abstract import HashableModel

from .abstract import BaseExecutableContent
from .environment import HypervisorType, InstanceEnvironment
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

    @validator("requirements")
    def terms_and_conditions_only_for_payg_instances(cls, v, values, field, config):
        if not v.node or not v.node.terms_and_conditions:
            return v

        if not values["payment"].is_stream:
            raise ValueError(
                f"only PAYG/stream instance can have a terms_and_conditions, not '{values['payment'].type}' instances"
            )

        if not v.node.node_hash:
            raise ValueError(
                "an instance with a terms_and_conditions needs a requirements.node.node_hash value"
            )

        return v

    @root_validator()
    def check_gpu_requirement(cls, values):
        if values.get("requirements") and values.get("requirements").gpu:
            if (
                not values.get("requirements").node
                or not values.get("requirements").node.node_hash
            ):
                raise ValueError("Node hash assignment is needed for GPU support")

            if (
                values.get("environment")
                and values.get("environment").hypervisor != HypervisorType.qemu
            ):
                raise ValueError("GPU option is only supported for QEmu hypervisor")
        return values
