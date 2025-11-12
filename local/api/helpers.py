from local.server.base import Server
from .base import TisV2Api


def get_api(server: str | Server, **kwargs) -> TisV2Api:
    """
    Returns an API instance ready to communicate with the requested `server`.

    If `server` is a string, the server details are loaded from a matching registered server.

    Matches are done against all registered IDs and aliases, with some normalization applied
    (case-insensitive, whitespace and some punctuation ignored). An exception is raised if no
    matches are found.
    """

    # HACK: We need to do this import at runtime to avoid a circular dependency.
    #       We could also move this function outside of local.api, but that just seems wrong.
    from local.server.lookup import get_server

    if isinstance(server, str):
        server = get_server(server)
    assert isinstance(server, Server)

    api = TisV2Api(
        env_name=server.id,
        base_url=server.url,
        **kwargs
    )
    return api
