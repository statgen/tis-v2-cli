"""
Provides user-level commands to query the server for non-job information.
"""

from enum import StrEnum
from dataclasses import dataclass, asdict
from typing import Any

from local.server import Server

from . import base


class QueryCommand(StrEnum):
    SERVER_INFO     = "server-info"
    CALLER_IDENTITY = "caller-identity"


@dataclass
class QueryArgs(base.ApiArgs):
    query_command: QueryCommand


@dataclass
class ServerInfo:
    url                 : str
    name                : str
    email_required      : bool
    maintenance         : bool
    maintenance_message : str | None


@dataclass
class QueryServerInfo(QueryArgs):
    def run_subcommand(self, api: base.TisV2Api) -> None:
        response = api.get_server_info()
        server_info = ServerInfo(
            url                 = self.server.url,
            name                = response.name,
            email_required      = response.email_required,
            maintenance         = response.maintenance,
            maintenance_message = response.maintenance_message,
        )
        self.output(api.cli, server_info)


@dataclass
class QueryCallerIdentity(QueryArgs):
    def run_subcommand(self, api: base.TisV2Api) -> None:
        response = api.get_server_info()
        user = response.user
        assert user is not None # Would mean we're not logged in, which should not be possible.
        self.output(api.cli, response.user)


def register_query_parser(subparsers: base.Subparser) -> None:
    query = subparsers.add_parser(base.Command.QUERY, help="Query the server for general information.")
    query_parsers = query.add_subparsers(title="Query Commands", dest="query_command", required=True)

    server_info = query_parsers.add_parser(QueryCommand.SERVER_INFO, help="Get basic information about the server status.")
    base.register_server_variable(server_info)

    caller_identity = query_parsers.add_parser(QueryCommand.CALLER_IDENTITY, help="Get basic information about your own account.")
    base.register_server_variable(caller_identity)


def parse_query_command(raw_args: Any, global_args: base.Args) -> QueryArgs:
    query_command = QueryCommand(raw_args.query_command)
    server: Server = raw_args.server

    dict_args = asdict(global_args)
    dict_args["query_command"] = query_command
    dict_args["server"] = server

    match query_command:
        case QueryCommand.SERVER_INFO:
            return QueryServerInfo(**dict_args)
        case QueryCommand.CALLER_IDENTITY:
            return QueryCallerIdentity(**dict_args)

    assert False, f"Unrecognized query command: {query_command}"
