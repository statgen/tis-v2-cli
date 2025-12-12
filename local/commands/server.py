"""
Provides commands for registering and managing servers.
"""


import sys
from enum import StrEnum
from dataclasses import dataclass, asdict
from typing import Any

from pretty_cli import PrettyCli

from local import server

from . import base


class ServerCommand(StrEnum):
    SHOW     = "show"
    REGISTER = "register"


@dataclass
class ServerArgs(base.Args):
    server_command: ServerCommand


@dataclass
class ServerRegister(ServerArgs):
    id  : str
    url : str

    def run_command(self, cli: PrettyCli) -> None:
        try:

            new_server = server.register_server(self.id, self.url) # Add stub to config
            new_server = server.get_server(new_server.id) # Force reaching out to server for initialization.

            display = server.display_server(new_server)
            self.output(cli, display)

        except ValueError as e:
            self.output(cli, e)
            sys.exit(1)



@dataclass
class ServerShow(ServerArgs):
    name: str | None

    def run_command(self, cli: PrettyCli) -> None:
        name = self.name if self.name is not None else ""
        name = server.normalize_name(name)

        try:
            if len(name) > 0:
                details = server.get_server(name)
                display = server.display_server(details)
            else:
                all_servers = server.get_all_servers()
                display = { id: server.display_server(details) for (id, details) in all_servers.items() }

            self.output(cli, display)

        except ValueError as e:
            self.output(cli, e)
            sys.exit(1)


def register_server_parser(subparsers: base.Subparser) -> None:
    server = subparsers.add_parser(base.Command.SERVER, help="Manage registered servers.")
    server_parsers = server.add_subparsers(title="Server Commands", dest="server_command", required=True)

    server_show = server_parsers.add_parser(ServerCommand.SHOW, help="Show registered servers.")
    server_show.add_argument("name", help="ID or alias of a server, shows only info about this server.", type=str, nargs="?")

    server_register = server_parsers.add_parser(ServerCommand.REGISTER, help="Register a new server.")
    server_register.add_argument("name", help="Primary ID to identify this server.", type=str)
    server_register.add_argument("url" , help="Base URL for this server."          , type=str) # TODO: Verify this is an actual URL!


def parse_server_command(raw_args: Any, global_args: base.Args) -> ServerArgs:
    server_command = ServerCommand(raw_args.server_command)

    dict_args = asdict(global_args)
    dict_args["server_command"] = server_command

    match server_command:
        case ServerCommand.REGISTER:
            return ServerRegister(**dict_args, id=raw_args.name, url=raw_args.url)
        case ServerCommand.SHOW:
            return ServerShow(**dict_args, name=raw_args.name)

    assert False, f"Unrecognized server command: {server_command}"
