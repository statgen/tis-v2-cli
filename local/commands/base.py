import json
import argparse
from datetime import datetime
from pathlib import Path
from enum import StrEnum
from dataclasses import dataclass
from typing import TypeAlias, Any

from pretty_cli import PrettyCli

from local.server import Server, get_server
from local.api import TisV2Api
from local.response_schema import JobInfo
from local.util import display, json_default, check_file


Subparser: TypeAlias = argparse._SubParsersAction


class Command(StrEnum):
    VERSION = "version"
    JOB     = "job"
    ADMIN   = "admin"
    SERVER  = "server"


class OutputStyle(StrEnum):
    PRETTY_CLI = "pretty-cli"
    MINIMAL    = "minimal"
    JSON       = "json"


@dataclass
class Args:
    debug        : bool
    output_style : OutputStyle
    token_file   : Path | None
    command      : Command

    def run_command(self, cli: PrettyCli) -> None:
        raise NotImplementedError()

    def output(self, cli: PrettyCli, data: Any) -> None:
        match self.output_style:
            case OutputStyle.PRETTY_CLI:
                display(cli, data)
            case OutputStyle.MINIMAL:
                pass
            case OutputStyle.JSON:
                cli.print(json.dumps(data, ensure_ascii=False, indent=4, default=json_default))


@dataclass
class ApiArgs(Args):
    server: Server

    def run_command(self, cli: PrettyCli) -> None:
        print_http_call = False if (self.output_style == OutputStyle.JSON) else True

        api = TisV2Api(
            env_name = self.server.id,
            base_url = self.server.url,
            cli      = cli,

            print_http_call        = print_http_call,
            print_request_headers  = self.debug,
            print_request_body     = self.debug,
            print_response_headers = self.debug,
            print_response_body    = self.debug,

            token_file = self.token_file,
        )

        self.run_subcommand(api)

    def run_subcommand(self, api: TisV2Api) -> None:
        raise NotImplementedError()


def filter_jobs(
    jobs       : list[JobInfo],
    start_time : datetime | None = None,
    end_time   : datetime | None = None,
    user       : str      | None = None,
) -> list[JobInfo]:

    filtered = []

    for j in jobs:

        if start_time:
            if j.end_time < start_time:
                continue

        if end_time:
            if j.start_time > end_time:
                continue

        if user:
            if j.username != user:
                continue

        filtered.append(j)

    return filtered


def register_base_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--debug"     , help="Activates additional debug printing."                                      , action="store_true")
    parser.add_argument("--token-file", help="Path to a text file containing the authentication token.", type=check_file , default=None)
    parser.add_argument("--output"    , help="Output format (default: pretty-print)"                   , type=OutputStyle, choices=[ style for style in OutputStyle ], default=OutputStyle.PRETTY_CLI, dest="output_style")


def register_server_variable(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("server", help="The server that this request will be sent to.", type=get_server)
