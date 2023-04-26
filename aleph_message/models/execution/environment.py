from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional, Union

from pydantic import Extra, Field

from ...utils import Mebibytes
from ..abstract import HashableModel


class Subscription(HashableModel):
    """A subscription is used to trigger a program in response to a FunctionTrigger."""

    class Config:
        extra = Extra.allow


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

    class Config:
        extra = Extra.forbid


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

    class Config:
        extra = Extra.forbid


class FunctionEnvironment(HashableModel):
    reproducible: bool = False
    internet: bool = False
    aleph_api: bool = False
    shared_cache: bool = False


class NodeRequirements(HashableModel):
    owner: Optional[str] = Field(default=None, description="Address of the node owner")
    address_regex: Optional[str] = Field(
        default=None, description="Node address must match this regular expression"
    )

    class Config:
        extra = Extra.forbid


class HostRequirements(HashableModel):
    cpu: Optional[CpuProperties] = Field(
        default=None, description="Required CPU properties"
    )
    node: Optional[NodeRequirements] = Field(
        default=None, description="Required Compute Resource Node properties"
    )

    class Config:
        # Allow users to add custom requirements
        extra = Extra.allow
