from __future__ import annotations

from abc import ABC
from typing import Annotated, Any, Dict, List, Optional, Sequence, Union

from pydantic import Field

from ..abstract import BaseContent, HashableModel
from .base import Payment
from .environment import (
    FunctionEnvironment,
    GpuProperties,
    HostRequirements,
    InstanceEnvironment,
    MachineResources,
)
from .volume import MachineVolume

MAX_METADATA_ENTRIES = 256
MAX_AUTHORIZED_KEYS = 256
MAX_AUTHORIZED_KEY_LENGTH = 8192
MAX_VARIABLE_ENTRIES = 256
MAX_VARIABLE_KEY_LENGTH = 128
MAX_VARIABLE_VALUE_LENGTH = 4096
MAX_VOLUMES = 256
MAX_REPLACES_LENGTH = 128

VariableKey = Annotated[str, Field(max_length=MAX_VARIABLE_KEY_LENGTH)]
VariableValue = Annotated[str, Field(max_length=MAX_VARIABLE_VALUE_LENGTH)]
AuthorizedKey = Annotated[str, Field(max_length=MAX_AUTHORIZED_KEY_LENGTH)]


class BaseExecutableContent(HashableModel, BaseContent, ABC):
    """Abstract content for execution messages (Instances, Programs)."""

    allow_amend: bool = Field(description="Allow amends to update this function")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        max_length=MAX_METADATA_ENTRIES,
        description="Metadata of the VM",
    )
    authorized_keys: Optional[List[AuthorizedKey]] = Field(
        default=None,
        max_length=MAX_AUTHORIZED_KEYS,
        description="SSH public keys authorized to connect to the VM",
    )
    variables: Optional[Dict[VariableKey, VariableValue]] = Field(
        default=None,
        max_length=MAX_VARIABLE_ENTRIES,
        description="Environment variables available in the VM",
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
        default=[],
        max_length=MAX_VOLUMES,
        description="Volumes to mount on the filesystem",
    )
    replaces: Optional[str] = Field(
        default=None,
        max_length=MAX_REPLACES_LENGTH,
        description="Previous version to replace. Must be signed by the same address",
    )

    @property
    def gpu_requirements(self) -> Sequence[GpuProperties]:
        """Returns the GPU requirements of the VM, if any."""
        return self.requirements.gpu_requirements if self.requirements else []

    @property
    def requires_gpu(self) -> bool:
        """Whether the VM requires one or more GPUs."""
        return len(self.gpu_requirements) > 0

    @property
    def is_confidential(self) -> bool:
        """Whether the VM is configured as a confidential VM."""
        return (
            isinstance(self.environment, InstanceEnvironment)
            and self.environment.trusted_execution is not None
        )
