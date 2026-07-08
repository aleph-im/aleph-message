"""Verifiable programs (V-Programs): auto-booting confidential VMs whose full
software stack is attestable via SEV-SNP runtime attestation.

Design: aleph-vm docs/plans/2026-07-08-confidential-vm-protocol-design.md
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import ConfigDict, Field, model_validator
from typing_extensions import Self

from ..abstract import HashableModel
from ..item_hash import ItemHash
from .abstract import BaseExecutableContent
from .base import Payment
from .environment import DEFAULT_SNP_POLICY, LaunchMeasurement, validate_snp_policy

MAX_RUNTIME_COMMENT_LENGTH = 1024
MAX_MEASUREMENTS = 16
# sha256 dm-verity root hash, as printed by veritysetup format
VERITY_ROOTHASH_PATTERN = r"^[0-9a-f]{64}$"


class ConfidentialRuntime(HashableModel):
    """The measured platform: a store object bundling the manifest, OVMF,
    kernel, initrd, and the dm-verity platform rootfs with its hash tree.

    There is deliberately no use_latest: the measurements in the message pin
    exact artifacts, so the reference must be immutable.
    """

    ref: ItemHash = Field(description="Store message of the measured runtime bundle")
    comment: str = Field(default="", max_length=MAX_RUNTIME_COMMENT_LENGTH)

    model_config = ConfigDict(extra="forbid")


class VerifiedWorkload(HashableModel):
    """The user's code: a read-only ext4 volume bound into the measured TCB
    via its dm-verity root hash on the kernel cmdline (workload_roothash=)."""

    ref: ItemHash = Field(description="Store message of the workload data image")
    hash_tree: ItemHash = Field(
        description="Store message of the dm-verity hash tree for the data image"
    )
    roothash: str = Field(
        pattern=VERITY_ROOTHASH_PATTERN,
        description="dm-verity root hash (sha256, lowercase hex); measured via cmdline",
    )

    model_config = ConfigDict(extra="forbid")


class TeeVerification(HashableModel):
    """TEE launch configuration plus supervisor-opaque measurement annotations."""

    backend: Literal["sev_snp"] = Field(description="TEE backend the VM launches with")
    policy: int = Field(
        default=DEFAULT_SNP_POLICY,
        ge=0,
        lt=1 << 64,
        description="SEV-SNP 64-bit guest policy (not SEV bit semantics)",
    )
    measurements: List[LaunchMeasurement] = Field(
        min_length=1,
        max_length=MAX_MEASUREMENTS,
        description="Expected launch digests; never sent to the supervisor",
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def check_policy(self) -> Self:
        validate_snp_policy(self.policy)
        return self


class VerifiableProgramEnvironment(HashableModel):
    """Execution environment flags. The hypervisor is always QEMU."""

    internet: bool = False
    aleph_api: bool = False

    model_config = ConfigDict(extra="forbid")


class VerifiableProgramContent(BaseExecutableContent):
    """Message content for scheduling a verifiable program (V-Program): an
    auto-booting SEV-SNP VM whose full software stack is attestable.

    Unlike classic programs there is no code/entrypoint/triggers model (the
    workload contract belongs to the runtime bundle) and no hypervisor choice
    (always QEMU). Unlike instances, the rootfs is Aleph-provided and measured;
    the user contribution is the verity-bound workload volume.

    Extra `volumes` are allowed but are OUTSIDE the attested TCB: they are
    neither measured nor verity-verified.
    """

    payment: Payment = Field(description="Payment details; V-Programs are credit-only")
    # VerifiableProgramEnvironment is deliberately not a member of the
    # Function/InstanceEnvironment union on BaseExecutableContent: V-Programs
    # have their own environment shape (see class docstring above).
    environment: VerifiableProgramEnvironment = Field(  # type: ignore[assignment]
        description="Properties of the execution environment"
    )
    runtime: ConfidentialRuntime = Field(
        description="The measured platform (runtime bundle)"
    )
    workload: VerifiedWorkload = Field(
        description="The user's verity-bound workload volume"
    )
    verification: TeeVerification = Field(
        description="TEE launch config and expected launch measurements"
    )
    attestation_port: Optional[int] = Field(
        default=None,
        ge=1,
        le=65535,
        description=(
            "In-guest attestation port; None means the runtime bundle's "
            "declared default (8443). Plumbed through the measured cmdline."
        ),
    )

    @property
    def is_confidential(self) -> bool:
        """V-Programs always run in a confidential VM."""
        return True

    @model_validator(mode="after")
    def check_payment_is_credit(self) -> Self:
        if not self.payment.is_credit:
            raise ValueError(
                "V-Programs are credit-only: holder-tier and PAYG stream "
                "payments are not supported"
            )
        return self
