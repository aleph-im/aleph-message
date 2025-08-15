from __future__ import annotations

from enum import Enum
from typing import Optional

from ..abstract import HashableModel
from ..base import Chain


class Encoding(str, Enum):
    """Code and data can be provided in plain format, as zip or as squashfs partition."""

    plain = "plain"
    zip = "zip"
    squashfs = "squashfs"


class MachineType(str, Enum):
    """Two types of execution environments supported:
    Instance (Virtual Private Server) and Function (Program oriented)."""

    vm_instance = "vm-instance"
    vm_function = "vm-function"


class PaymentType(str, Enum):
    """Payment type for a program execution."""

    hold = "hold"
    superfluid = "superfluid"
    credit = "credit"


class Payment(HashableModel):
    """Payment information for a program execution."""

    chain: Optional[Chain] = None
    """Which chain to check for funds"""
    receiver: Optional[str] = None
    """Optional alternative address to send tokens to"""
    type: PaymentType
    """Whether to pay by holding $ALEPH or by streaming tokens"""

    @property
    def is_stream(self):
        return self.type == PaymentType.superfluid

    @property
    def is_credit(self):
        return self.type == PaymentType.credit


class Interface(str, Enum):
    """Two types of program interfaces supported:
    Running plain binary and ASGI apps."""

    asgi = "asgi"
    binary = "binary"
