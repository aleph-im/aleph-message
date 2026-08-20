"""Tests for the V-PROGRAM message type and the SEV-SNP TEE extension.

Design: aleph-vm docs/plans/2026-07-08-confidential-vm-protocol-design.md
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from aleph_message.models import (
    VerifiableProgramMessage,
    add_item_content_and_hash,
    create_message_from_file,
    parse_message,
)
from aleph_message.models.base import MessageType
from aleph_message.models.execution.environment import (
    DEFAULT_SNP_POLICY,
    LaunchMeasurement,
    TeePlatform,
    TrustedExecutionEnvironment,
    validate_snp_policy,
)
from aleph_message.models.execution.instance import InstanceContent
from aleph_message.models.execution.vprogram import (
    TeeVerification,
    VerifiableProgramContent,
    VerifiableProgramEnvironment,
    VerifiableProgramRuntime,
    VerifiedVolume,
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


def test_validate_snp_policy_bounds():
    # negative values must not slip past the bit-17 check via Python's
    # arbitrary-precision integer semantics (bit 17 of -1 is "set")
    with pytest.raises(ValueError):
        validate_snp_policy(-1)
    # must fit in an unsigned 64-bit integer
    with pytest.raises(ValueError):
        validate_snp_policy((1 << 64) | (1 << 17))


ITEM_HASH = "cafe" * 16  # 64 hex chars, valid storage ItemHash


def test_verifiable_program_runtime():
    r = VerifiableProgramRuntime(ref=ITEM_HASH, comment="compose-runner snp bundle")
    assert r.ref == ITEM_HASH
    # no use_latest field exists: measurements pin exact artifacts
    assert "use_latest" not in VerifiableProgramRuntime.model_fields


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


def test_tee_verification_rejects_negative_policy():
    with pytest.raises(ValidationError):
        TeeVerification(
            backend="sev_snp",
            policy=-1,
            measurements=[LaunchMeasurement(platform="sev_snp", digest=SNP_DIGEST)],
        )


def test_vprogram_environment_defaults():
    env = VerifiableProgramEnvironment()
    assert env.internet is False
    with pytest.raises(ValidationError):
        VerifiableProgramEnvironment(hypervisor="qemu")  # extra fields forbidden
    with pytest.raises(ValidationError):
        VerifiableProgramEnvironment(aleph_api=True)  # dropped legacy program flag


def make_vprogram_content(**overrides) -> dict:
    """Minimal valid VerifiableProgramContent as a dict."""
    content = {
        "address": "0x9319Ad3B7A8E0eE24f2E639c40D8eD124C5520Ba",
        "time": 1719502000.0,
        "allow_amend": False,
        "payment": {"type": "credit"},
        "environment": {"internet": True},
        "resources": {"vcpus": 2, "memory": 2048, "seconds": 30},
        "runtime": {"ref": ITEM_HASH, "comment": "compose-runner snp bundle"},
        "workload": {
            "ref": ITEM_HASH,
            "hash_tree": ITEM_HASH,
            "roothash": "cd" * 32,
        },
        "verification": {
            "backend": "sev_snp",
            "policy": 0x30000,
            "measurements": [
                {"platform": "sev_snp", "digest": SNP_DIGEST, "vcpu_type": "EPYC-v4"}
            ],
        },
    }
    content.update(overrides)
    return content


def test_vprogram_content_valid():
    content = VerifiableProgramContent.model_validate(make_vprogram_content())
    assert content.payment.is_credit
    assert content.is_confidential is True
    assert content.volumes == []
    assert content.verification.measurements[0].vcpu_type == "EPYC-v4"


def test_vprogram_content_is_credit_only():
    for payment_type in ("hold", "superfluid"):
        with pytest.raises(ValidationError, match="credit"):
            VerifiableProgramContent.model_validate(
                make_vprogram_content(payment={"type": payment_type})
            )


def test_vprogram_content_payment_required():
    content = make_vprogram_content()
    del content["payment"]
    with pytest.raises(ValidationError):
        VerifiableProgramContent.model_validate(content)
    with pytest.raises(ValidationError):
        VerifiableProgramContent.model_validate(make_vprogram_content(payment=None))


def test_verified_volume():
    v = VerifiedVolume(
        ref=ITEM_HASH, hash_tree=ITEM_HASH, roothash="ab" * 32, comment="llm weights"
    )
    assert v.roothash == "ab" * 32
    # no mount field: binding is positional via the measured cmdline, and an
    # unmeasured mount mapping would let a malicious host permute volumes
    assert "mount" not in VerifiedVolume.model_fields
    with pytest.raises(ValidationError):
        VerifiedVolume(ref=ITEM_HASH, hash_tree=ITEM_HASH, roothash="ab" * 31)
    with pytest.raises(ValidationError):
        VerifiedVolume(
            ref=ITEM_HASH, hash_tree=ITEM_HASH, roothash="ab" * 32, mount="/data"
        )


def test_vprogram_content_accepts_verified_volumes():
    volume = {"ref": ITEM_HASH, "hash_tree": ITEM_HASH, "roothash": "ab" * 32}
    content = VerifiableProgramContent.model_validate(
        make_vprogram_content(volumes=[volume])
    )
    assert content.volumes[0].roothash == "ab" * 32


def test_vprogram_content_rejects_unverified_volumes():
    # classic machine volumes are unmeasured input inside an attested VM
    for bad_volume in (
        {"ephemeral": True, "mount": "/var/cache", "size_mib": 5},
        {"ref": ITEM_HASH, "mount": "/opt/venv", "use_latest": False},
        {"persistence": "host", "name": "scratch", "mount": "/var/raw", "size_mib": 1},
    ):
        with pytest.raises(ValidationError):
            VerifiableProgramContent.model_validate(
                make_vprogram_content(volumes=[bad_volume])
            )


def test_vprogram_content_caps_verified_volumes():
    volume = {"ref": ITEM_HASH, "hash_tree": ITEM_HASH, "roothash": "ab" * 32}
    with pytest.raises(ValidationError):
        VerifiableProgramContent.model_validate(
            make_vprogram_content(volumes=[volume] * 9)  # MAX_VERIFIED_VOLUMES + 1
        )


def test_vprogram_content_rejects_unmeasured_inputs():
    with pytest.raises(ValidationError, match="variables"):
        VerifiableProgramContent.model_validate(
            make_vprogram_content(variables={"VM_CUSTOM_VARIABLE": "SOMETHING"})
        )
    key = (
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGULT6A41Msmw2KEu0R9MvUjhuWNAsbdeZ0DOwYbt4Qt"
        " user@example"
    )
    with pytest.raises(ValidationError, match="authorized_keys"):
        VerifiableProgramContent.model_validate(
            make_vprogram_content(authorized_keys=[key])
        )


def test_vprogram_content_rejects_amendment():
    # An amend would let the measured stack change under a fixed deployment
    # identity; upgrades are explicit redeployments (new message, new hash).
    with pytest.raises(ValidationError, match="immutable"):
        VerifiableProgramContent.model_validate(make_vprogram_content(allow_amend=True))
    with pytest.raises(ValidationError, match="immutable"):
        VerifiableProgramContent.model_validate(
            make_vprogram_content(replaces="cafe" * 16)
        )


def test_vprogram_content_node_hash_is_optional():
    # dispatch is scheduler-driven; node_hash is only an optional placement pin
    content = VerifiableProgramContent.model_validate(
        make_vprogram_content(requirements={"node": {"node_hash": ITEM_HASH}})
    )
    assert content.requirements.node.node_hash == ITEM_HASH


def test_vprogram_message_machine():
    path = Path(__file__).parent / "messages/vprogram_machine.json"
    message = create_message_from_file(path, factory=VerifiableProgramMessage)
    assert isinstance(message, VerifiableProgramMessage)
    assert message.type == "V-PROGRAM"
    assert message.content.is_confidential
    assert hash(message.content)
    # the factory-less path must dispatch to the same class
    assert isinstance(create_message_from_file(path), VerifiableProgramMessage)


def test_parse_message_dispatches_v_program():
    path = Path(__file__).parent / "messages/vprogram_machine.json"
    message_dict = json.loads(path.read_text())
    add_item_content_and_hash(message_dict, inplace=True)
    message = parse_message(message_dict)
    assert isinstance(message, VerifiableProgramMessage)


def make_snp_tee(**overrides) -> dict:
    tee = {
        "mode": "sev_snp",
        "policy": 0x30000,
        "runtime": ITEM_HASH,
        "measurements": [{"platform": "sev_snp", "digest": SNP_DIGEST}],
    }
    tee.update(overrides)
    return tee


def test_trusted_execution_legacy_sev_unchanged():
    # the exact shape of the existing confidential fixture must keep parsing
    tee = TrustedExecutionEnvironment.model_validate(
        {
            "policy": 1,
            "firmware": "e258d248fda94c63753607f7c4494ee0fcbe92f1a76bfdac795c9d84101eb317",
        }
    )
    assert tee.mode is None  # None means legacy SEV
    assert tee.is_snp is False
    # dump stability: no new keys appear on legacy content
    dump = tee.model_dump(exclude_none=True)
    assert set(dump) == {"policy", "firmware"}


def test_trusted_execution_snp_valid():
    tee = TrustedExecutionEnvironment.model_validate(make_snp_tee())
    assert tee.is_snp is True
    assert tee.runtime == ITEM_HASH
    assert tee.measurements[0].platform is TeePlatform.sev_snp


def test_trusted_execution_snp_requires_fields():
    for missing in ("runtime", "measurements"):
        tee = make_snp_tee()
        del tee[missing]
        with pytest.raises(ValidationError, match=missing):
            TrustedExecutionEnvironment.model_validate(tee)


def test_trusted_execution_snp_forbids_firmware():
    with pytest.raises(ValidationError, match="firmware"):
        TrustedExecutionEnvironment.model_validate(
            make_snp_tee(
                firmware="e258d248fda94c63753607f7c4494ee0fcbe92f1a76bfdac795c9d84101eb317"
            )
        )


def test_trusted_execution_snp_policy_bit17():
    # the implicit SEV default (0x1) is not a valid SNP policy: an explicit,
    # SNP-valid policy is effectively required in sev_snp mode
    tee = make_snp_tee()
    del tee["policy"]
    with pytest.raises(ValidationError, match="bit 17"):
        TrustedExecutionEnvironment.model_validate(tee)


def test_trusted_execution_snp_rejects_negative_policy():
    with pytest.raises(ValidationError):
        TrustedExecutionEnvironment.model_validate(make_snp_tee(policy=-1))


def test_trusted_execution_sev_forbids_snp_fields():
    for extra in (
        {"runtime": ITEM_HASH},
        {"measurements": [{"platform": "sev_snp", "digest": SNP_DIGEST}]},
        {"attestation_port": 8443},
    ):
        with pytest.raises(ValidationError, match="sev_snp"):
            TrustedExecutionEnvironment.model_validate({"policy": 1, **extra})


def make_snp_instance_content(payment: dict) -> dict:
    return {
        "address": "0x9319Ad3B7A8E0eE24f2E639c40D8eD124C5520Ba",
        "time": 1719502000.0,
        "allow_amend": False,
        "payment": payment,
        "environment": {
            "internet": True,
            "aleph_api": False,
            "hypervisor": "qemu",
            "trusted_execution": make_snp_tee(),
        },
        "resources": {"vcpus": 2, "memory": 2048, "seconds": 30},
        "rootfs": {
            "parent": {"ref": ITEM_HASH, "use_latest": False},
            "persistence": "host",
            "size_mib": 4096,
        },
    }


def test_snp_instance_requires_credit_payment():
    content = InstanceContent.model_validate(
        make_snp_instance_content(payment={"type": "credit"})
    )
    assert content.environment.trusted_execution.is_snp

    with pytest.raises(ValidationError, match="credit"):
        InstanceContent.model_validate(
            make_snp_instance_content(payment={"type": "hold"})
        )
    with pytest.raises(ValidationError, match="credit"):
        InstanceContent.model_validate(
            make_snp_instance_content(payment={"type": "superfluid", "chain": "AVAX"})
        )


def test_legacy_sev_instance_payment_unrestricted():
    # legacy SEV coco instances keep working with hold payments
    content_dict = make_snp_instance_content(payment={"type": "hold"})
    content_dict["environment"]["trusted_execution"] = {
        "policy": 1,
        "firmware": ITEM_HASH,
    }
    content = InstanceContent.model_validate(content_dict)
    assert content.environment.trusted_execution.is_snp is False
