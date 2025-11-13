"""
Provides admin-level commands.
"""


from getpass import getpass
from datetime import datetime
from pathlib import Path
from enum import StrEnum
from dataclasses import dataclass, asdict
from typing import Any

from local.server import Server
from local.api import TisV2Api
from local.request_schema import AdminListJobsState
from local.util import check_datetime

from . import base


class AdminCommand(StrEnum):
    LOGIN      = "login"
    LIST_USERS = "list-users"
    LIST_JOBS  = "list-jobs"
    KILL_ALL   = "kill-all"


@dataclass
class AdminArgs(base.ApiArgs):
    admin_command: AdminCommand


@dataclass
class AdminLogin(AdminArgs):
    username : str | None
    password : str | None

    def run_subcommand(self, api: TisV2Api) -> None:
        if self.username is None:
            self.username = input("Username: ")
        if self.password is None:
            self.password = getpass()

        response = api.admin_login(self.username, self.password)
        token_path = Path("data") / f"{self.server.id}-admin.token"

        with open(token_path, "w") as file:
            file.write(response.access_token)

        response.access_token = None
        self.output(api.cli, response)


@dataclass
class AdminListUsers(AdminArgs):
    def run_subcommand(self, api: TisV2Api) -> None:
        users = api.admin_list_users()
        self.output(api.cli, users)


@dataclass
class AdminListJobs(AdminArgs):
    states: list[AdminListJobsState]
    start_time : datetime | None
    end_time   : datetime | None

    def run_subcommand(self, api: TisV2Api) -> None:
        jobs = api.admin_list_jobs(self.states)
        jobs = base.filter_jobs(jobs, self.start_time, self.end_time)
        self.output(api.cli, jobs)


@dataclass
class AdminKillAll(AdminArgs):
    def run_subcommand(self, api: TisV2Api) -> None:
        response = api.admin_kill_all()
        self.output(api.cli, response)


def register_admin_parser(subparsers: base.Subparser) -> None:
    admin = subparsers.add_parser(base.Command.ADMIN, help="Issue admin commands")
    admin_parsers = admin.add_subparsers(title="Admin Commands", dest="admin_command", required=True)

    admin_login = admin_parsers.add_parser(AdminCommand.LOGIN, help="Log in to an admin account.")
    base.register_server_variable(admin_login)
    admin_login.add_argument("--username", help="Username for the admin account.", type=str, default=None)
    admin_login.add_argument("--password", help="Password for the admin account.", type=str, default=None)

    admin_list_users = admin_parsers.add_parser(AdminCommand.LIST_USERS, help="List all users.")
    base.register_server_variable(admin_list_users)

    admin_list_jobs = admin_parsers.add_parser(AdminCommand.LIST_JOBS, help="List jobs from all users.")
    base.register_server_variable(admin_list_jobs)
    admin_list_jobs.add_argument("--state"     , help="Job state filter.", choices=[ state for state in AdminListJobsState ], required=True, action="append")
    admin_list_jobs.add_argument("--start-time", help="Only display results for jobs that were running after this time." , type=check_datetime, default=None)
    admin_list_jobs.add_argument("--end-time"  , help="Only display results for jobs that were running before this time.", type=check_datetime, default=None)

    admin_kill_all = admin_parsers.add_parser(AdminCommand.KILL_ALL, help="Cancel all running or waiting jobs.")
    base.register_server_variable(admin_kill_all)


def parse_admin_command(raw_args: Any, global_args: base.Args) -> AdminArgs:
    admin_command = AdminCommand(raw_args.admin_command)
    server: Server = raw_args.server

    dict_args = asdict(global_args)
    dict_args["admin_command"] = admin_command
    dict_args["server"] = server

    match admin_command:
        case AdminCommand.LOGIN:
            return AdminLogin(**dict_args, username=raw_args.username, password=raw_args.password)
        case AdminCommand.LIST_USERS:
            return AdminListUsers(**dict_args)
        case AdminCommand.LIST_JOBS:
            return AdminListJobs(**dict_args, states=raw_args.state, start_time=raw_args.start_time, end_time=raw_args.end_time)
        case AdminCommand.KILL_ALL:
            return AdminKillAll(**dict_args)

    assert False, f"Unrecognized admin command: {admin_command}"
