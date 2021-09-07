from __future__ import annotations

from abc import ABC, abstractmethod

from enum import Enum
from pydantic import Field, Extra, conint
from typing import Optional, List, Union
from typing_extensions import Literal

from .abstract import BaseContent, HashableModel


class Encoding(str, Enum):
    plain = "plain"
    zip = "zip"
    squashfs = "squashfs"


class MachineType(str, Enum):
    vm_function = "vm-function"


class CodeContent(HashableModel):
    encoding: Encoding
    entrypoint: str
    ref: str
    use_latest: bool = False


class DataContent(HashableModel):
    encoding: Encoding
    mount: str
    ref: str
    use_latest: bool = False


class Export(HashableModel):
    encoding: Encoding
    mount: str


class Subscription(HashableModel):
    class Config:
        extra = Extra.allow


class FunctionTriggers(HashableModel):
    http: bool
    message: Optional[List[Subscription]]


class FunctionEnvironment(HashableModel):
    reproducible: bool = False
    internet: bool = False
    aleph_api: bool = False
    shared_cache: bool = False


class MachineResources(HashableModel):
    vcpus: int = 1
    memory: int = 128
    seconds: int = 1


class FunctionRuntime(HashableModel):
    ref: str
    use_latest: bool = True
    comment: str


class AbstractVolume(HashableModel, ABC):
    comment: Optional[str]
    mount: Optional[str]

    @abstractmethod
    def is_read_only(self): ...

    class Config:
        extra = Extra.forbid


class ImmutableVolume(AbstractVolume):
    ref: str
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
    size_mib: conint(gt=0, le=1000, strict=True)  # Limit to 1 GiB

    def is_read_only(self):
        return False


MachineVolume = Union[ImmutableVolume, EphemeralVolume, PersistentVolume]


class ProgramContent(HashableModel, BaseContent):
    type: MachineType = Field(description="Type of execution")
    allow_amend: bool = Field(description="Allow amends to update this function")
    code: CodeContent = Field(description="Code to execute")
    data: Optional[DataContent] = Field(description="Data to use during computation")
    export: Optional[Export] = Field(description="Data to export after computation")
    on: FunctionTriggers = Field(description="Signals that trigger an execution")
    environment: FunctionEnvironment = Field(description="Properties of the execution environment")
    resources: MachineResources = Field(description="System resources required")
    runtime: FunctionRuntime = Field(
        description="Execution runtime (rootfs with Python interpreter)"
    )
    volumes: List[MachineVolume] = Field(
        default=[],
        description="Volumes to mount on the filesystem"
    )
    replaces: Optional[str] = Field(
        default=None,
        description="Previous version to replace. Must be signed by the same address"
    )
