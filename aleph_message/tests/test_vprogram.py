"""Tests for the V-PROGRAM message type and the SEV-SNP TEE extension.

Design: aleph-vm docs/plans/2026-07-08-confidential-vm-protocol-design.md
"""

import pytest
from pydantic import ValidationError

from aleph_message.models.base import MessageType
from aleph_message.models.execution.environment import (
    DEFAULT_SNP_POLICY,
    LaunchMeasurement,
    TeePlatform,
    validate_snp_policy,
)
from aleph_message.models.execution.vprogram import (
    ConfidentialRuntime,
    TeeVerification,
    VerifiableProgramEnvironment,
    VerifiedWorkload,
)

SNP_DIGEST = "ab" * 48  # 96 hex chars, 48 bytes
SHA256_HEX = "cd" * 32  # 64 hex chars


def test_message_type_v_program():
    assert MessageType.v_program.value == "V-PROGRAM"
    assert MessageType("V-PROGRAM") is MessageType.v_program


def test_launch_measurement_valid():
    m = LaunchMeasurement(
        platform=TeePlatform.sev_snp, digest=SNP_DIGEST, vcpu_type="EPYC-v4"
    )
    assert m.platform is TeePlatform.sev_snp
    assert m.vcpu_type == "EPYC-v4"
    # vcpu_type is optional: absent for igvm-recipe bundles
    assert LaunchMeasurement(platform="sev_snp", digest=SNP_DIGEST).vcpu_type is None


def test_launch_measurement_rejects_bad_digests():
    # wrong length for sev_snp (sha256-sized digest)
    with pytest.raises(ValidationError):
        LaunchMeasurement(platform="sev_snp", digest=SHA256_HEX)
    # non-hex content
    with pytest.raises(ValidationError):
        LaunchMeasurement(platform="sev_snp", digest="zz" * 48)
    # uppercase hex is rejected (canonical form is lowercase)
    with pytest.raises(ValidationError):
        LaunchMeasurement(platform="sev_snp", digest="AB" * 48)


def test_launch_measurement_rejects_unknown_platform():
    # unknown platforms are schema-invalid until a protocol upgrade adds them
    with pytest.raises(ValidationError):
        LaunchMeasurement(platform="tdx", digest=SNP_DIGEST)


def test_launch_measurement_forbids_extra_fields():
    with pytest.raises(ValidationError):
        LaunchMeasurement(platform="sev_snp", digest=SNP_DIGEST, extra_field=1)


def test_validate_snp_policy():
    validate_snp_policy(DEFAULT_SNP_POLICY)  # 0x30000: bits 16+17
    validate_snp_policy(1 << 17)
    with pytest.raises(ValueError):
        validate_snp_policy(0x1)  # the AMD SEV default lacks bit 17
    with pytest.raises(ValueError):
        validate_snp_policy(0x10000)  # SMT bit alone, no bit 17


ITEM_HASH = "cafe" * 16  # 64 hex chars, valid storage ItemHash


def test_confidential_runtime():
    r = ConfidentialRuntime(ref=ITEM_HASH, comment="compose-runner snp bundle")
    assert r.ref == ITEM_HASH
    # no use_latest field exists: measurements pin exact artifacts
    assert "use_latest" not in ConfidentialRuntime.model_fields


def test_verified_workload_roothash_validation():
    w = VerifiedWorkload(ref=ITEM_HASH, hash_tree=ITEM_HASH, roothash="cd" * 32)
    assert w.roothash == "cd" * 32
    with pytest.raises(ValidationError):
        VerifiedWorkload(ref=ITEM_HASH, hash_tree=ITEM_HASH, roothash="cd" * 31)
    with pytest.raises(ValidationError):
        VerifiedWorkload(ref=ITEM_HASH, hash_tree=ITEM_HASH, roothash="ZZ" * 32)


def test_tee_verification_defaults_and_policy():
    v = TeeVerification(
        backend="sev_snp",
        measurements=[LaunchMeasurement(platform="sev_snp", digest=SNP_DIGEST)],
    )
    assert v.policy == 0x30000
    with pytest.raises(ValidationError):
        # SEV-style policy value is invalid for SNP (bit 17 unset)
        TeeVerification(
            backend="sev_snp",
            policy=0x1,
            measurements=[LaunchMeasurement(platform="sev_snp", digest=SNP_DIGEST)],
        )


def test_tee_verification_requires_measurements():
    with pytest.raises(ValidationError):
        TeeVerification(backend="sev_snp", measurements=[])


def test_vprogram_environment_defaults():
    env = VerifiableProgramEnvironment()
    assert env.internet is False
    assert env.aleph_api is False
    with pytest.raises(ValidationError):
        VerifiableProgramEnvironment(hypervisor="qemu")  # extra fields forbidden
