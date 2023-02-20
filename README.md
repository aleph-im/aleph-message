# Aleph.im Message Specification

This library aims to provide an easy way to create, update and manipulate 
messages from Aleph.im.

It mainly consists in [pydantic](https://pydantic-docs.helpmanual.io/) 
models that provide field type validation and IDE autocompletion for messages.

This library provides:
* schema validation when parsing messages.
* cryptographic hash validation that the `item_hash` matches the content of the message.
* type validation using type checkers such as [mypy](https://www.mypy-lang.org/) in development environments.
* autocompletion support in development editors.

The `item_hash` is commonly used as unique message identifier on Aleph.im.

Cryptographic signatures are out of scope of this library and part of the `aleph-sdk-python`
project, due to their extended scope and dependency on cryptographic libraries.

This library is used in both client and node software of Aleph.im.

## Usage

```shell
pip install aleph-message
```

```python
import requests
from aleph_message import Message
from pydantic import ValidationError

ALEPH_API_SERVER = "https://official.aleph.cloud"
MESSAGE_ITEM_HASH = "9b21eb870d01bf64d23e1d4475e342c8f958fcd544adc37db07d8281da070b00"

message_dict = requests.get(ALEPH_API_SERVER + "/api/v0/messages.json?hashes=" + MESSAGE_ITEM_HASH).json()

try:
    message = Message(**message_dict["messages"][0])
    print(message.sender)
except ValidationError as e:
    print(e.json(indent=4))
```
