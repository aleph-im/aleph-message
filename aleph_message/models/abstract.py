from pydantic import BaseModel, Extra


def list_to_tuple(obj):
    """Convert a list to a tuple (hashable), ignore the rest."""
    if isinstance(obj, list):
        return tuple(obj)
    return obj


class HashableModel(BaseModel):
    def __hash__(self):
        values = tuple(list_to_tuple(value) for value in self.__dict__.values())
        return hash(self.__class__) + hash(values)


class BaseContent(BaseModel):
    "Base template for message content"
    address: str
    time: float

    class Config:
        extra = Extra.forbid
