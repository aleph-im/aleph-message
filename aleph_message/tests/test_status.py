from aleph_message.status import MessageStatus


def test_message_status():
    assert MessageStatus.PENDING == "pending"
