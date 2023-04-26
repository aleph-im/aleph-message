from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from .environment import FunctionTriggers
from ..abstract import HashableModel
from ..item_hash import ItemHash
from .abstract import BaseExecutableContent
from .base import Encoding, MachineType


class FunctionRuntime(HashableModel):
    ref: ItemHash
    use_latest: bool = True
    comment: str


class CodeContent(HashableModel):
    """Reference to the StoreMessage that contains the code or program to be executed."""

    encoding: Encoding
    entrypoint: str
    ref: ItemHash  # Must reference a StoreMessage
    use_latest: bool = False


class DataContent(HashableModel):
    """Reference to the StoreMessage that contains the input data of a program."""

    encoding: Encoding
    mount: str
    ref: ItemHash
    use_latest: bool = False


class Export(HashableModel):
    """Data to export after computations."""

    encoding: Encoding
    mount: str


class ProgramContent(BaseExecutableContent):
    """Message content or scheduling a program on the network."""

    type: Literal[MachineType.vm_function]
    code: CodeContent = Field(description="Code to execute")
    runtime: FunctionRuntime = Field(
        description="Execution runtime (rootfs with Python interpreter)"
    )
    data: Optional[DataContent] = Field(
        default=None, description="Data to use during computation"
    )
    export: Optional[Export] = Field(
        default=None, description="Data to export after computation"
    )
    on: FunctionTriggers = Field(description="Signals that trigger an execution")
