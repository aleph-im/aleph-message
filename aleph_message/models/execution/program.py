from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field

from ..abstract import HashableModel
from ..item_hash import ItemHash
from .abstract import BaseExecutableContent
from .base import Encoding, Interface, MachineType, Payment
from .environment import FunctionTriggers


class FunctionRuntime(HashableModel):
    ref: ItemHash
    use_latest: bool = True
    comment: str


class CodeContent(HashableModel):
    """Reference to the StoreMessage that contains the code or program to be executed."""

    encoding: Encoding
    entrypoint: str
    ref: ItemHash  # Must reference a StoreMessage
    interface: Optional[Interface] = None
    args: Optional[List[str]] = None
    use_latest: bool = False

    @property
    def inferred_interface(self) -> Interface:
        """The initial behaviour is to use asgi, if there is a semicolon in the entrypoint. Else, assume its a binary on port 8000."""
        if self.interface:
            return self.interface
        elif ":" in self.entrypoint:
            return Interface.asgi
        else:
            return Interface.binary


class DataContent(HashableModel):
    """Reference to the StoreMessage that contains the input data of a program."""

    encoding: Encoding
    mount: str
    ref: Optional[ItemHash] = None
    use_latest: Optional[bool] = False


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

    metadata: Optional[dict] = None
    authorized_keys: Optional[List[str]] = None
    payment: Optional[Payment] = None
