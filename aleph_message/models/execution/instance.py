from __future__ import annotations

from typing import List, Optional

from pydantic import Field, model_validator
from typing_extensions import Self

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

    payment: Optional[Payment] = None
    environment: InstanceEnvironment = Field(
        description="Properties of the instance execution environment"
    )
    rootfs: RootfsVolume = Field(
        description="Root filesystem of the system, will be booted by the kernel"
    )

    @model_validator(mode="after")
    def check_requirements(self) -> Self:
        if self.requirements:
            # Streamed (PAYG) payments must target a specific node. Credit
            # payments are billed independently of the host, so they no longer
            # need to pin a node.
            if (self.payment and self.payment.is_stream) and (
                not self.requirements.node or not self.requirements.node.node_hash
            ):
                raise ValueError("Node hash assignment is needed for PAYG payments")
            # GPU filter only supported for QEmu instances. The GPU host must be
            # pinned with a node_hash, except for credit payments which are not
            # tied to a specific node.
            if self.requirements.gpu:
                if not (self.payment and self.payment.is_credit) and (
                    not self.requirements.node or not self.requirements.node.node_hash
                ):
                    raise ValueError("Node hash assignment is needed for GPU support")

                if (
                    self.environment
                    and self.environment.hypervisor != HypervisorType.qemu
                ):
                    raise ValueError("GPU option is only supported for QEmu hypervisor")

            # Terms and conditions filter only supported for PAYG/coco instances with node_hash assigned
            if self.requirements.node and self.requirements.node.terms_and_conditions:
                if not self.requirements.node.node_hash:
                    raise ValueError(
                        "Terms_and_conditions field needs a requirements.node.node_hash value"
                    )

                if (
                    not self.payment
                    or (not self.payment.is_stream and not self.payment.is_credit)
                ) and not self.environment.trusted_execution:
                    raise ValueError(
                        "Only PAYG/CoCo/Credit instances can have a terms_and_conditions"
                    )

        return self

    @model_validator(mode="after")
    def check_measured_tee_payment(self) -> Self:
        # Measured confidential instances (SEV-SNP, TDX) are credit-only.
        trusted_execution = self.environment.trusted_execution
        if trusted_execution is not None and trusted_execution.is_measured:
            if not (self.payment and self.payment.is_credit):
                raise ValueError(
                    f"{trusted_execution.mode} confidential instances are "
                    "credit-only: holder-tier and PAYG stream payments are "
                    "not supported"
                )
        return self
