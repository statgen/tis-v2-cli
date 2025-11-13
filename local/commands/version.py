"""
Provides the `version` command to print this tool's version.
"""


from dataclasses import dataclass, asdict
from typing import Any

from pretty_cli import PrettyCli

from local.util import get_project_info

from . import base


@dataclass
class VersionArgs(base.Args):
    def run_command(self, cli: PrettyCli) -> None:
        project_info = get_project_info()
        self.output(cli, project_info.version)


def register_version_parser(subparsers: base.Subparser) -> None:
    version = subparsers.add_parser(base.Command.VERSION, help="Print this program's version.")


def parse_version_command(raw_args: Any, global_args: base.Args) -> VersionArgs:
    dict_args = asdict(global_args)
    return VersionArgs(**dict_args)
