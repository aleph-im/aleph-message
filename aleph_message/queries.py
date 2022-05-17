from typing import Union, List

from pydantic import BaseModel, Extra

from aleph_message import PostMessage, ProgramMessage, StoreMessage, AggregateMessage


class MessagesResponse(BaseModel):
    "Response from an Aleph node API."
    messages: List[Union[PostMessage, AggregateMessage, StoreMessage, ProgramMessage]]
    pagination_page: int
    pagination_total: int
    pagination_per_page: int
    pagination_item: str

    class Config:
        extra = Extra.forbid