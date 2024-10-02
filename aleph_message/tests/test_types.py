import copy

import pytest
from pydantic import BaseModel, ValidationError

from aleph_message.exceptions import UnknownHashError
from aleph_message.models import ItemHash, ItemType

STORAGE_HASH = ItemHash(
    "b236db23bf5ad005ad7f5d82eed08a68a925020f0755b2a59c03f784499198eb"
)
IPFS_HASH = ItemHash("QmPxCe3eHVCdTG5uKnSZTsPGrYvMFTWAAt4PSfK7ETkz4d")


def test_item_type():
    assert ItemType.from_hash(STORAGE_HASH) == ItemType.storage
    assert ItemType.is_storage(STORAGE_HASH)
    assert ItemType.from_hash(IPFS_HASH) == ItemType.ipfs
    assert ItemType.is_ipfs(IPFS_HASH)


class ModelWithItemHash(BaseModel):
    hash: ItemHash


def test_item_hash():
    storage_object_dict = {"hash": STORAGE_HASH}
    storage_object = ModelWithItemHash.model_validate(storage_object_dict)
    assert storage_object.hash == STORAGE_HASH
    assert storage_object.hash.item_type == ItemType.storage

    ipfs_object_dict = {"hash": IPFS_HASH}
    ipfs_object = ModelWithItemHash.model_validate(ipfs_object_dict)
    assert ipfs_object.hash == IPFS_HASH
    assert ipfs_object.hash.item_type == ItemType.ipfs
    assert repr(ipfs_object.hash).startswith("<ItemHash value='")

    invalid_object_dict = {"hash": "fake-hash"}
    with pytest.raises(ValidationError):
        _ = ModelWithItemHash.model_validate(invalid_object_dict)

    with pytest.raises(ValidationError):
        _ = ModelWithItemHash.model_validate({"hash": 12345})


def test_item_hash_serialization():
    ipfs_object = ModelWithItemHash(hash=STORAGE_HASH)
    assert (
        ipfs_object.model_dump_json()
        == '{"hash":"b236db23bf5ad005ad7f5d82eed08a68a925020f0755b2a59c03f784499198eb"}'
    )

    ipfs_object = ModelWithItemHash(hash=IPFS_HASH)
    assert (
        ipfs_object.model_dump_json()
        == '{"hash":"QmPxCe3eHVCdTG5uKnSZTsPGrYvMFTWAAt4PSfK7ETkz4d"}'
    )


def test_copy_item_hash():
    item_hash = ItemHash(STORAGE_HASH)

    item_hash_copy = copy.copy(item_hash)
    assert item_hash_copy == item_hash
    assert item_hash_copy.item_type == item_hash.item_type

    item_hash_deepcopy = copy.deepcopy(item_hash)
    assert item_hash_deepcopy == item_hash
    assert item_hash_deepcopy.item_type == item_hash.item_type


def test_bad_item_hashes():
    with pytest.raises(UnknownHashError):
        ItemHash("This is not a hash !")
    # UnknownHashError should be a ValueError
    with pytest.raises(ValueError):
        ItemHash("This is not a hash !")
