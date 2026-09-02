from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import (
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from ...utils import Mebibytes
from ..abstract import HashableModel
from ..item_hash import ItemHash

MAX_ADDRESS_REGEX_LENGTH = 256
MAX_SUBSCRIPTION_ENTRIES = 32


class Subscription(HashableModel):
    """A subscription is used to trigger a program in response to a FunctionTrigger."""

    # Subscriptions are user-defined filter criteria; the model intentionally
    # accepts arbitrary keys. Cap the number of entries so a subscription
    # object can't be padded with hundreds of keys.
    @model_validator(mode="after")
    def check_subscription_size(self) -> "Subscription":
        extra = self.__pydantic_extra__ or {}
        if len(extra) > MAX_SUBSCRIPTION_ENTRIES:
            raise ValueError(
                f"Subscription has {len(extra)} entries, "
                f"maximum allowed is {MAX_SUBSCRIPTION_ENTRIES}"
            )
        return self

    model_config = ConfigDict(extra="allow")


class FunctionTriggers(HashableModel):
    """Triggers define the conditions on which the program is started."""

    http: bool = Field(description="Route HTTP requests to the program.")
    message: Optional[List[Subscription]] = Field(
        default=None, description="Run the program in response to new messages."
    )
    persistent: Optional[bool] = Field(
        default=None,
        description="Persist the execution of the program instead of running it on demand.",
    )

    model_config = ConfigDict(extra="forbid")


class NetworkProtocol(str, Enum):
    tcp = "tcp"
    udp = "udp"


class PublishedPort(HashableModel):
    """IPv4 port to forward from a randomly assigned port on the host to the VM."""

    protocol: NetworkProtocol = NetworkProtocol.tcp
    port: int = Field(
        ge=1, le=65535, description="Port open on by the program and to be exposed"
    )


class PortMapping(PublishedPort):
    """IPv4 port mapping from a public port on the host to a port on the VM."""

    # The range 49152–65535 (215 + 214 to 216 − 1) contains dynamic or private
    # ports that cannot be registered with IANA.[406] This range is used for
    # private or customized services, for temporary purposes, and for automatic
    # allocation of ephemeral ports.
    # https://datatracker.ietf.org/doc/html/rfc6335
    public_port: int = Field(
        ge=49152, le=65535, description="Port open routed to the service port"
    )


MAX_VCPUS = 256
MAX_MEMORY_MIB = 1024 * 1024  # 1 TiB
# ~10 years expressed in seconds. Guards against overflow in downstream
# cost calculations while remaining high enough for long-running instances.
MAX_SECONDS = 10 * 365 * 24 * 3600


class MachineResources(HashableModel):
    vcpus: int = Field(default=1, ge=1, le=MAX_VCPUS)
    memory: Mebibytes = Field(default=Mebibytes(128), ge=1, le=MAX_MEMORY_MIB)
    seconds: int = Field(default=1, ge=1, le=MAX_SECONDS)
    published_ports: Optional[List[PublishedPort]] = Field(
        default=None, description="IPv4 ports to map to open ports on the host."
    )


class CpuProperties(HashableModel):
    """CPU properties."""

    architecture: Optional[Literal["x86_64", "arm64"]] = Field(
        default=None, description="CPU architecture"
    )
    vendor: Optional[Union[Literal["AuthenticAMD", "GenuineIntel"], str]] = Field(
        default=None, description="CPU vendor. Allows other vendors."
    )
    # Features described here share the naming conventions of CPU flags (/proc/cpuinfo)
    # but differ in that they must be actually available to the VM.
    features: Optional[List[str]] = Field(
        default=None,
        description="CPU features required by the virtual machine. Examples: 'sev', 'sev_es', 'sev_snp'.",
    )

    model_config = ConfigDict(extra="forbid")


class GpuDeviceClass(str, Enum):
    """GPU device class. Look at https://admin.pci-ids.ucw.cz/read/PD/03"""

    VGA_COMPATIBLE_CONTROLLER = "0300"
    _3D_CONTROLLER = "0302"


class GpuProperties(HashableModel):
    """GPU properties."""

    vendor: str = Field(description="GPU vendor name")
    device_name: str = Field(description="GPU vendor card name")
    device_class: GpuDeviceClass = Field(
        description="GPU device class. Look at https://admin.pci-ids.ucw.cz/read/PD/03"
    )
    device_id: str = Field(description="GPU vendor & device ids")

    model_config = ConfigDict(extra="forbid")


class HypervisorType(str, Enum):
    qemu = "qemu"
    firecracker = "firecracker"


class FunctionEnvironment(HashableModel):
    reproducible: bool = False
    internet: bool = False
    aleph_api: bool = False
    shared_cache: bool = False


class AMDSEVPolicy(int, Enum):
    """AMD Guest Policy for SEV-ES and SEV.

    The firmware maintains a guest policy provided by the guest owner. This policy is enforced by the
    firmware and restricts what configuration and operational commands can be performed on this
    guest by the hypervisor. The policy also requires a minimum firmware level.

    The policy comprises a set of flags that can be combined with bitwise OR.

    See https://github.com/virtee/sev/blob/fbfed998930a0d1e6126462b371890b9f8d77148/src/launch/sev.rs#L245 for reference.
    """

    NO_DBG = 0b1  # Debugging of the guest is disallowed
    NO_KS = 0b10  # Sharing keys with other guests is disallowed
    SEV_ES = 0b100  # SEV-ES is required
    NO_SEND = 0b1000  # Sending the guest to another platform is disallowed
    DOMAIN = 0b10000  # The guest must not be transmitted to another platform that is not in the domain
    SEV = 0b100000  # The guest must not be transmitted to another platform that is not SEV capable


# SEV-SNP guest policy (64-bit). Bit 17 is reserved and must be 1; 0x30000
# also sets bit 16 (SMT allowed), the recommended default.
SNP_POLICY_RESERVED_BIT_17 = 1 << 17
DEFAULT_SNP_POLICY = 0x30000
MAX_VCPU_TYPE_LENGTH = 64
# Protocol-wide cap on the number of launch measurements a single TEE
# declaration may carry (one per vcpu_type in the mixed-fleet case).
MAX_MEASUREMENTS = 16


def validate_snp_policy(policy: int) -> None:
    """Raise ValueError if the value is not a plausible SEV-SNP guest policy."""
    policy_int = int(policy)
    if not 0 <= policy_int < 1 << 64:
        raise ValueError(
            f"SEV-SNP guest policy must be an unsigned 64-bit integer; got {policy_int:#x}"
        )
    if not policy_int & SNP_POLICY_RESERVED_BIT_17:
        raise ValueError(
            "SEV-SNP guest policy must have reserved bit 17 set "
            f"(e.g. {DEFAULT_SNP_POLICY:#x}); got {policy_int:#x}. "
            "Note that SEV policy bit semantics do not apply to SEV-SNP."
        )


class TeePlatform(str, Enum):
    """TEE platforms with a defined launch-measurement semantics.

    Grows over protocol upgrades. Unknown platforms are schema-invalid:
    nothing unverifiable gets network blessing.
    """

    sev_snp = "sev_snp"
    tdx = "tdx"


# Every pinned register is a 48-byte SHA-384 value.
_REGISTER_HEX_LENGTH = 96

# A register value: exactly _REGISTER_HEX_LENGTH lowercase hex characters.
# Encoding length and charset in one pattern keeps the constraint in the JSON
# schema, so consumers generating off `model_json_schema()` (other SDKs, docs)
# see the real shape. Lowercase only, so two encodings of the same value can
# never both validate.
RegisterValue = Annotated[
    str, StringConstraints(pattern=rf"^[0-9a-f]{{{_REGISTER_HEX_LENGTH}}}$")
]


class SevSnpRegisters(HashableModel):
    """The measurement registers SEV-SNP pins: one launch digest.

    A TEE's launch identity is not always a single value. SEV-SNP has one
    launch digest, but platforms such as Intel TDX spread it over several
    hardware registers (MRTD plus RTMRs), which is why the wire shape is an
    object rather than a scalar. Each platform gets a concrete model rather
    than a generic map: `extra="forbid"` plus required fields give the closed
    key set natively, with no validator to keep in step.
    """

    launch: RegisterValue

    model_config = ConfigDict(extra="forbid")


class TdxRegisters(HashableModel):
    """The measurement registers Intel TDX pins: firmware, boot chain, config.

    The pinned set is `{mrtd, rtmr1, rtmr2, mrconfigid}`. `rtmr0` is
    deliberately absent: TDVF extends the VMM-supplied memory layout and the
    variable store into it, which are deployment parameters, not code
    identity. `rtmr3` is absent because it
    carries the launch-TCB commitment, which a verifier *derives* rather than
    compares against a declared constant; keeping it out of the schema lets
    enforcement harden later without a protocol change.
    """

    mrtd: RegisterValue
    rtmr1: RegisterValue
    rtmr2: RegisterValue
    mrconfigid: RegisterValue

    model_config = ConfigDict(extra="forbid")


# Which register model each platform declares. `LaunchMeasurement.registers`
# is discriminated on the sibling `platform` field: the union member key sets
# are disjoint, so parsing is unambiguous, and `check_registers_platform`
# enforces that the parsed member matches the declared platform.
_PLATFORM_REGISTERS: Dict[TeePlatform, type] = {
    TeePlatform.sev_snp: SevSnpRegisters,
    TeePlatform.tdx: TdxRegisters,
}


class LaunchMeasurement(HashableModel):
    """Supervisor-opaque verification annotation, validated by the CCN.

    Declares the measurement registers a verifier should expect. Multiple
    entries (one per vcpu_type) keep a message verifiable across a mixed CPU
    fleet.
    """

    platform: TeePlatform
    registers: Union[SevSnpRegisters, TdxRegisters] = Field(
        description=(
            "Expected measurement registers; sev_snp declares {'launch'}, "
            "tdx declares {'mrtd', 'rtmr1', 'rtmr2', 'mrconfigid'}"
        ),
    )
    vcpu_type: Optional[str] = Field(
        default=None,
        max_length=MAX_VCPU_TYPE_LENGTH,
        description=(
            "QEMU CPU model these registers were computed for (e.g. 'EPYC-v4'). "
            "Required by direct-boot measurement recipes, absent for igvm bundles."
        ),
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def check_registers_platform(self) -> "LaunchMeasurement":
        expected = _PLATFORM_REGISTERS[self.platform]
        if not isinstance(self.registers, expected):
            raise ValueError(
                f"platform {self.platform.value!r} declares "
                f"{expected.__name__} registers, got "
                f"{type(self.registers).__name__}"
            )
        return self


class TrustedExecutionEnvironment(HashableModel):
    """Trusted Execution Environment properties.

    Two families of modes coexist:
    - mode None or "sev" (legacy): AMD SEV/SEV-ES with the CRN-mediated
      launch-secret flow; `firmware` references the confidential OVMF and
      `policy` uses AMD SEV bit semantics (AMDSEVPolicy).
    - measured modes ("sev_snp", "tdx"): measured boot from a runtime bundle
      with direct client-to-guest attestation; `measurements` carry the
      expected measurement registers. In "sev_snp" mode `policy` uses the
      SEV-SNP 64-bit guest-policy semantics. In "tdx" mode there is no
      host-chosen launch policy at all (TDATTRIBUTES and XFAM are set by the
      TDX module and measured, not selected), so `policy` must be left at
      its default.
    """

    firmware: Optional[ItemHash] = Field(
        default=None, description="Confidential OVMF firmware to use (SEV mode only)"
    )
    policy: int = Field(
        default=AMDSEVPolicy.NO_DBG,
        description=(
            "Policy of the TEE. SEV bit semantics in SEV mode (default 0x01, "
            "no debugging); SEV-SNP 64-bit guest policy in sev_snp mode."
        ),
    )
    mode: Optional[Literal["sev", "sev_snp", "tdx"]] = Field(
        default=None,
        description="TEE mode; None means legacy SEV (kept for wire stability)",
    )
    runtime: Optional[ItemHash] = Field(
        default=None,
        description="Measured runtime bundle store message (measured modes only)",
    )
    measurements: Optional[List[LaunchMeasurement]] = Field(
        default=None,
        max_length=MAX_MEASUREMENTS,
        description=(
            "Expected measurement registers (measured modes only); CCN-validated"
        ),
    )
    attestation_port: Optional[int] = Field(
        default=None,
        ge=1,
        le=65535,
        description=(
            "In-guest attestation port (measured modes only); None means the "
            "runtime bundle default (8443)"
        ),
    )

    model_config = ConfigDict(extra="forbid")

    @property
    def is_snp(self) -> bool:
        return self.mode == "sev_snp"

    @property
    def is_measured(self) -> bool:
        """Measured-boot modes: runtime bundle plus declared registers."""
        return self.mode in ("sev_snp", "tdx")

    @model_validator(mode="after")
    def check_mode_consistency(self) -> "TrustedExecutionEnvironment":
        if self.is_measured:
            if self.firmware is not None:
                raise ValueError(
                    "firmware belongs to the SEV flow and must not be set in "
                    f"{self.mode} mode; use runtime instead"
                )
            if self.runtime is None:
                raise ValueError(f"{self.mode} mode requires runtime")
            if not self.measurements:
                raise ValueError(f"{self.mode} mode requires measurements")
            for i, measurement in enumerate(self.measurements):
                if measurement.platform.value != self.mode:
                    raise ValueError(
                        f"measurements[{i}] declares platform "
                        f"{measurement.platform.value!r}, which does not match "
                        f"mode {self.mode!r}"
                    )
            if self.mode == "sev_snp":
                validate_snp_policy(self.policy)
            else:
                # TDX has no host-chosen launch policy: TDATTRIBUTES and XFAM
                # are set by the TDX module and measured, not selected. Reject
                # any non-default value rather than inventing a meaning.
                if self.policy != AMDSEVPolicy.NO_DBG:
                    raise ValueError(
                        "tdx mode has no host-chosen launch policy; "
                        "policy must be left at its default"
                    )
        else:
            for field_name in ("runtime", "measurements", "attestation_port"):
                if getattr(self, field_name) is not None:
                    raise ValueError(
                        f"{field_name} is only valid in the measured TEE modes "
                        "(sev_snp, tdx)"
                    )
        return self


class InstanceEnvironment(HashableModel):
    internet: bool = False
    aleph_api: bool = False
    hypervisor: Optional[HypervisorType] = Field(
        default=None, description="Hypervisor application to use. Default value is QEmu"
    )
    trusted_execution: Optional[TrustedExecutionEnvironment] = Field(
        default=None,
        description="Trusted Execution Environment properties. Defaults to no TEE.",
    )
    # The following fields are kept for retro-compatibility.
    reproducible: bool = False
    shared_cache: bool = False

    @field_validator("trusted_execution", mode="before")
    def check_hypervisor(cls, v, values):
        if v and values.data.get("hypervisor") != HypervisorType.qemu:
            raise ValueError("Trusted Execution Environment is only supported for QEmu")
        return v


class NodeRequirements(HashableModel):
    owner: Optional[str] = Field(default=None, description="Address of the node owner")
    address_regex: Optional[str] = Field(
        default=None,
        max_length=MAX_ADDRESS_REGEX_LENGTH,
        description="Node address must match this regular expression",
    )
    node_hash: Optional[ItemHash] = Field(
        default=None, description="Hash of the compute resource node that must be used"
    )
    terms_and_conditions: Optional[ItemHash] = Field(
        default=None, description="Terms and conditions of this CRN"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("address_regex")
    def check_address_regex_compiles(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            re.compile(v)
        except re.error as exc:
            raise ValueError(f"Invalid regular expression: {exc}") from exc
        return v


class HostRequirements(HashableModel):
    cpu: Optional[CpuProperties] = Field(
        default=None, description="Required CPU properties"
    )
    node: Optional[NodeRequirements] = Field(
        default=None, description="Required Compute Resource Node properties"
    )
    gpu: Optional[List[GpuProperties]] = Field(
        default=None, description="GPUs needed to pass-through from the host"
    )

    @property
    def gpu_requirements(self):
        return self.gpu or []

    model_config = ConfigDict(extra="forbid")
