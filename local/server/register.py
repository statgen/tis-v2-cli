"""
Provides utilities for registering servers, including the defaults `michigan` and `topmed`.

Provides `register_server()`, `register_defaults()`.
"""


from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse

from local.api import TisV2Api

from . import lookup, base


DEFAULT_SERVERS = {
    "topmed"   : "https://imputation.biodatacatalyst.nhlbi.nih.gov",
    "michigan" : "https://imputationserver.sph.umich.edu",
}


def force_server_update(server: base.Server) -> None:
    """
    Updates the given server's reference panels (including their populations).

    Calls the server to collect this information.
    """

    start_time = datetime.now()

    # TODO: We should propagate `cli` and verbosity params from upstream!
    api = TisV2Api(env_name=server.id, base_url=server.url)
    refpanel_response = api.list_refpanels()
    assert len(refpanel_response) > 0

    processed_refpanels : dict[str, base.RefPanel] = dict()
    refpanel_lookup     : dict[str, base.RefPanel] = dict()

    for raw in refpanel_response:
        populations = { pop.api_name: base.Population(id=pop.api_name, display_name=pop.display_name) for pop in raw.populations }
        processed = base.RefPanel(id=raw.api_name, aliases=[], populations=populations)

        assert processed.id not in processed_refpanels
        processed_refpanels[processed.id] = processed

        normalized_repanel_id = lookup.normalize_name(processed.id)
        assert normalized_repanel_id not in refpanel_lookup
        refpanel_lookup[normalized_repanel_id] = processed

    for refpanel_id in processed_refpanels:
        if refpanel_id in server.refpanels:
            new_refpanel = processed_refpanels[refpanel_id]
            old_refpanel = server.refpanels[refpanel_id]

            if len(old_refpanel.aliases) > 0:
                new_refpanel.aliases = old_refpanel.aliases

    server.refpanels       = processed_refpanels
    server.refpanel_lookup = refpanel_lookup
    server.last_updated    = start_time


def maybe_update_server(server: base.Server) -> bool:
    """
    Checks if the server has been updated recently. If not, calls `_force_server_update()`
    to query the server and get fresh refpanel information (including populations).

    Returns `True` if the server has been updated, `False` otherwise.
    """

    now = datetime.now()

    if (now - server.last_updated) > timedelta(days=7):
        force_server_update(server)
        return True

    return False


def _register_server_internal(id: str, url: str) -> base.Server:
    """
    Internal version of `register_server()`.
    Skips server data initialization and dumping to file.
    """

    assert lookup._servers is not None
    assert lookup._server_lookup is not None

    id_norm = lookup.normalize_name(id)

    if id_norm in lookup._server_lookup:
        raise ValueError(f"New ID '{id}' already associated with a server (normalized form: '{id_norm}'). Aborting server registration.")

    url_parts = urlparse(url)

    if len(url_parts.netloc) < 1:
        raise ValueError(f"Submitted URL is malformed: {url}")

    url_clean = urlunparse(("https", url_parts.netloc, "", "", "", ""))

    server = base.Server(
        id              = id,
        url             = url_clean,
        aliases         = [],
        last_updated    = datetime.fromtimestamp(0), # Unix epoch (we just need something clearly out of date)
        refpanels       = {},
        refpanel_lookup = {},
    )

    lookup._servers[id] = server
    lookup._server_lookup[id_norm] = server

    return server


def register_server(id: str, url: str) -> base.Server:
    """Adds an entry with the given ID and base URL to the server registry. Calls the server to fill in the refpanel basics."""
    lookup._check_servers()
    server = _register_server_internal(id, url)
    lookup.dump_servers_to_file()
    return server


def register_defaults() -> None:
    """Initializes the server data and registers the `DEFAULT_SERVERS`. Must run on an uninitialized state."""

    if lookup._servers is not None:
        assert lookup._server_lookup is not None # These two should be synced
        raise Exception("Server data already initialized!")
    assert lookup._server_lookup is None

    lookup._servers       = dict()
    lookup._server_lookup = dict()

    for id, url in DEFAULT_SERVERS.items():
        _register_server_internal(id, url)

    lookup.dump_servers_to_file()
