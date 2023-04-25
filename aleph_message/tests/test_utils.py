from aleph_message.utils import Gigabytes, gigabyte_to_mebibyte


def test_gigabyte_to_mebibyte():
    assert gigabyte_to_mebibyte(Gigabytes(1)) == 954
    assert gigabyte_to_mebibyte(Gigabytes(100)) == 95368
