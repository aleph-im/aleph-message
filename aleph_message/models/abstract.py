from pydantic import BaseModel, Extra


class HashableModel(BaseModel):
    def __hash__(self):
        return hash(self.__class__) + hash(tuple(self.__dict__.values()))


class BaseContent(BaseModel):
    "Base template for message content"
    address: str
    time: float

    class Config:
        extra = Extra.forbid
