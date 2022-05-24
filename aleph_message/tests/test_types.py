from aleph_message.models import ItemType

STORAGE_HASH = "b236db23bf5ad005ad7f5d82eed08a68a925020f0755b2a59c03f784499198eb"
IPFS_HASH = "QmPxCe3eHVCdTG5uKnSZTsPGrYvMFTWAAt4PSfK7ETkz4d"


def test_item_type():
    assert ItemType.from_hash(STORAGE_HASH) == ItemType.storage
    assert ItemType.is_storage(STORAGE_HASH)
    assert ItemType.from_hash(IPFS_HASH) == ItemType.ipfs
    assert ItemType.is_ipfs(IPFS_HASH)
