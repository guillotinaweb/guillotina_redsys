import secrets
import string
import time


_ALNUM = string.ascii_uppercase + string.digits


def generate_redsys_order_id(length: int = 12) -> str:
    """
    Generate a Redsys Ds_Merchant_Order:
    - 4–12 chars, alphanumeric
    - starts with 4 digits (common Redsys expectation)
    - remainder is random A–Z/0–9
    """
    if not (4 <= length <= 12):
        raise ValueError("length must be between 4 and 12")

    # 4-digit rolling timestamp component (00:00–99:99 style)
    first4 = f"{int(time.time() * 1000) % 10000:04d}"

    # random tail
    tail_len = length - 4
    tail = "".join(secrets.choice(_ALNUM) for _ in range(tail_len))

    return first4 + tail
