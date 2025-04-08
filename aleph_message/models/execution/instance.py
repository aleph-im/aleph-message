from __future__ import annotations

from typing import List, Optional

from pydantic import Field, model_validator

from aleph_message.models.abstract import HashableModel

from .abstract import BaseExecutableContent
from .base import Payment
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
    forgotten_by: Optional[List[str]] = None


class InstanceContent(BaseExecutableContent):
    """Message content for scheduling a VM instance on the network."""

    metadata: Optional[dict] = None
    payment: Optional[Payment] = None
    authorized_keys: Optional[List[str]] = Field(
        default=None, description="List of authorized SSH keys"
    )
    environment: InstanceEnvironment = Field(
        description="Properties of the instance execution environment"
    )
    rootfs: RootfsVolume = Field(
        description="Root filesystem of the system, will be booted by the kernel"
    )

    @model_validator(mode="after")
    def check_requirements(cls, values):
        if values.requirements:
            # GPU filter only supported for QEmu instances with node_hash assigned
            if values.requirements.gpu:
                if (
                    not values.requirements.node
                    or not values.requirements.node.node_hash
                ):
                    raise ValueError("Node hash assignment is needed for GPU support")

                if (
                    values.environment
                    and values.environment.hypervisor != HypervisorType.qemu
                ):
                    raise ValueError("GPU option is only supported for QEmu hypervisor")

            # Terms and conditions filter only supported for PAYG/coco instances with node_hash assigned
            if (
                values.requirements.node
                and values.requirements.node.terms_and_conditions
            ):
                if not values.requirements.node.node_hash:
                    raise ValueError(
                        "Terms_and_conditions field needs a requirements.node.node_hash value"
                    )

                if (
                    not values.payment.is_stream
                    and not values.environment.trusted_execution
                ):
                    raise ValueError(
                        "Only PAYG/coco instances can have a terms_and_conditions"
                    )

        return values
