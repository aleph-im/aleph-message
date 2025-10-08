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
        if getattr(values, "requirements", None):
            if (
                getattr(values.payment, "is_stream", None)
                or getattr(values.payment, "is_credit", None)
            ) and (
                not getattr(values.requirements, "node", None)
                or not getattr(values.requirements.node, "node_hash", None)
            ):
                raise ValueError(
                    "Node hash assignment is needed for PAYG or Credit payments"
                )
            # GPU filter only supported for QEmu instances with node_hash assigned
            if getattr(values.requirements, "gpu", None):
                if not getattr(values.requirements, "node", None) or not getattr(
                    values.requirements.node, "node_hash", None
                ):
                    raise ValueError("Node hash assignment is needed for GPU support")

                if (
                    getattr(values, "environment", None)
                    and getattr(values.environment, "hypervisor", None)
                    != HypervisorType.qemu
                ):
                    raise ValueError("GPU option is only supported for QEmu hypervisor")

            # Terms and conditions filter only supported for PAYG/coco instances with node_hash assigned
            if getattr(values.requirements, "node", None) and getattr(
                values.requirements.node, "terms_and_conditions", None
            ):
                if not getattr(values.requirements.node, "node_hash", None):
                    raise ValueError(
                        "Terms_and_conditions field needs a requirements.node.node_hash value"
                    )

                if not getattr(values.payment, "is_stream", None) and not getattr(
                    values.environment, "trusted_execution", None
                ):
                    raise ValueError(
                        "Only PAYG/coco instances can have a terms_and_conditions"
                    )

        return values
