from pydantic import Field

from aleph_message.models.execution.instance import RootfsVolume

from aleph_message.models.execution import BaseExecutableContent


class QemuContent(BaseExecutableContent):
    """Message content for scheduling a VM instance on the network."""

    rootfs: RootfsVolume = Field(
        description="Base image for the kernel, as qcow2"
    )

