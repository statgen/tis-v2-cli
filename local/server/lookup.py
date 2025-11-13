"""
Provides server lookup and registration utilities:
    * `get_all_servers()`, `get_server()`.
"""


from pathlib import Path
from typing import Any

import yaml

from local.api.base import TisV2Api
from local.util import flatten_for_storage

from .base import Population, RefPanel, Server, normalize_name
from .register import register_defaults


_servers       : dict[str, Server] | None = None # Canonical mapping: (original ID) -> server
_server_lookup : dict[str, Server] | None = None # Lookup: (any possible NORMALIZED name) -> server


def _get_dict_field(dictionary: dict[str, Any], key: str, value_type: type, key_missing_message: str, value_wrong_type_message: str) -> Any:
    if not key in dictionary:
        raise Exception(f"{key_missing_message} Found keys: {[ k for k in dictionary.keys() ]}")

    value = dictionary[key]

    if not isinstance(value, value_type):
        raise Exception(f"{value_wrong_type_message} Found type: {type(value)}")

    return value


def _load_servers() -> None:
    """Loads server data from file."""

    new_servers       : dict[str, Server] = dict()
    new_server_lookup : dict[str, Server] = dict()
    server_ids        : set[str]          = set()

    # ================================================================ #
    # File Loading
    # ================================================================ #

    data_dir = Path("data")

    if not data_dir.is_dir():
        data_dir.mkdir(parents=False, exist_ok=False)

    servers_file = data_dir / "servers.yaml"

    if not servers_file.is_file():
        register_defaults()
        return

    with open(servers_file, "r") as file_handle:
        data = yaml.load(file_handle, Loader=yaml.SafeLoader)

    # We treat an empty YAML file the same as a missing file.
    if data is None:
        register_defaults()
        return

    # ================================================================ #
    # Data Processing
    # ================================================================ #

    if not isinstance(data, dict):
        raise Exception(f"Expected top-level server configuration object to be a dict, but found: {type(data)}")

    server_data = _get_dict_field(
        dictionary               = data,
        key                      = "servers",
        value_type               = dict,
        key_missing_message      = "Expected top-level server configuration object to contain a 'servers' entry.",
        value_wrong_type_message = "Expected top-level 'servers' entry to be a dict.",
    )

    for server_id, server_details in server_data.items():
        server_id_norm = normalize_name(server_id)

        if server_id_norm in server_ids:
            raise Exception(f"Server ID already present in processed IDs or aliases: '{server_id}' (normalized form: '{server_id_norm}')")

        server_ids.add(server_id_norm)

        if not isinstance(server_details, dict):
            raise Exception(f"Server '{server_id}': Expected server details to be a dict. Found type: {type(server_details)}")

        def _get_server_field(key: str, value_type: type) -> Any:
            return _get_dict_field(
                dictionary=server_details,
                key=key,
                value_type=value_type,
                key_missing_message=f"Server '{server_id}': missing mandatory key '{key}'.",
                value_wrong_type_message=f"Server '{server_id}': field '{key}' should be a {value_type}.",
            )

        server_url = _get_server_field(key="url", value_type=str)

        server_aliases = _get_server_field(key="aliases", value_type=list)

        for alias in server_aliases:
            if not isinstance(alias, str):
                raise Exception(f"Each server alias should be a string. Found type: {type(alias)}")

            alias_norm = normalize_name(alias)

            if alias_norm in server_ids:
                raise Exception(f"Server '{server_id}': Server alias '{alias}' already found in prior server ID or server alias (normalized form: '{alias_norm}').")

            server_ids.add(alias_norm)

        server_refpanels = _get_server_field(key="refpanels", value_type=dict)

        refpanel_ids        : set[str]            = set()
        processed_refpanels : dict[str, RefPanel] = dict()
        refpanel_lookup     : dict[str, RefPanel] = dict()

        for refpanel_id, refpanel_details in server_refpanels.items():
            assert isinstance(refpanel_id, str) # We're assuming it always is so, just double-checking. Otherwise we should throw a descriptive error.

            if refpanel_id in refpanel_ids:
                raise Exception(f"Server '{server_id}': refpanel ID '{refpanel_id}' already used by a previous refpanel ID or alias.")
            refpanel_ids.add(refpanel_id)

            if not isinstance(refpanel_details, dict):
                raise Exception(f"Server '{server_id}'; refpanel '{refpanel_id}': Expected refpanel details to be a dict. Found type: {type(refpanel_details)}")

            def _get_refpanel_field(key: str, value_type: type) -> Any:
                return _get_dict_field(
                    dictionary=refpanel_details,
                    key=key,
                    value_type=value_type,
                    key_missing_message=f"Server '{server_id}'; refpanel '{refpanel_id}': missing mandatory key '{key}'.",
                    value_wrong_type_message=f"Server '{server_id}'; refpanel '{refpanel_id}': field '{key}' should be a {value_type}.",
                )

            refpanel_aliases = _get_refpanel_field(key="aliases", value_type=list)

            for alias in refpanel_aliases:
                if not isinstance(alias, str):
                    raise Exception(f"Server '{server_id}'; refpanel '{refpanel_id}': Each refpanel alias should be a string. Found type: {type(alias)}")

                if alias in refpanel_ids:
                    raise Exception(f"Server '{server_id}'; refpanel: '{refpanel_id}': Refpanel alias '{alias}' already used by a previous refpanel ID or alias.")

                refpanel_ids.add(alias)

            refpanel_populations = _get_refpanel_field(key="populations", value_type=dict)

            processed_populations: dict[str, Population] = dict()

            for population_id, population_details in refpanel_populations.items():
                assert isinstance(population_id, str), f"Server '{server_id}'; refpanel: '{refpanel_id}': population_id should be a string. Found type: {type(population_id)} (value: {population_id})" # We assume it's true

                if not isinstance(population_details, dict):
                    raise Exception(f"Server '{server_id}'; refpanel: '{refpanel_id}': population '{population_id}' should be a dict. Type found: {type(population_details)}")

                population_display_name = _get_dict_field(
                    dictionary               = population_details,
                    key                      = "display-name",
                    value_type               = str,
                    key_missing_message      = f"Server '{server_id}'; refpanel: '{refpanel_id}'; population '{population_id}': missing mandatory field 'display-name'.",
                    value_wrong_type_message = f"Server '{server_id}'; refpanel: '{refpanel_id}'; population '{population_id}': field 'display-name should be a string.",
                )

                population = Population(id=population_id, display_name=population_display_name)

                assert population_id not in processed_populations # Sanity check
                processed_populations[population_id] = population

            refpanel = RefPanel(id=refpanel_id, aliases=refpanel_aliases, populations=processed_populations)
            assert refpanel_id not in processed_refpanels
            processed_refpanels[refpanel_id] = refpanel

            assert refpanel_id not in refpanel_lookup
            refpanel_lookup[refpanel_id] = refpanel
            for alias in refpanel_aliases:
                alias_norm = normalize_name(alias)
                assert alias_norm not in refpanel_lookup
                refpanel_lookup[alias_norm] = refpanel

        server = Server(id=server_id, url=server_url, aliases=server_aliases, refpanels=processed_refpanels, refpanel_lookup=refpanel_lookup)

        assert server_id not in new_servers # Sanity check
        new_servers[server_id] = server

        assert server_id not in new_server_lookup # Sanity check
        new_server_lookup[server_id_norm] = server
        for alias in server.aliases:
            alias_norm = normalize_name(alias)
            assert alias_norm not in new_server_lookup # Sanity check
            new_server_lookup[alias_norm] = server

    global _servers
    global _server_lookup

    _servers       = new_servers
    _server_lookup = new_server_lookup


def _check_servers() -> None:
    """If `_servers` is still `None`, call `load_servers()`."""
    if _servers is None:
        assert _server_lookup is None # If _servers is not loaded, _server_lookup should also not be loaded.
        _load_servers()

    assert _servers is not None # load_servers() should throw or load.
    assert _server_lookup is not None # load_servers() should throw or load.


def get_all_servers() -> dict[str, Server]:
    """Returns a dict mapping (canonical server ID) -> (`Server` data structure) for all registered servers."""
    _check_servers()
    return _servers


def get_server(name: str) -> Server:
    """Matches `name` with any ID or alias from the registered servers. Raises an exception if no match is found."""
    _check_servers()

    name_norm = normalize_name(name)

    if not name_norm in _server_lookup:
        raise ValueError(f"Server not recognized: '{name}' (normalized form: '{name_norm}'). Available values: {[ k for k in _server_lookup.keys() ]}")

    return _server_lookup[name_norm]


def _dump_servers_to_file() -> None:
    """Saves the in-memory server data to the server configuration file."""
    assert _servers is not None
    assert _server_lookup is not None

    data_dir = Path("data")

    if not data_dir.is_dir():
        data_dir.mkdir(parents=False, exist_ok=False)

    servers_file = data_dir / "servers.yaml"
    server_data = { "servers": flatten_for_storage(_servers, skip_keys={ "refpanel-lookup", "id" }) }

    with open(servers_file, "w") as file_handle:
        yaml.safe_dump(server_data, file_handle)
