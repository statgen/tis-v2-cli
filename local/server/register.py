"""
Provides utilities for registering servers, including the defaults `michigan` and `topmed`.

Provides `register_server()`, `register_defaults()`.
"""


from local.api import TisV2Api
from . import lookup, base


DEFAULT_SERVERS = {
    "topmed-dev" : "https://topmed.dev.imputationserver.org",
    # "topmed"   : "https://imputation.biodatacatalyst.nhlbi.nih.gov",
    "michigan" : "https://imputationserver.sph.umich.edu",
}


def _register_server_internal(id: str, url: str) -> base.Server:
    """Internal version of `register_server()`. Skips server data initialization and dumping to file."""
    assert lookup._servers is not None
    assert lookup._server_lookup is not None

    normalized = lookup.normalize_name(id)

    if normalized in lookup._server_lookup:
        raise ValueError(f"New ID '{id}' already associated with a server (normalized form: '{normalized}'). Aborting server registration.")

    api = TisV2Api(env_name=id, base_url=url)

    refpanel_response = api.list_refpanels()

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

    server = base.Server(
        id              = id,
        url             = url,
        aliases         = [],
        refpanels       = processed_refpanels,
        refpanel_lookup = refpanel_lookup,
    )

    lookup._servers[id] = server
    lookup._server_lookup[normalized] = server

    return server


def register_server(id: str, url: str) -> base.Server:
    """Adds an entry with the given ID and base URL to the server registry. Calls the server to fill in the refpanel basics."""
    lookup._check_servers()
    server = _register_server_internal(id, url)
    lookup._dump_servers_to_file()
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

    lookup._dump_servers_to_file()
