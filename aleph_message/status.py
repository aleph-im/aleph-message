from enum import Enum


class MessageStatus(str, Enum):
    """The current of the processing of a message by a node.

    pending: the message is waiting to be processed.
    processed: the message has been processed successfully.
    rejected: the message is invalid and has been rejected.
    forgotten: a FORGET message required this message content to be deleted.
    """

    PENDING = "pending"
    PROCESSED = "processed"
    REJECTED = "rejected"
    FORGOTTEN = "forgotten"
