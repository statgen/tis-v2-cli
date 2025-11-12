from . import lookup


DEFAULT_SERVERS = {
    "topmed-dev" : "https://topmed.dev.imputationserver.org",
    # "topmed"   : "https://imputation.biodatacatalyst.nhlbi.nih.gov",
    "michigan" : "https://imputationserver.sph.umich.edu",
}


def register_defaults() -> None:
    """Initializes the server data and registers the `DEFAULT_SERVERS`. Must run on an uninitialized state."""

    if lookup._servers is not None:
        assert lookup._server_lookup is not None # These two should be synced
        raise Exception("Server data already initialized!")
    assert lookup._server_lookup is None

    lookup._servers       = dict()
    lookup._server_lookup = dict()

    for id, url in DEFAULT_SERVERS.items():
        lookup._register_server_internal(id, url)

    lookup._dump_servers_to_file()
