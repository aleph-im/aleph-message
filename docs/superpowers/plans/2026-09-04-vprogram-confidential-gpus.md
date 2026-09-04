# V-PROGRAM confidential GPU field Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a V-PROGRAM message declare that it needs one NVIDIA GPU in confidential-computing mode.

**Architecture:** One new closed model, `ConfidentialGpu`, and one new bounded list field, `VerifiableProgramContent.gpus`, defaulting to empty so every existing message serializes exactly as today except for the canonical model dump, which gains `"gpus":[]` and whose pinned hash is recomputed once, deliberately. The inherited `requirements.gpu` channel is refused on V-PROGRAMs so there is exactly one way to ask for a GPU. No other message type changes.

**Tech Stack:** Python 3.9+ (pydantic v2, `HashableModel`), pytest via `hatch run testing:cov`, ruff/black/isort/mypy via `hatch run linting:all`. Version comes from the git tag (hatch-vcs); releasing is pushing a tag.

**Spec:** aleph-vm `docs/superpowers/specs/2026-09-04-nvidia-cc-design.md`, section 5.1 (branch `od/nvidia-cc-design` in the aleph-vm repository).

## Global Constraints

- `ConfidentialGpu` is `{vendor: Literal["nvidia"], device_id: str}` with `device_id` constrained to `^[0-9a-f]{4}:[0-9a-f]{4}$` (lowercase `vendor:device` PCI ids, the same string aleph-vm's inventory and the settings aggregate use) and `extra="forbid"`.
- `VerifiableProgramContent.gpus: List[ConfidentialGpu]`, `default=[]`, `max_length=1` (`MAX_CONFIDENTIAL_GPUS = 1`): single-GPU passthrough is the only mode NVIDIA validates on the target SKU.
- A V-PROGRAM whose inherited `requirements.gpu` is set is schema-invalid: the confidential channel is `gpus`, and an unverified GPU request must not reach an attested VM.
- Existing messages (no `gpus` key) keep validating; `item_hash` of the fixture message is unchanged because `item_content` is the signed string, not the dump.
- The canonical-dump pin in `test_vprogram_content_dump_is_canonically_stable` is recomputed exactly once, in the same commit that adds the field, with the docstring's rationale intact.
- No em-dashes anywhere. Commit messages: conventional prefix, no Co-Authored-By trailer.
- Branch `od/vprogram-confidential-gpus` off `origin/main` (tag `1.4.0`, commit `37a4345`), worktree `.worktrees/vprogram-confidential-gpus`.

---

## File map

- Modify: `aleph_message/models/execution/vprogram.py` (constant, `ConfidentialGpu`, `gpus` field, validator)
- Modify: `aleph_message/tests/test_vprogram.py` (positive, negative, cap, pattern, schema, requirements-refusal tests; recomputed canonical hash)
- Modify: `aleph_message/models/execution/__init__.py` only if it re-exports V-PROGRAM models by name (check; `VerifiedVolume` is the precedent)

---

### Task 1: `ConfidentialGpu` and `VerifiableProgramContent.gpus`

**Files:**
- Modify: `aleph_message/models/execution/vprogram.py:31-36` (constants), `:130-150` (models, add after `VerifiedVolume`), `:221-227` (fields, add after `volumes`), `:253-266` (validators)
- Test: `aleph_message/tests/test_vprogram.py`

**Interfaces:**
- Produces: `MAX_CONFIDENTIAL_GPUS = 1`, `CONFIDENTIAL_GPU_DEVICE_ID_PATTERN = r"^[0-9a-f]{4}:[0-9a-f]{4}$"`, `class ConfidentialGpu(HashableModel)`, `VerifiableProgramContent.gpus: List[ConfidentialGpu]`. Consumed by aleph-vm's agent (`content.gpus[].device_id`, `.vendor`) and mirrored in aleph-rs `aleph-types`.

- [ ] **Step 1: Write the failing tests**

Add to `aleph_message/tests/test_vprogram.py`, next to the verified-volume tests (after `test_vprogram_content_caps_verified_volumes`, line 397):

```python
CONFIDENTIAL_GPU = {"vendor": "nvidia", "device_id": "10de:2b85"}


def test_vprogram_content_gpus_default_empty():
    content = VerifiableProgramContent.model_validate(make_vprogram_content())
    assert content.gpus == []


def test_vprogram_content_accepts_one_confidential_gpu():
    content = VerifiableProgramContent.model_validate(
        make_vprogram_content(gpus=[CONFIDENTIAL_GPU])
    )
    assert content.gpus[0].vendor == "nvidia"
    assert content.gpus[0].device_id == "10de:2b85"


def test_vprogram_content_caps_confidential_gpus():
    with pytest.raises(ValidationError):
        VerifiableProgramContent.model_validate(
            make_vprogram_content(gpus=[CONFIDENTIAL_GPU] * 2)  # MAX_CONFIDENTIAL_GPUS + 1
        )


@pytest.mark.parametrize(
    "bad",
    [
        {"vendor": "amd", "device_id": "1002:744c"},
        {"vendor": "NVIDIA", "device_id": "10de:2b85"},
        {"vendor": "nvidia", "device_id": "10DE:2B85"},
        {"vendor": "nvidia", "device_id": "2b85"},
        {"vendor": "nvidia", "device_id": "10de:2b85", "pci_host": "06:00.0"},
        {"vendor": "nvidia"},
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
    assert schema["properties"]["gpus"]["maxItems"] == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/olivier/git/aleph/aleph-message/.worktrees/vprogram-confidential-gpus && hatch run testing:test aleph_message/tests/test_vprogram.py -k "gpu" -q` (if the `testing` env has no `test` script, use `hatch run testing:cov -- -k gpu -q`; check `pyproject.toml` `[tool.hatch.envs.testing.scripts]`).
Expected: `gpus` is an unknown field on the model (pydantic `extra_forbidden`) for the positive tests, and `test_vprogram_content_gpus_default_empty` fails with `AttributeError`.

- [ ] **Step 3: Implement**

In `vprogram.py`, constants block:

```python
# One GPU per confidential VM: single-GPU passthrough is the only NVIDIA CC
# mode validated on the RTX PRO 6000 Blackwell Server Edition (no NVLink).
MAX_CONFIDENTIAL_GPUS = 1
# Lowercase PCI vendor:device ids, the string the CRN inventory and the
# settings aggregate's compatible_gpus use, so one id names a card kind
# everywhere.
CONFIDENTIAL_GPU_DEVICE_ID_PATTERN = r"^[0-9a-f]{4}:[0-9a-f]{4}$"
```

After `VerifiedVolume`:

```python
class ConfidentialGpu(HashableModel):
    """One GPU that must be attached in confidential-computing mode.

    Names a kind of card, never a concrete device: the CRN resolves the id
    against the cards it probed in CC mode. What a client pins about the
    GPU (architecture, driver version) lives in the runtime manifest, not
    here, because those are properties of the measured runtime.
    """

    vendor: Literal["nvidia"] = Field(description="GPU vendor with a confidential-computing mode")
    device_id: str = Field(
        pattern=CONFIDENTIAL_GPU_DEVICE_ID_PATTERN,
        description="PCI vendor:device id, lowercase hex, e.g. 10de:2b85",
    )

    model_config = ConfigDict(extra="forbid")
```

On `VerifiableProgramContent`, after `volumes`:

```python
    # Confidential GPUs only: a plain passthrough GPU has no attestation and
    # would be host-controlled hardware inside an attested VM.
    gpus: List[ConfidentialGpu] = Field(
        default=[],
        max_length=MAX_CONFIDENTIAL_GPUS,
        description="GPUs to attach in confidential-computing mode; at most one",
    )
```

Extend `check_no_unmeasured_inputs` (or add a sibling `check_gpu_channel` validator in the same style) so that `self.requirements is not None and self.requirements.gpu` raises `ValueError("V-PROGRAMs request GPUs through `gpus`, not requirements.gpu")`.

- [ ] **Step 4: Recompute the canonical-dump pin**

Run the suite once: `test_vprogram_content_dump_is_canonically_stable` now fails because the dump carries `"gpus":[]`. Recompute:

```bash
hatch run testing:python - <<'EOF'
import hashlib, json
from pathlib import Path
from aleph_message.models.execution.vprogram import VerifiableProgramContent
fixture = json.loads(Path("aleph_message/tests/messages/vprogram_machine.json").read_text())
content = VerifiableProgramContent.model_validate(fixture["content"])
canonical = json.dumps(content.model_dump(mode="json"), separators=(",", ":"))
print(hashlib.sha256(canonical.encode()).hexdigest())
EOF
```

Replace the constant in the test with the printed value and add one line to the test's docstring: `Recomputed 2026-09 when the gpus field was added.` Confirm `test_parse_message_dispatches_v_program` still passes unchanged: `item_hash` is computed from `item_content` (the fixture's signed string), which does not change.

- [ ] **Step 5: Run everything**

Run: `hatch run testing:cov` then `hatch run linting:all`
Expected: green; mypy clean on the new `Literal` and `List` annotations (the module already imports both).

- [ ] **Step 6: Commit**

```bash
git add aleph_message/models/execution/vprogram.py aleph_message/tests/test_vprogram.py
git commit -m "feat(vprogram): confidential GPU requirement, one NVIDIA card in CC mode"
```

---

### Task 2: re-exports, README and release note

**Files:**
- Modify: `aleph_message/models/execution/__init__.py` (only if V-PROGRAM models are re-exported there; mirror `VerifiedVolume`), `README.md` (if it lists V-PROGRAM fields)

- [ ] **Step 1: Check the re-export surface**

Run: `grep -rn "VerifiedVolume" aleph_message/models/__init__.py aleph_message/models/execution/__init__.py README.md`
If `VerifiedVolume` is re-exported anywhere, add `ConfidentialGpu` beside it with the same style; if not, nothing to do.

- [ ] **Step 2: Commit if anything changed**

```bash
git add -A aleph_message README.md
git commit -m "chore(vprogram): export ConfidentialGpu"
```

- [ ] **Step 3: Open the PR**

`gh pr create --base main --title "feat(vprogram): confidential GPU requirement (gpus field)"` with a body that names the aleph-vm spec, states the wire-format impact (existing messages unchanged; canonical dump gains `"gpus":[]`, pin recomputed), and that the release is a minor bump (`1.5.0` tag) consumed by aleph-vm PR E and by the aleph-rs `aleph-types` mirror.
