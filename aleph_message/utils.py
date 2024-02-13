from __future__ import annotations

import json
import math
from datetime import date, datetime, time
from typing import Any, Dict, NewType, Union

from pydantic import BaseModel
from pydantic.json import pydantic_encoder

Megabytes = NewType("Megabytes", int)
Mebibytes = NewType("Mebibytes", int)
Gigabytes = NewType("Gigabytes", int)


def gigabyte_to_mebibyte(n: Gigabytes) -> Mebibytes:
    """Convert Gigabytes to Mebibytes (the unit used for VM volumes).
    Rounds up to ensure that data of a given size will fit in the space allocated.
    """
    mebibyte = 2**20
    gigabyte = 10**9
    return Mebibytes(math.ceil(n * gigabyte / mebibyte))


def extended_json_encoder(obj: Any) -> Any:
    """
    Extended JSON encoder for dumping objects that contain pydantic models and datetime objects.
    """
    if isinstance(obj, datetime):
        return obj.timestamp()
    elif isinstance(obj, date):
        return obj.toordinal()
    elif isinstance(obj, time):
        return obj.hour * 3600 + obj.minute * 60 + obj.second + obj.microsecond / 1e6
    else:
        return pydantic_encoder(obj)


def dump_content(obj: Union[Dict, BaseModel]) -> str:
    """Dump message content as JSON string."""
    if isinstance(obj, dict):
        # without None values
        obj = {k: v for k, v in obj.items() if v is not None}
        return json.dumps(obj, separators=(",", ":"), default=extended_json_encoder)
    elif isinstance(obj, BaseModel):
        return json.dumps(
            obj.dict(exclude_none=True),
            separators=(",", ":"),
            default=extended_json_encoder,
        )
    else:
        raise TypeError(f"Invalid type: `{type(obj)}`")
