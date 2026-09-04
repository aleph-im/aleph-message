"""Tests for the V-PROGRAM message type and the SEV-SNP TEE extension.

Design: aleph-vm docs/plans/2026-07-08-confidential-vm-protocol-design.md
"""

import hashlib
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
    TdxRegisters,
    TeePlatform,
    TrustedExecutionEnvironment,
    validate_snp_policy,
)
from aleph_message.models.execution.instance import InstanceContent
from aleph_message.models.execution.vprogram import (
    MAX_CONFIDENTIAL_GPUS,
    TeeVerification,
    VerifiableProgramContent,
    VerifiableProgramEnvironment,
    VerifiableProgramRuntime,
    VerifiedVolume,
    VerifiedWorkload,
)

SNP_DIGEST = "ab" * 48  # 96 hex chars, 48 bytes
SHA256_HEX = "cd" * 32  # 64 hex chars


def tdx_registers() -> dict:
    # The pinned TDX set: {mrtd, rtmr1, rtmr2, mrconfigid}, all SHA-384-sized
    return {
        "mrtd": "11" * 48,
        "rtmr1": "22" * 48,
        "rtmr2": "33" * 48,
        "mrconfigid": "44" * 48,
    }


def test_message_type_v_program():
    assert MessageType.v_program.value == "V-PROGRAM"
    assert MessageType("V-PROGRAM") is MessageType.v_program


def test_launch_measurement_valid():
    m = LaunchMeasurement(
        platform=TeePlatform.sev_snp,
        registers={"launch": SNP_DIGEST},
        vcpu_type="EPYC-v4",
    )
    assert m.platform is TeePlatform.sev_snp
    assert m.registers.launch == SNP_DIGEST
    assert m.vcpu_type == "EPYC-v4"
    # vcpu_type is optional: absent for igvm-recipe bundles
    assert (
        LaunchMeasurement(
            platform="sev_snp", registers={"launch": SNP_DIGEST}
        ).vcpu_type
        is None
    )


def test_launch_measurement_rejects_bad_register_values():
    # wrong length for sev_snp (sha256-sized digest)
    with pytest.raises(ValidationError):
        LaunchMeasurement(platform="sev_snp", registers={"launch": SHA256_HEX})
    # non-hex content
    with pytest.raises(ValidationError):
        LaunchMeasurement(platform="sev_snp", registers={"launch": "zz" * 48})
    # uppercase hex is rejected (canonical form is lowercase)
    with pytest.raises(ValidationError):
        LaunchMeasurement(platform="sev_snp", registers={"launch": "AB" * 48})


def test_launch_measurement_register_key_set_is_closed():
    """The register set is exactly {"launch"}: nothing more, nothing less.

    An unknown register key is as schema-invalid as an unknown platform:
    nothing unverifiable gets network blessing.
    """
    # missing the required key
    with pytest.raises(ValidationError) as exc:
        LaunchMeasurement(platform="sev_snp", registers={})
    assert exc.value.errors()[0]["type"] == "missing"
    # an unknown key alongside the required one
    with pytest.raises(ValidationError) as exc:
        LaunchMeasurement(
            platform="sev_snp",
            registers={"launch": SNP_DIGEST, "mrtd": SNP_DIGEST},
        )
    assert exc.value.errors()[0]["type"] == "extra_forbidden"
    # a register from another platform instead of the required one
    with pytest.raises(ValidationError):
        LaunchMeasurement(platform="sev_snp", registers={"mrtd": SNP_DIGEST})


def test_launch_measurement_register_values_are_type_constrained():
    """Value shape is enforced by the field type, not a validator.

    The error must be located at the offending register so a malformed
    message says which one is wrong.
    """
    with pytest.raises(ValidationError) as exc:
        LaunchMeasurement(platform="sev_snp", registers={"launch": "zz" * 48})
    error = exc.value.errors()[0]
    assert error["type"] == "string_pattern_mismatch"
    # the union member name sits between the field and the register
    assert error["loc"] == ("registers", "SevSnpRegisters", "launch")


def test_launch_measurement_schema_exposes_register_constraints():
    """The constraints must reach model_json_schema().

    Other SDKs and the docs generate off the JSON schema; a shape enforced
    only in Python is invisible to them.
    """
    schema = LaunchMeasurement.model_json_schema()
    registers = schema["$defs"]["SevSnpRegisters"]
    assert registers["required"] == ["launch"]
    assert registers["additionalProperties"] is False
    assert registers["properties"]["launch"]["pattern"] == r"^[0-9a-f]{96}$"


def test_launch_measurement_rejects_unknown_platform():
    # unknown platforms are schema-invalid until a protocol upgrade adds them
    with pytest.raises(ValidationError):
        LaunchMeasurement(platform="sgx", registers={"launch": SNP_DIGEST})


def test_launch_measurement_rejects_legacy_digest_field():
    """The pre-register scalar shape must not silently deserialize.

    `extra="forbid"` turns a stale `digest` key into an error rather than a
    measurement with an empty register map.
    """
    with pytest.raises(ValidationError):
        LaunchMeasurement(platform="sev_snp", digest=SNP_DIGEST)


def test_launch_measurement_forbids_extra_fields():
    with pytest.raises(ValidationError):
        LaunchMeasurement(
            platform="sev_snp", registers={"launch": SNP_DIGEST}, extra_field=1
        )


def test_launch_measurement_tdx_valid():
    m = LaunchMeasurement(
        platform=TeePlatform.tdx, registers=tdx_registers(), vcpu_type="GraniteRapids"
    )
    assert m.platform is TeePlatform.tdx
    assert isinstance(m.registers, TdxRegisters)
    assert m.registers.mrtd == "11" * 48
    assert m.registers.mrconfigid == "44" * 48
    # vcpu_type stays optional on TDX too
    assert (
        LaunchMeasurement(platform="tdx", registers=tdx_registers()).vcpu_type is None
    )


def test_launch_measurement_tdx_key_set_is_closed():
    """The TDX register set is exactly {mrtd, rtmr1, rtmr2, mrconfigid}.

    rtmr0 (deployment parameters) and rtmr3 (derived launch-TCB commitment)
    are deliberately not pinnable: declaring them is schema-invalid.
    """
    for missing in ("mrtd", "rtmr1", "rtmr2", "mrconfigid"):
        registers = tdx_registers()
        del registers[missing]
        with pytest.raises(ValidationError):
            LaunchMeasurement(platform="tdx", registers=registers)
    for forbidden in ("rtmr0", "rtmr3", "launch"):
        with pytest.raises(ValidationError):
            LaunchMeasurement(
                platform="tdx", registers={**tdx_registers(), forbidden: SNP_DIGEST}
            )


def test_launch_measurement_platform_must_match_registers():
    """The union is discriminated on `platform`: cross-wiring is invalid."""
    with pytest.raises(ValidationError, match="does not match|SevSnpRegisters"):
        LaunchMeasurement(platform="sev_snp", registers=tdx_registers())
    with pytest.raises(ValidationError, match="does not match|TdxRegisters"):
        LaunchMeasurement(platform="tdx", registers={"launch": SNP_DIGEST})


def test_launch_measurement_schema_exposes_tdx_constraints():
    schema = LaunchMeasurement.model_json_schema()
    registers = schema["$defs"]["TdxRegisters"]
    assert registers["required"] == ["mrtd", "rtmr1", "rtmr2", "mrconfigid"]
    assert registers["additionalProperties"] is False
    for register in registers["required"]:
        assert registers["properties"][register]["pattern"] == r"^[0-9a-f]{96}$"


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
        measurements=[
            LaunchMeasurement(platform="sev_snp", registers={"launch": SNP_DIGEST})
        ],
    )
    assert v.policy == 0x30000
    with pytest.raises(ValidationError):
        # SEV-style policy value is invalid for SNP (bit 17 unset)
        TeeVerification(
            backend="sev_snp",
            policy=0x1,
            measurements=[
                LaunchMeasurement(platform="sev_snp", registers={"launch": SNP_DIGEST})
            ],
        )


def test_tee_verification_requires_measurements():
    with pytest.raises(ValidationError):
        TeeVerification(backend="sev_snp", measurements=[])


def test_tee_verification_rejects_negative_policy():
    with pytest.raises(ValidationError):
        TeeVerification(
            backend="sev_snp",
            policy=-1,
            measurements=[
                LaunchMeasurement(platform="sev_snp", registers={"launch": SNP_DIGEST})
            ],
        )


def test_tee_verification_rejects_foreign_platform_measurements():
    # a TDX measurement says nothing about an sev_snp backend
    with pytest.raises(ValidationError, match="does not match backend"):
        TeeVerification(
            backend="sev_snp",
            measurements=[LaunchMeasurement(platform="tdx", registers=tdx_registers())],
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
                {
                    "platform": "sev_snp",
                    "registers": {"launch": SNP_DIGEST},
                    "vcpu_type": "EPYC-v4",
                }
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


CONFIDENTIAL_GPU = {"vendor": "nvidia", "device_id": "10de:2b85"}


def test_vprogram_content_gpus_default_empty():
    content = VerifiableProgramContent.model_validate(make_vprogram_content())
    assert content.gpus is None
    assert content.requires_gpu is False


def test_vprogram_content_accepts_one_confidential_gpu():
    content = VerifiableProgramContent.model_validate(
        make_vprogram_content(gpus=[CONFIDENTIAL_GPU])
    )
    assert content.gpus[0].vendor == "nvidia"
    assert content.gpus[0].device_id == "10de:2b85"
    assert content.requires_gpu is True


def test_vprogram_content_caps_confidential_gpus():
    with pytest.raises(ValidationError):
        VerifiableProgramContent.model_validate(
            make_vprogram_content(gpus=[CONFIDENTIAL_GPU] * (MAX_CONFIDENTIAL_GPUS + 1))
        )


def test_vprogram_message_without_gpus_key_still_parses():
    # Messages signed before the gpus field existed carry no such key: an
    # absent field must still parse, since check_content compares the dump
    # to the signed item_content.
    path = Path(__file__).parent / "messages/vprogram_machine.json"
    message_dict = json.loads(path.read_text())
    add_item_content_and_hash(message_dict, inplace=True)
    message = parse_message(message_dict)
    assert isinstance(message, VerifiableProgramMessage)
    assert message.content.gpus is None


@pytest.mark.parametrize(
    "bad",
    [
        {"vendor": "amd", "device_id": "1002:744c"},
        {"vendor": "NVIDIA", "device_id": "10de:2b85"},
        {"vendor": "nvidia", "device_id": "10DE:2B85"},
        {"vendor": "nvidia", "device_id": "2b85"},
        {"vendor": "nvidia", "device_id": "10de:2b85", "pci_host": "06:00.0"},
        {"vendor": "nvidia"},
        {"device_id": "10de:2b85"},
    ],
)
def test_confidential_gpu_rejects_malformed(bad):
    with pytest.raises(ValidationError):
        VerifiableProgramContent.model_validate(make_vprogram_content(gpus=[bad]))


def test_vprogram_content_refuses_inherited_gpu_requirements():
    """`requirements.gpu` is the unverified instance channel; a V-PROGRAM asks
    for a GPU through `gpus` only, or it is not a confidential request."""
    with pytest.raises(ValidationError, match="gpus"):
        VerifiableProgramContent.model_validate(
            make_vprogram_content(
                requirements={
                    "gpu": [
                        {
                            "vendor": "NVIDIA",
                            "device_name": "NVIDIA H100",
                            "device_class": "0300",
                            "device_id": "10de:2504",
                        }
                    ]
                }
            )
        )


def test_confidential_gpu_schema_exposes_constraints():
    schema = VerifiableProgramContent.model_json_schema()
    gpu = schema["$defs"]["ConfidentialGpu"]
    assert gpu["properties"]["device_id"]["pattern"] == r"^[0-9a-f]{4}:[0-9a-f]{4}$"
    assert gpu["properties"]["vendor"]["const"] == "nvidia"
    assert gpu["additionalProperties"] is False
    # gpus is Optional, so pydantic wraps its schema in anyOf[array, null]
    # instead of putting maxItems directly on the properties.gpus object.
    gpus_variants = schema["properties"]["gpus"]["anyOf"]
    array_schema = next(v for v in gpus_variants if v.get("type") == "array")
    assert array_schema["maxItems"] == 1


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


# Serde-parity strict scalars: the CCN stores and serves the raw item_content,
# so a coerced scalar ("1" -> 1, 196608.0 -> 196608, "true" -> True) would
# yield a processed message that strict decoders (the aleph-rs SDK) cannot
# parse. V-PROGRAM scalars must accept exactly what serde accepts.


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("resources", "vcpus"), "2"),
        (("resources", "vcpus"), 2.0),
        (("resources", "vcpus"), True),
        (("resources", "memory"), "2048"),
        (("resources", "memory"), 2048.0),
        (("resources", "seconds"), "30"),
        (("resources", "seconds"), 30.0),
        (("verification", "policy"), "196608"),
        (("verification", "policy"), 196608.0),
        (("verification", "policy"), True),
        (("environment", "internet"), "true"),
        (("environment", "internet"), 1),
        (("environment", "internet"), 0),
        (("allow_amend",), "false"),
        (("allow_amend",), 0),
        (("time",), "1719502000.0"),
        (("time",), True),
    ],
)
def test_vprogram_content_rejects_coerced_scalars(path, value):
    """A scalar serde would reject must not validate, however coercible."""
    content = make_vprogram_content()
    target = content
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        VerifiableProgramContent.model_validate(content)


def test_vprogram_content_time_accepts_json_integer():
    # serde parses an integer JSON number into f64, so an integral time is
    # valid; only strings and booleans are rejected
    content = VerifiableProgramContent.model_validate(
        make_vprogram_content(time=1719502000)
    )
    assert content.time == 1719502000.0


def test_vprogram_content_published_ports_are_strict():
    resources = {
        "vcpus": 2,
        "memory": 2048,
        "seconds": 30,
    }
    for coerced_port in ("8080", 8080.0, True):
        resources["published_ports"] = [{"port": coerced_port}]
        with pytest.raises(ValidationError):
            VerifiableProgramContent.model_validate(
                make_vprogram_content(resources=resources)
            )
    resources["published_ports"] = [{"port": 8080}]
    content = VerifiableProgramContent.model_validate(
        make_vprogram_content(resources=resources)
    )
    assert content.resources.published_ports[0].port == 8080


def test_vprogram_content_dump_is_canonically_stable():
    """Pin the canonical serialization of the fixture content.

    Publishers build item_content from a model dump, so a pydantic upgrade
    or a refactor that reorders a re-declared field would silently shift
    item hashes, and only mainnet would notice. Recompute the constant only
    for a deliberate wire-format change.

    Recomputed 2026-09 when the gpus field was added: gpus is optional
    (default None) so the fixture never sets it, but model_dump() still
    serializes the unset field as "gpus":null, same as every other optional
    field on this model (metadata, requirements, replaces, ...), so the
    dump still gains a key even without a GPU declared.
    """
    fixture = json.loads(
        (Path(__file__).parent / "messages/vprogram_machine.json").read_text()
    )
    content = VerifiableProgramContent.model_validate(fixture["content"])
    canonical = json.dumps(content.model_dump(mode="json"), separators=(",", ":"))
    assert (
        hashlib.sha256(canonical.encode()).hexdigest()
        == "9a1e914a2f63c8c99c08ae7910360cdd043c2591fd8efcf95ce1eb0b4523811d"
    )


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
        "measurements": [{"platform": "sev_snp", "registers": {"launch": SNP_DIGEST}}],
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
        {
            "measurements": [
                {"platform": "sev_snp", "registers": {"launch": SNP_DIGEST}}
            ]
        },
        {"attestation_port": 8443},
    ):
        with pytest.raises(ValidationError, match="sev_snp"):
            TrustedExecutionEnvironment.model_validate({"policy": 1, **extra})


def make_tdx_tee(**overrides) -> dict:
    tee = {
        "mode": "tdx",
        "runtime": ITEM_HASH,
        "measurements": [{"platform": "tdx", "registers": tdx_registers()}],
    }
    tee.update(overrides)
    return tee


def test_trusted_execution_tdx_valid():
    tee = TrustedExecutionEnvironment.model_validate(make_tdx_tee())
    assert tee.is_measured is True
    assert tee.is_snp is False
    assert tee.runtime == ITEM_HASH
    assert tee.measurements[0].platform is TeePlatform.tdx
    assert isinstance(tee.measurements[0].registers, TdxRegisters)
    # attestation_port belongs to the measured modes, tdx included
    tee = TrustedExecutionEnvironment.model_validate(
        make_tdx_tee(attestation_port=8443)
    )
    assert tee.attestation_port == 8443


def test_trusted_execution_tdx_requires_fields():
    for missing in ("runtime", "measurements"):
        tee = make_tdx_tee()
        del tee[missing]
        with pytest.raises(ValidationError, match=missing):
            TrustedExecutionEnvironment.model_validate(tee)


def test_trusted_execution_tdx_forbids_firmware():
    with pytest.raises(ValidationError, match="firmware"):
        TrustedExecutionEnvironment.model_validate(make_tdx_tee(firmware=ITEM_HASH))


def test_trusted_execution_tdx_has_no_policy():
    """TDX has no host-chosen launch policy: TDATTRIBUTES and XFAM are
    measured, not selected. Any non-default value is rejected rather than
    given an invented meaning; the serialized default must keep round-tripping.
    """
    with pytest.raises(ValidationError, match="no host-chosen launch policy"):
        TrustedExecutionEnvironment.model_validate(make_tdx_tee(policy=0x30000))
    # the pydantic default (the legacy SEV NO_DBG bit) round-trips: a dump
    # carries policy=1 and must reparse
    tee = TrustedExecutionEnvironment.model_validate(make_tdx_tee())
    reparsed = TrustedExecutionEnvironment.model_validate(tee.model_dump())
    assert reparsed == tee


def test_trusted_execution_measurement_platform_must_match_mode():
    # an sev_snp measurement under tdx mode (and vice versa) is incoherent
    with pytest.raises(ValidationError, match="does not match"):
        TrustedExecutionEnvironment.model_validate(
            make_tdx_tee(
                measurements=[
                    {"platform": "sev_snp", "registers": {"launch": SNP_DIGEST}}
                ]
            )
        )
    with pytest.raises(ValidationError, match="does not match"):
        TrustedExecutionEnvironment.model_validate(
            make_snp_tee(
                measurements=[{"platform": "tdx", "registers": tdx_registers()}]
            )
        )


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


def test_tdx_instance_requires_credit_payment():
    content_dict = make_snp_instance_content(payment={"type": "credit"})
    content_dict["environment"]["trusted_execution"] = make_tdx_tee()
    content = InstanceContent.model_validate(content_dict)
    assert content.environment.trusted_execution.is_measured

    content_dict = make_snp_instance_content(payment={"type": "hold"})
    content_dict["environment"]["trusted_execution"] = make_tdx_tee()
    with pytest.raises(ValidationError, match="credit"):
        InstanceContent.model_validate(content_dict)


def test_legacy_sev_instance_payment_unrestricted():
    # legacy SEV coco instances keep working with hold payments
    content_dict = make_snp_instance_content(payment={"type": "hold"})
    content_dict["environment"]["trusted_execution"] = {
        "policy": 1,
        "firmware": ITEM_HASH,
    }
    content = InstanceContent.model_validate(content_dict)
    assert content.environment.trusted_execution.is_snp is False
