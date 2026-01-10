from __future__ import annotations

from abc import ABC
from typing import Any, Dict, List, Optional, Union, Sequence

from pydantic import Field

from ..abstract import BaseContent, HashableModel
from .base import Payment
from .environment import (
    FunctionEnvironment,
    HostRequirements,
    InstanceEnvironment,
    MachineResources, GpuProperties,
)
from .volume import MachineVolume


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
    environment: Union[FunctionEnvironment, InstanceEnvironment] = Field(
        description="Properties of the execution environment"
    )
    resources: MachineResources = Field(description="System resources required")
    payment: Optional[Payment] = Field(description="Payment details for the execution")
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

    @property
    def gpu_requirements(self) -> Sequence[GpuProperties]:
        """Returns the GPU requirements of the VM, if any."""
        return self.requirements.gpu if self.requirements else []

    @property
    def requires_gpu(self) -> bool:
        """Whether the VM requires one or more GPUs."""
        return len(self.gpu_requirements) > 0

    @property
    def is_confidential(self) -> bool:
        """Whether the VM is configured as a confidential VM."""
        return self.environment.trusted_execution is not None

