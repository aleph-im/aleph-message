from __future__ import annotations

from enum import Enum


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
