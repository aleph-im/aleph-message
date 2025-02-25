from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional, Union

from pydantic import ConfigDict, Field, field_validator

from ...utils import Mebibytes
from ..abstract import HashableModel
from ..item_hash import ItemHash


class Subscription(HashableModel):
    """A subscription is used to trigger a program in response to a FunctionTrigger."""

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


class MachineResources(HashableModel):
    vcpus: int = 1
    memory: Mebibytes = Mebibytes(128)
    seconds: int = 1
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


class TrustedExecutionEnvironment(HashableModel):
    """Trusted Execution Environment properties."""

    firmware: Optional[ItemHash] = Field(
        default=None, description="Confidential OVMF firmware to use"
    )
    policy: int = Field(
        default=AMDSEVPolicy.NO_DBG,
        description="Policy of the TEE. Default value is 0x01 for SEV without debugging.",
    )

    model_config = ConfigDict(extra="allow")


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
        default=None, description="Node address must match this regular expression"
    )
    node_hash: Optional[ItemHash] = Field(
        default=None, description="Hash of the compute resource node that must be used"
    )
    terms_and_conditions: Optional[ItemHash] = Field(
        default=None, description="Terms and conditions of this CRN"
    )

    model_config = ConfigDict(extra="forbid")


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

    model_config = ConfigDict(extra="allow")
