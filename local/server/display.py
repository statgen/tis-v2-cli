"""
Provides utilities for pretty-printing server info.
"""


from datetime import datetime
from dataclasses import dataclass

from . import base


@dataclass
class RefPanelDisplay:
    aliases     : list[str] | None
    populations : dict[str, str]


@dataclass
class ServerDisplay:
    url          : str
    aliases      : list[str] | None
    last_updated : datetime
    refpanels    : dict[str, RefPanelDisplay]


def display_refpanel(refpanel: base.RefPanel) -> RefPanelDisplay:
    return RefPanelDisplay(
        aliases     = refpanel.aliases if len(refpanel.aliases) > 0 else None,
        populations = { id: details.display_name for (id, details) in refpanel.populations.items() },
    )

def display_server(server: base.Server) -> ServerDisplay:
    return ServerDisplay(
        url          = server.url,
        aliases      = server.aliases if len(server.aliases) > 0 else None,
        last_updated = server.last_updated,
        refpanels    = { id: display_refpanel(refpanel) for (id, refpanel) in server.refpanels.items() },
    )
