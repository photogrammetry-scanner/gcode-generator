import os


def assert_uint(x, lower_bound=None, upper_bound=None) -> int:
    i = int(x)
    if (i < 0) or (lower_bound and i < lower_bound) or (upper_bound and i > upper_bound):
        raise ValueError
    return i


def environ_or_default(key, default):
    return os.environ.get(key) if os.environ.get(key) else default
