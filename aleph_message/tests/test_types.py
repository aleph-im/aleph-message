import pytest
from pydantic import BaseModel, ValidationError

from aleph_message.models import ItemHash, ItemType

STORAGE_HASH = "b236db23bf5ad005ad7f5d82eed08a68a925020f0755b2a59c03f784499198eb"
IPFS_HASH = "QmPxCe3eHVCdTG5uKnSZTsPGrYvMFTWAAt4PSfK7ETkz4d"


def test_item_type():
    assert ItemType.from_hash(STORAGE_HASH) == ItemType.storage
    assert ItemType.is_storage(STORAGE_HASH)
    assert ItemType.from_hash(IPFS_HASH) == ItemType.ipfs
    assert ItemType.is_ipfs(IPFS_HASH)


class ModelWithItemHash(BaseModel):
    hash: ItemHash


def test_item_hash():
    storage_object_dict = {"hash": STORAGE_HASH}
    storage_object = ModelWithItemHash.parse_obj(storage_object_dict)
    assert storage_object.hash == STORAGE_HASH
    assert storage_object.hash.item_type == ItemType.storage

    ipfs_object_dict = {"hash": IPFS_HASH}
    ipfs_object = ModelWithItemHash.parse_obj(ipfs_object_dict)
    assert ipfs_object.hash == IPFS_HASH
    assert ipfs_object.hash.item_type == ItemType.ipfs

    invalid_object_dict = {"hash": "fake-hash"}
    with pytest.raises(ValidationError):
        _ = ModelWithItemHash.parse_obj(invalid_object_dict)
