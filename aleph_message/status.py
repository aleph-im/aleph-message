from enum import Enum


class MessageStatus(str, Enum):
    """The current of the processing of a message by a node.

    pending: the message is waiting to be processed.
    processed: the message has been processed successfully.
    rejected: the message is invalid and has been rejected.
    forgotten: a FORGET message required this message content to be deleted.
    removing: the resources of the message will be removed soon if the wallet don't get enough balance.
    removed: the resources of the message has been removed.
    """

    PENDING = "pending"
    PROCESSED = "processed"
    REJECTED = "rejected"
    FORGOTTEN = "forgotten"
    REMOVING = "removing"
    REMOVED = "removed"
