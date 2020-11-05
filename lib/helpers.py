"""Shared functions across commands"""
import os
import pwd
import re
import time


def get_username():
    """Return the user's user name"""
    return pwd.getpwuid(os.getuid())[0]


def str_to_seconds(duration):
    """Convert a string of format "XdXhXmXs" to seconds or return the integer value"""
    units = {"d": 86400, "h": 3600, "m": 60, "s": 1}

    matches = re.findall("^([0-9-]+[%s])+$" % "".join(units.keys()), duration.lower())

    if not matches:
        return int(duration)

    return sum([int(match.strip()[:-1]) * units.get(match.strip()[-1], 0)
                for match in matches
                if match.strip()[-1] in units.keys()])


def retry_every(every=None, limit=None):
    """Decorator to retry every X seconds until Y seconds limit is exceeded"""
    if not every:
        every = 1

    if not limit:
        limit = -1  # Forever

    def outer(func):
        def wrapper(*args, **kwargs):
            count = 0
            ret = func(*args, **kwargs)
            while ret is None:
                if count >= limit:
                    raise Exception("Retry limit reached.")
                time.sleep(every)
                ret = func(*args, **kwargs)
                count += 1
            return ret
        return wrapper
    return outer
