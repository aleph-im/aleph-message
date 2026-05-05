from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Unix timestamp upper bound (year 2262). Well below the float-precision
# cliff at 2**53 while still leaving headroom for any realistic message.
MAX_CONTENT_TIME = 9_223_372_036.0

# Maximum number of tags per message.
MAX_N_TAGS = 16
# Maximum length of a tag. Real-world tags in production reach ~200 chars,
# so the cap is set to 256 for backward compatibility.
MAX_TAG_LENGTH = 256

Tag = Annotated[str, StringConstraints(min_length=1, max_length=MAX_TAG_LENGTH)]


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
    time: float = Field(ge=0, le=MAX_CONTENT_TIME)

    model_config = ConfigDict(extra="forbid")
