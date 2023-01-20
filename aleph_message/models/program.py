from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, NewType, Optional, Union

from pydantic import Extra, Field, conint
from typing_extensions import Literal

from ..utils import gigabyte_to_mebibyte
from .abstract import BaseContent, HashableModel
from .item_hash import ItemHash

Megabytes = NewType("Megabytes", int)


class Encoding(str, Enum):
    plain = "plain"
    zip = "zip"
    squashfs = "squashfs"


class MachineType(str, Enum):
    vm_function = "vm-function"


class CodeContent(HashableModel):
    encoding: Encoding
    entrypoint: str
    ref: ItemHash
    use_latest: bool = False


class DataContent(HashableModel):
    encoding: Encoding
    mount: str
    ref: ItemHash
    use_latest: bool = False


class Export(HashableModel):
    encoding: Encoding
    mount: str


class Subscription(HashableModel):
    class Config:
        extra = Extra.allow


class FunctionTriggers(HashableModel):
    http: bool
    message: Optional[List[Subscription]] = None
    persistent: Optional[bool] = None

    class Config:
        extra = Extra.forbid


class FunctionEnvironment(HashableModel):
    reproducible: bool = False
    internet: bool = False
    aleph_api: bool = False
    shared_cache: bool = False


class MachineResources(HashableModel):
    vcpus: int = 1
    memory: int = 128
    seconds: int = 1


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


class FunctionRuntime(HashableModel):
    ref: ItemHash
    use_latest: bool = True
    comment: str


class AbstractVolume(HashableModel, ABC):
    comment: Optional[str] = None
    mount: Optional[str] = None

    @abstractmethod
    def is_read_only(self):
        ...

    class Config:
        extra = Extra.forbid


class ImmutableVolume(AbstractVolume):
    ref: ItemHash
    use_latest: bool = True

    def is_read_only(self):
        return True


class EphemeralVolume(AbstractVolume):
    ephemeral: Literal[True] = True
    size_mib: conint(gt=0, le=1000, strict=True)  # Limit to 1 GiB

    def is_read_only(self):
        return False


class VolumePersistence(str, Enum):
    host = "host"
    store = "store"


class PersistentVolume(AbstractVolume):
    persistence: VolumePersistence
    name: str
    size_mib: conint(
        gt=0, le=gigabyte_to_mebibyte(100), strict=True
    )  # Limit to 100 GiB

    def is_read_only(self):
        return False


MachineVolume = Union[ImmutableVolume, EphemeralVolume, PersistentVolume]


class ProgramContent(HashableModel, BaseContent):
    type: MachineType = Field(description="Type of execution")
    allow_amend: bool = Field(description="Allow amends to update this function")
    code: CodeContent = Field(description="Code to execute")
    metadata: Optional[Dict[str, Any]] = Field(description="Metadata of the VM")
    variables: Optional[Dict[str, str]] = Field(
        default=None, description="Environment variables available in the VM"
    )
    data: Optional[DataContent] = Field(
        default=None, description="Data to use during computation"
    )
    export: Optional[Export] = Field(
        default=None, description="Data to export after computation"
    )
    on: FunctionTriggers = Field(description="Signals that trigger an execution")
    environment: FunctionEnvironment = Field(
        description="Properties of the execution environment"
    )
    resources: MachineResources = Field(description="System resources required")
    requirements: Optional[HostRequirements] = Field(
        default=None, description="System properties required"
    )
    runtime: FunctionRuntime = Field(
        description="Execution runtime (rootfs with Python interpreter)"
    )
    volumes: List[MachineVolume] = Field(
        default=[], description="Volumes to mount on the filesystem"
    )
    replaces: Optional[str] = Field(
        default=None,
        description="Previous version to replace. Must be signed by the same address",
    )
