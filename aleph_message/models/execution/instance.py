from __future__ import annotations

from typing import Any, Dict, Literal

from pydantic import Field

from .abstract import BaseExecutableContent
from .base import MachineType
from .volume import PersistentVolume


class InstanceContent(BaseExecutableContent):
    """Message content for scheduling a VM instance on the network."""

    rootfs: PersistentVolume = Field(
        description="Root filesystem of the system, will be booted by the kernel"
    )
    cloud_config: Dict[str, Any] = Field(
        description="Cloud-init configuration, see https://cloudinit.readthedocs.io/en/latest/"
    )
