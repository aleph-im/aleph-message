import pytest

from aleph_message.exceptions import UnknownHashError
from aleph_message.models.item_hash import ItemHash, ItemType

IPNS_NAME = "k51qzi5uqu5dlvj2baxnqndepeb86cbk3ng7n3i46uzyxzyqj2xjonzllnv0v8"


def test_ipns_name_is_62_chars():
    # Guard: the canonical Ed25519 IPNS base36 form is exactly 62 chars
    assert len(IPNS_NAME) == 62


def test_from_hash_detects_ipns():
    assert ItemType.from_hash(IPNS_NAME) == ItemType.ipns


def test_item_hash_accepts_ipns_name():
    item_hash = ItemHash(IPNS_NAME)
    assert item_hash.item_type == ItemType.ipns
    assert str(item_hash) == IPNS_NAME


def test_uppercase_ipns_name_rejected():
    with pytest.raises(UnknownHashError):
        ItemType.from_hash(IPNS_NAME.upper())


def test_mixed_case_suffix_rejected():
    # Prefix intact, one uppercase char in the suffix: must fail the
    # base36 charset check, not the prefix check.
    mixed = IPNS_NAME[:3] + IPNS_NAME[3].upper() + IPNS_NAME[4:]
    with pytest.raises(UnknownHashError):
        ItemType.from_hash(mixed)


def test_wrong_length_ipns_name_rejected():
    with pytest.raises(UnknownHashError):
        ItemType.from_hash(IPNS_NAME[:-1])
    with pytest.raises(UnknownHashError):
        ItemType.from_hash(IPNS_NAME + "a")


def test_existing_hash_shapes_unaffected():
    assert (
        ItemType.from_hash("QmPZ9gcCEpqKTo6aq61g2nXGUhM4iCL3ewB6LDXZCtioEB")
        == ItemType.ipfs
    )
    assert (
        ItemType.from_hash(
            "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
        )
        == ItemType.ipfs
    )
    assert (
        ItemType.from_hash(
            "c25b0525bc308797d3e35763faf5c560f2974dab802cb4a734ae4e9d1040319e"
        )
        == ItemType.storage
    )
