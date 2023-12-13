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


class Payment(HashableModel):
    """Payment information for a program execution."""

    chain: Chain
    """Which chain to check for funds"""
    receiver_address: Optional[str]
    """Optional alternative address to send tokens to"""
    payment_type: PaymentType
    """Whether to pay by holding $ALEPH or by streaming tokens"""
