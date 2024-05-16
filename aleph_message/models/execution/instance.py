from __future__ import annotations

from pydantic import Field

from .abstract import BaseExecutableContent
from .volume import RootfsVolume


class InstanceContent(BaseExecutableContent):
    """Message content for scheduling a VM instance on the network."""

    rootfs: RootfsVolume = Field(
        description="Root filesystem of the system, will be booted by the kernel"
    )
