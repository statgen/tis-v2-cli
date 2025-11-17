"""
Handles loading, saving and manipulating registered servers.

Provides dataclasses `Server`, `RefPanel`, and `Population`, as well as `normalize_name()` for ID matching.

Provides server lookup utilities `get_all_servers()`, `get_server()`.

Provides server registration utilities `register_server()`, `register_defaults()`.
"""


from .base import Population, RefPanel, Server, normalize_name
from .lookup import get_all_servers, get_server
from .register import register_server
from .display import RefPanelDisplay, ServerDisplay, display_refpanel, display_server
