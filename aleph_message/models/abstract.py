from typing import List, Optional

from pydantic import BaseModel, Extra, Field


def hashable(obj):
    """Convert `obj` into a hashable object."""
    if isinstance(obj, list):
        # Convert a list to a tuple (hashable)
        return tuple(obj)
    elif isinstance(obj, dict):
        # Convert a dict to a frozenset of items (hashable)
        return frozenset(obj.items())
    return obj


class HashableModel(BaseModel):
    def __hash__(self):
        values = tuple(hashable(value) for value in self.__dict__.values())
        return hash(self.__class__) + hash(values)


class BaseContent(BaseModel):
    """Base template for message content"""

    address: str
    time: float
    tags: Optional[List[str]] = Field(
        default=None, description="Tags associated with the message"
    )

    class Config:
        extra = Extra.forbid
