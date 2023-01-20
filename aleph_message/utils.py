import math


def gigabyte_to_mebibyte(n: int) -> int:
    """Convert Gigabytes to Mebibytes (the unit used for VM volumes).
    Rounds up to ensure that data of a given size will fit in the space allocated.
    """
    mebibyte = 2**20
    gigabyte = 10**9
    return math.ceil(n * gigabyte / mebibyte)
