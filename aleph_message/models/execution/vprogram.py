"""Verifiable programs (V-Programs): auto-booting confidential VMs whose full
software stack is attestable via SEV-SNP runtime attestation.

Design: aleph-vm docs/plans/2026-07-08-confidential-vm-protocol-design.md
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import ConfigDict, Field, StrictBool, model_validator
from typing_extensions import Self

from ...utils import Mebibytes
from ..abstract import MAX_CONTENT_TIME, HashableModel
from ..item_hash import ItemHash
from .abstract import BaseExecutableContent
from .base import Payment
from .environment import (
    DEFAULT_SNP_POLICY,
    MAX_MEASUREMENTS,
    MAX_MEMORY_MIB,
    MAX_SECONDS,
    MAX_VCPUS,
    LaunchMeasurement,
    MachineResources,
    PublishedPort,
    validate_snp_policy,
)

MAX_RUNTIME_COMMENT_LENGTH = 1024
# sha256 dm-verity root hash, as printed by veritysetup format
VERITY_ROOTHASH_PATTERN = r"^[0-9a-f]{64}$"
# Bounded by the kernel cmdline budget: each roothash costs ~65 bytes in the
# measured verified_volumes= slot.
MAX_VERIFIED_VOLUMES = 8
# One GPU per confidential VM: single-GPU passthrough is the only NVIDIA CC
# mode validated on the RTX PRO 6000 Blackwell Server Edition (no NVLink).
MAX_CONFIDENTIAL_GPUS = 1
# Lowercase PCI vendor:device ids, the string the CRN inventory and the
# settings aggregate's compatible_gpus use, so one id names a card kind
# everywhere.
CONFIDENTIAL_GPU_DEVICE_ID_PATTERN = r"^[0-9a-f]{4}:[0-9a-f]{4}$"


# Serde-parity strict scalars.
#
# The CCN (pyaleph) validates content with these models but stores and serves
# the RAW item_content dict, so any pydantic coercion it performs ("1" -> 1,
# 196608.0 -> 196608, "true" -> True) yields a processed message that strict
# decoders (the aleph-rs SDK, serde) cannot parse. A single such message used
# to poison every page-strict history fetch (aleph-rs#386). V-PROGRAM scalar
# fields therefore accept exactly what serde accepts: JSON integers for int
# fields, true/false for bools, int-or-float for time. Nothing unverifiable
# gets network blessing, and nothing network-blessed is undecodable.


class StrictPublishedPort(PublishedPort):
    """PublishedPort with serde-strict port (see module note above)."""

    port: int = Field(
        strict=True,
        ge=1,
        le=65535,
        description="Port open on by the program and to be exposed",
    )


class StrictMachineResources(MachineResources):
    """MachineResources with serde-strict scalars (see module note above)."""

    vcpus: int = Field(default=1, strict=True, ge=1, le=MAX_VCPUS)
    memory: Mebibytes = Field(
        default=Mebibytes(128), strict=True, ge=1, le=MAX_MEMORY_MIB
    )
    seconds: int = Field(default=1, strict=True, ge=1, le=MAX_SECONDS)
    published_ports: Optional[List[StrictPublishedPort]] = Field(  # type: ignore[assignment]
        default=None, description="IPv4 ports to map to open ports on the host."
    )


class VerifiableProgramRuntime(HashableModel):
    """The measured platform: a store message holding the runtime manifest,
    which pins the OVMF, kernel, initrd and dm-verity platform rootfs (plus
    its hash tree) by content hash, and declares the cmdline template, boot
    format and attestation protocols the runtime implements.

    There is deliberately no use_latest: the measurements in the message pin
    exact artifacts, so the reference must be immutable (resolved as an exact
    item hash, never through file tags).
    """

    ref: ItemHash = Field(description="Store message of the runtime manifest")
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


class VerifiedVolume(HashableModel):
    """An extra read-only data volume bound into the attested TCB, e.g. LLM
    weights or datasets shared across deployments.

    Volumes are positional: the measured cmdline carries the roothashes in
    list order (verified_volumes=h1,h2,...), the guest init verity-verifies
    device i against roothash i and exposes it at a well-known indexed path,
    and the verity-bound workload contract maps it onward. There is
    deliberately no mount field: an unmeasured mount mapping would let a
    malicious host permute volumes.
    """

    ref: ItemHash = Field(description="Store message of the volume data image")
    hash_tree: ItemHash = Field(
        description="Store message of the dm-verity hash tree for the data image"
    )
    roothash: str = Field(
        pattern=VERITY_ROOTHASH_PATTERN,
        description="dm-verity root hash (sha256, lowercase hex); measured via cmdline",
    )
    comment: str = Field(default="", max_length=MAX_RUNTIME_COMMENT_LENGTH)

    model_config = ConfigDict(extra="forbid")


class ConfidentialGpu(HashableModel):
    """One GPU that must be attached in confidential-computing mode.

    Names a kind of card, never a concrete device: the CRN resolves the id
    against the cards it probed in CC mode. What a client pins about the
    GPU (architecture, driver version) lives in the runtime manifest, not
    here, because those are properties of the measured runtime.
    """

    vendor: Literal["nvidia"] = Field(
        description="GPU vendor with a confidential-computing mode"
    )
    device_id: str = Field(
        pattern=CONFIDENTIAL_GPU_DEVICE_ID_PATTERN,
        description="PCI vendor:device id, lowercase hex, e.g. 10de:2b85",
    )

    model_config = ConfigDict(extra="forbid")


class TeeVerification(HashableModel):
    """TEE launch configuration plus supervisor-opaque measurement annotations."""

    backend: Literal["sev_snp"] = Field(description="TEE backend the VM launches with")
    policy: int = Field(
        default=DEFAULT_SNP_POLICY,
        strict=True,
        ge=0,
        lt=1 << 64,
        description="SEV-SNP 64-bit guest policy (not SEV bit semantics)",
    )
    measurements: List[LaunchMeasurement] = Field(
        min_length=1,
        max_length=MAX_MEASUREMENTS,
        description="Expected measurement registers; never sent to the supervisor",
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def check_policy(self) -> Self:
        validate_snp_policy(self.policy)
        return self

    @model_validator(mode="after")
    def check_measurements_platform(self) -> Self:
        # The register-model union is discriminated on `platform`; a
        # measurement for another TEE says nothing about this backend.
        for i, measurement in enumerate(self.measurements):
            if measurement.platform.value != self.backend:
                raise ValueError(
                    f"measurements[{i}] declares platform "
                    f"{measurement.platform.value!r}, which does not match "
                    f"backend {self.backend!r}"
                )
        return self


class VerifiableProgramEnvironment(HashableModel):
    """Execution environment flags. The hypervisor is always QEMU."""

    internet: StrictBool = False

    model_config = ConfigDict(extra="forbid")


class VerifiableProgramContent(BaseExecutableContent):
    """Message content for scheduling a verifiable program (V-Program): an
    auto-booting SEV-SNP VM whose full software stack is attestable.

    Unlike classic programs there is no code/entrypoint/triggers model (the
    workload contract belongs to the runtime bundle) and no hypervisor choice
    (always QEMU). Unlike instances, the rootfs is Aleph-provided and measured;
    the user contribution is the verity-bound workload volume.

    Every input reaching the guest is measured or verity-bound: extra volumes
    must be verified (VerifiedVolume), and the inherited unmeasured input
    channels (variables, authorized_keys) are rejected. Workload environment
    variables belong in the verity-bound workload contract.

    V-Programs are also immutable: the inherited amendment channel
    (allow_amend, replaces) is rejected, because an amend would let the
    measured stack change under a fixed deployment identity. Upgrading is
    an explicit redeployment: publish a new message, clients re-target it.
    """

    # Serde-parity overrides of inherited lax scalars (see module note above
    # the strict resource models): a coerced value would be stored raw by the
    # CCN and become undecodable to strict readers.
    time: float = Field(strict=True, ge=0, le=MAX_CONTENT_TIME)
    allow_amend: StrictBool = Field(description="Allow amends to update this function")
    resources: StrictMachineResources = Field(description="System resources required")
    payment: Payment = Field(description="Payment details; V-Programs are credit-only")
    # VerifiableProgramEnvironment is deliberately not a member of the
    # Function/InstanceEnvironment union on BaseExecutableContent: V-Programs
    # have their own environment shape (see class docstring above).
    environment: VerifiableProgramEnvironment = Field(  # type: ignore[assignment]
        description="Properties of the execution environment"
    )
    runtime: VerifiableProgramRuntime = Field(
        description="The measured platform (runtime manifest)"
    )
    workload: VerifiedWorkload = Field(
        description="The user's verity-bound workload volume"
    )
    verification: TeeVerification = Field(
        description="TEE launch config and expected launch measurements"
    )
    # Only verity-bound volumes are allowed: unverified extra volumes would be
    # attacker-controllable input inside an attested VM.
    volumes: List[VerifiedVolume] = Field(  # type: ignore[assignment]
        default=[],
        max_length=MAX_VERIFIED_VOLUMES,
        description="Extra read-only volumes, verity-bound via the measured cmdline",
    )
    # Confidential GPUs only: a plain passthrough GPU has no attestation and
    # would be host-controlled hardware inside an attested VM. Optional
    # rather than defaulted, because an absent field and an empty list both
    # mean "no GPU": check_content compares the dump to the signed
    # item_content, and messages signed before this field existed must keep
    # parsing without it.
    gpus: Optional[List[ConfidentialGpu]] = Field(
        default=None,
        max_length=MAX_CONFIDENTIAL_GPUS,
        description="GPUs to attach in confidential-computing mode; at most one",
    )

    @property
    def is_confidential(self) -> bool:
        """V-Programs always run in a confidential VM."""
        return True

    # gpu_requirements (inherited, reads requirements.gpu) stays empty on
    # V-Programs by design: ConfidentialGpu is not a GpuProperties.
    @property
    def requires_gpu(self) -> bool:
        return bool(self.gpus)

    @model_validator(mode="after")
    def check_payment_is_credit(self) -> Self:
        if not self.payment.is_credit:
            raise ValueError(
                "V-Programs are credit-only: holder-tier and PAYG stream "
                "payments are not supported"
            )
        return self

    @model_validator(mode="after")
    def check_immutable(self) -> Self:
        if self.allow_amend or self.replaces is not None:
            raise ValueError(
                "V-Programs are immutable: amendment would let the measured "
                "stack change under a fixed deployment identity; publish a "
                "new message instead"
            )
        return self

    @model_validator(mode="after")
    def check_no_unmeasured_inputs(self) -> Self:
        if self.variables:
            raise ValueError(
                "variables are not supported for V-Programs: environment "
                "variables would reach the guest unmeasured; ship them in the "
                "verity-bound workload instead"
            )
        if self.authorized_keys:
            raise ValueError(
                "authorized_keys are not supported for V-Programs: host key "
                "injection has no place in an attested VM"
            )
        if self.requirements is not None and self.requirements.gpu:
            raise ValueError(
                "requirements.gpu is not supported for V-Programs: an "
                "unattested passthrough GPU has no place in an attested VM; "
                "declare the card in gpus instead"
            )
        return self
