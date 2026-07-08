"""Tests for the V-PROGRAM message type and the SEV-SNP TEE extension.

Design: aleph-vm docs/plans/2026-07-08-confidential-vm-protocol-design.md
"""

from aleph_message.models.base import MessageType


def test_message_type_v_program():
    assert MessageType.v_program.value == "V-PROGRAM"
    assert MessageType("V-PROGRAM") is MessageType.v_program
