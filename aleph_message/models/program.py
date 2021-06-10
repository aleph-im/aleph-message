from enum import Enum
from typing import Optional, List

from pydantic import Field

from .abstract import BaseContent, HashableModel


class Encoding(str, Enum):
    plain = "plain"
    zip = "zip"


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


class FunctionTriggers(HashableModel):
    http: bool


class FunctionEnvironment(HashableModel):
    reproducible: bool = False
    internet: bool = False
    aleph_api: bool = False


class MachineResources(HashableModel):
    vcpus: int = 1
    memory: int = 128
    seconds: int = 1


class FunctionRuntime(HashableModel):
    ref: str
    use_latest: bool = True
    comment: str


class MachineVolume(HashableModel):
    mount: str
    ref: str
    use_latest: bool = True


class ProgramContent(HashableModel, BaseContent):
    type: MachineType = Field(description="Type of execution")
    allow_amend: bool = Field(description="Allow amends to update this function")
    code: CodeContent = Field(description="Code to execute")
    data: Optional[DataContent] = Field(description="Data to use during computation")
    export: Optional[Export] = Field(description="Data to export after computation")
    on: FunctionTriggers = Field("Signals that trigger an execution")
    environment: FunctionEnvironment = Field("Properties of the execution environment")
    resources: MachineResources = Field("System resources required")
    runtime: FunctionRuntime = Field(
        "Execution runtime (rootfs with Python interpreter)"
    )
    volumes: List[MachineVolume] = Field(
        "Volumes to mount on the filesystem"
    )
    replaces: Optional[str] = Field(
        description="Previous version to replace. Must be signed by the same address"
    )
