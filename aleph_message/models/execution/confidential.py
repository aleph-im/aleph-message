from __future__ import annotations

from pydantic import Field

from .abstract import BaseExecutableContent
from .base import Payment
from .volume import RootfsVolume
from ..item_hash import ItemHash


class ConfidentialPayment(Payment):
    """Payment information for a confidential instance execution."""

    # Added node item hash required on the payment field
    node_hash: ItemHash
    """Node item hash that execute the message"""


class ConfidentialContent(BaseExecutableContent):
    """Message content for scheduling a VM confidential instance on the network."""

    # Make payment field required for confidential messages
    payment: ConfidentialPayment = Field(
        description="Payment details for the confidential execution"
    )
    rootfs: RootfsVolume = Field(
        description="Root filesystem of the system, will be booted by the kernel"
    )
