from __future__ import annotations

from abc import ABC
from typing import Any, Dict, List, Optional

from pydantic import Field

from ..abstract import BaseContent, HashableModel
from .base import MachineType
from .environment import (
    FunctionEnvironment,
    FunctionTriggers,
    HostRequirements,
    MachineResources,
)
from .volume import MachineVolume


class ExecutableContent(HashableModel, BaseContent, ABC):
    """Abstract content for execution messages (Instances, Programs)."""

    type: MachineType = Field(description="Type of execution")
    allow_amend: bool = Field(description="Allow amends to update this function")
    metadata: Optional[Dict[str, Any]] = Field(description="Metadata of the VM")
    variables: Optional[Dict[str, str]] = Field(
        default=None, description="Environment variables available in the VM"
    )
    on: FunctionTriggers = Field(description="Signals that trigger an execution")
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
