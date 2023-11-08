from __future__ import annotations

from abc import ABC
from typing import Any, Dict, List, Optional

from pydantic import Field

from .environment import (
    FunctionEnvironment,
    HostRequirements,
    MachineResources,
)
from .volume import MachineVolume
from ..abstract import BaseContent, HashableModel


class BaseExecutableContent(HashableModel, BaseContent, ABC):
    """Abstract content for execution messages (Instances, Programs)."""

    allow_amend: bool = Field(description="Allow amends to update this function")
    metadata: Optional[Dict[str, Any]] = Field(description="Metadata of the VM")
    authorized_keys: Optional[List[str]] = Field(
        description="SSH public keys authorized to connect to the VM",
    )
    variables: Optional[Dict[str, str]] = Field(
        default=None, description="Environment variables available in the VM"
    )
    environment: FunctionEnvironment = Field(
        description="Properties of the execution environment"
    )
    resources: MachineResources = Field(description="System resources required")
    requirements: Optional[HostRequirements] = Field(
        default=None, description="System properties required"
    )
    volumes: List[MachineVolume] = Field(
        default=[], description="Volumes to mount on the filesystem"
    )
    replaces: Optional[str] = Field(
        default=None,
        description="Previous version to replace. Must be signed by the same address",
    )
