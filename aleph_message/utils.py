from __future__ import annotations

import math
from typing import NewType

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
