# Aleph.im BaseMessage Specification

This library aims to provide an easy way to create, update and validate 
messages from Aleph.im.

It mainly consists in [pydantic](https://pydantic-docs.helpmanual.io/) 
models that provide field type validation and IDE autocompletion for messages.

## Status

Currently, only basic type validation is included. Advanced data and signature
validation is not included.

In the future, this library would be useful within other projects such as
the client library [aleph-client](https://github.com/aleph-im/aleph-client).

## Usage

```python
import requests
from aleph_message import BaseMessage
from pydantic import ValidationError

message_dict = requests.get(ALEPH_API_SERVER + "/api/v0/messages.json?hashes=...").json()

try:
    message = BaseMessage(**message_dict)
    print(message.sender)
except ValidationError as e:
    print(e.json())
```
