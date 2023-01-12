from aleph_message.utils import gigabyte_to_mebibyte


def test_gigabyte_to_mebibyte():
    assert gigabyte_to_mebibyte(1) == 954
    assert gigabyte_to_mebibyte(100) == 95368
