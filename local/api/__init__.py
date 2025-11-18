"""
Provides `TisV2Api`, a class to manage all calls to and from a specific server.

Also provides `get_api(server, **kwargs)` to obtain a `TisV2Api` instance that points to a server by name (or by `Server` class).
"""


from .base import TisV2Api, AdminKillAllResponse
from .helpers import get_api
