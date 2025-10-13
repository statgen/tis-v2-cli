#!/bin/env python3


import sys
import json
import argparse
import time
from getpass import getpass
from datetime import datetime
from pathlib import Path
from enum import StrEnum
from dataclasses import dataclass

from pretty_cli import PrettyCli

from local.api import TisV2Api
from local.env import Environment
from local.request_schema import JobParams, Build, Phasing, Mode, AdminListJobsState
from local.response_schema import JobInfo
from local.util import display, check_file, late_check_refpanel, check_datetime, json_default, get_project_info


class Command(StrEnum):
    LIST_JOBS      = "list-jobs"
    GET_JOB        = "get-job"
    SUBMIT_JOB     = "submit-job"
    CANCEL_JOB     = "cancel-job"
    RESTART_JOB    = "restart-job"
    LIST_REFPANELS = "list-refpanels"
    DOWNLOAD       = "download"
    ADMIN          = "admin"


class AdminCommand(StrEnum):
    LOGIN      = "login"
    LIST_USERS = "list-users"
    LIST_JOBS  = "list-jobs"
    KILL_ALL   = "kill-all"


class OutputStyle(StrEnum):
    PRETTY_CLI = "pretty-cli"
    MINIMAL    = "minimal"
    JSON       = "json"


@dataclass
class Args:
    env          : Environment
    debug        : bool
    repeat       : int
    delay        : float
    output_style : OutputStyle
    token_file   : Path | None
    command      : Command

    def run_command(self, api: TisV2Api) -> None:
        raise NotImplementedError()

    def output(self, api: TisV2Api, data) -> None:
        match self.output_style:
            case OutputStyle.PRETTY_CLI:
                if isinstance(data, list):
                    for entry in data:
                        display(api.cli, entry)
                else:
                    display(api.cli, data)
            case OutputStyle.MINIMAL:
                pass
            case OutputStyle.JSON:
                api.cli.print(json.dumps(data, ensure_ascii=False, indent=4, default=json_default))


def filter_jobs(
    jobs       : list[JobInfo],
    start_time : datetime | None = None,
    end_time   : datetime | None = None,
) -> list[JobInfo]:
    filtered = []

    for j in jobs:
        if start_time:
            if j.end_time < start_time:
                continue
        if end_time:
            if j.start_time > end_time:
                continue
        filtered.append(j)

    return filtered


@dataclass
class ListJobsArgs(Args):
    start_time : datetime | None
    end_time   : datetime | None

    def run_command(self, api: TisV2Api) -> None:
        jobs = api.list_jobs()
        jobs = filter_jobs(jobs, self.start_time, self.end_time)
        self.output(api, jobs)


@dataclass
class GetJobArgs(Args):
    job_id: str

    def run_command(self, api: TisV2Api) -> None:
        job = api.get_job(self.job_id)
        self.output(api, job)


@dataclass
class CancelJobArgs(Args):
    job_id: str

    def run_command(self, api: TisV2Api) -> None:
        job = api.cancel_job(self.job_id)
        self.output(api, job)


@dataclass
class RestartJobArgs(Args):
    job_id: str

    def run_command(self, api: TisV2Api) -> None:
        response = api.restart_job(self.job_id)
        self.output(api, response)


@dataclass
class SubmitJobArgs(Args):
    job_params: JobParams

    def run_command(self, api: TisV2Api) -> None:
        response = api.submit_job(self.job_params)
        self.output(api, response)


@dataclass
class ListRefpanelsArgs(Args):
    def run_command(self, api: TisV2Api) -> None:
        response = api.list_refpanels()
        self.output(api, response)


@dataclass
class DownloadArgs(Args):
    download_dir: Path
    job_id: str

    def run_command(self, api: TisV2Api) -> None:
        response = api.download(self.download_dir, self.job_id)
        self.output(api, response)


@dataclass
class AdminArgs(Args):
    admin_command: AdminCommand


@dataclass
class AdminLogin(AdminArgs):
    username : str | None
    password : str | None

    def run_command(self, api: TisV2Api) -> None:
        if self.username is None:
            self.username = input("Username:")
        if self.password is None:
            self.password = getpass()

        response = api.admin_login(self.username, self.password)
        token_path = Path("data") / f"{self.env}-admin.token"

        with open(token_path, "w") as file:
            file.write(response.access_token)

        response.access_token = None
        self.output(api, response)


@dataclass
class AdminListUsers(AdminArgs):

    def run_command(self, api: TisV2Api) -> None:
        users = api.admin_list_users()
        self.output(api, users)


@dataclass
class AdminListJobs(AdminArgs):
    states: list[AdminListJobsState]
    start_time : datetime | None
    end_time   : datetime | None

    def run_command(self, api: TisV2Api) -> None:
        jobs = api.admin_list_jobs(self.states)
        jobs = filter_jobs(jobs, self.start_time, self.end_time)
        self.output(api, jobs)


@dataclass
class AdminKillAll(AdminArgs):
    def run_command(self, api: TisV2Api) -> None:
        response = api.admin_kill_all()
        self.output(api, response)


def parse_arguments() -> Args:
    parser = argparse.ArgumentParser(description="Query the TOPMed Imputation Server API")

    # This argument is a dummy. To avoid messing with the current structure, -v and --version are handled manually before parsing arguments.
    parser.add_argument("-v", "--version", help="Print script version and exit.", action="store_true")

    parser.add_argument("env"         , help="Target environment."                                     , type=str        , choices=[env for env in Environment])
    parser.add_argument("--debug"     , help="Activates additional debug printing."                                      , action="store_true")
    parser.add_argument("--repeat"    , help="Number of times to repeat the requested call."           , type=int        , default=1)
    parser.add_argument("--delay"     , help="Time in seconds to wait before performing the call."     , type=float      , default=0.0)
    parser.add_argument("--token-file", help="Path to a text file containing the authentication token.", type=check_file , default=None)
    parser.add_argument("--output"    , help="Output format (default: pretty-print)"                   , type=OutputStyle, choices=[ style for style in OutputStyle ], default=OutputStyle.PRETTY_CLI, dest="output_style")

    subparsers = parser.add_subparsers(title="Commands", dest="command", required=True)

    list_jobs = subparsers.add_parser(Command.LIST_JOBS, help="List all of the user's jobs.")
    list_jobs.add_argument("--start-time", help="Only display results for jobs that were running after this time." , type=check_datetime, default=None)
    list_jobs.add_argument("--end-time"  , help="Only display results for jobs that were running before this time.", type=check_datetime, default=None)

    get_job = subparsers.add_parser(Command.GET_JOB, help="Get one job visible by the user, by ID.")
    get_job.add_argument("job_id", help="ID of the job to retrieve")

    cancel_job = subparsers.add_parser(Command.CANCEL_JOB, help="Cancel one job visible by the user, by ID.")
    cancel_job.add_argument("job_id", help="ID of the job to cancel")

    restart_job = subparsers.add_parser(Command.RESTART_JOB, help="Restart one job visible by the user, by ID.")
    restart_job.add_argument("job_id", help="ID of the job to retry")

    submit_job = subparsers.add_parser(Command.SUBMIT_JOB, help="Submit a job for processing.")
    submit_job.add_argument("-f", "--file"      , help="VCF file to upload for testing. Repeat for a multi-file upload."      , type=check_file, required=True, action="append")
    submit_job.add_argument("-r", "--refpanel"  , help="Reference panel used for imputation."                                 , type=str       , required=True)
    submit_job.add_argument("-b", "--build"     , help="Data format (HG19 vs. HG38)"                                          , type=Build     , required=True)
    submit_job.add_argument("-n", "--name"      , help="Optional name for this job (will be assigned a unique ID regardless).", type=str       , default=None)
    submit_job.add_argument("-R", "--r2-filter" , help="rsq filter. Set to 0 or leave blank for none"                         , type=float     , default=0.0)
    submit_job.add_argument("-p", "--phasing"   , help="Phasing engine to use."                                               , type=Phasing   , default=Phasing.EAGLE)
    submit_job.add_argument("-P", "--population", help="Reference population used for the allele frequency check"             , type=str       , default=None)
    submit_job.add_argument("-m", "--mode"      , help="Run QC only, or do QC + Imputation."                                  , type=Mode      , default=Mode.IMPUTATION)

    list_refpanels = subparsers.add_parser(Command.LIST_REFPANELS, help="List the available reference panels in the selected environment.")

    download = subparsers.add_parser(Command.DOWNLOAD, help="Download all files for the given job.")
    download.add_argument("--download-dir", help="Directory used for file downloads. If the job contains outputs, a sub-dir named <job-id>/ will be created, and used to store all outputs.", type=Path, default=Path(".").resolve())
    download.add_argument("job_id", help="ID of the job to download.")

    admin = subparsers.add_parser(Command.ADMIN, help="Issue admin commands")
    admin_parsers = admin.add_subparsers(title="Admin Commands", dest="admin_command", required=True)

    admin_login = admin_parsers.add_parser(AdminCommand.LOGIN, help="Log in to an admin account.")
    admin_login.add_argument("--username", help="Username for the admin account.", type=str, default=None)
    admin_login.add_argument("--password", help="Password for the admin account.", type=str, default=None)

    admin_list_users = admin_parsers.add_parser(AdminCommand.LIST_USERS, help="List all users.")

    admin_list_jobs = admin_parsers.add_parser(AdminCommand.LIST_JOBS, help="List jobs from all users.")
    admin_list_jobs.add_argument("--state"     , help="Job state filter.", choices=[ state for state in AdminListJobsState ], required=True, action="append")
    admin_list_jobs.add_argument("--start-time", help="Only display results for jobs that were running after this time." , type=check_datetime, default=None)
    admin_list_jobs.add_argument("--end-time"  , help="Only display results for jobs that were running before this time.", type=check_datetime, default=None)

    admin_kill_all = admin_parsers.add_parser(AdminCommand.KILL_ALL, help="Cancel all running or waiting jobs.")

    args = parser.parse_args()

    env = Environment(args.env)
    command = Command(args.command)

    global_args = {
        "env"          : env,
        "debug"        : args.debug,
        "repeat"       : args.repeat,
        "delay"        : args.delay,
        "output_style" : args.output_style if (args.output_style is not None) else OutputStyle.PRETTY_CLI,
        "token_file"   : args.token_file,
        "command"      : command,
    }

    match command:
        case Command.LIST_JOBS:
            return ListJobsArgs(**global_args, start_time=args.start_time, end_time=args.end_time)
        case Command.GET_JOB:
            return GetJobArgs(**global_args, job_id=args.job_id)
        case Command.CANCEL_JOB:
            return CancelJobArgs(**global_args, job_id=args.job_id)
        case Command.RESTART_JOB:
            return RestartJobArgs(**global_args, job_id=args.job_id)
        case Command.LIST_REFPANELS:
            return ListRefpanelsArgs(**global_args)
        case Command.DOWNLOAD:
            return DownloadArgs(**global_args, download_dir=args.download_dir, job_id=args.job_id)
        case Command.SUBMIT_JOB:
            refpanel = late_check_refpanel(submit_job, env, args.refpanel)

            job_params = JobParams(
                job_name   = args.name,
                refpanel   = refpanel,
                build      = args.build,
                r2_filter  = args.r2_filter,
                phasing    = args.phasing,
                population = args.population,
                mode       = args.mode,
                files      = args.file,
            )
            return SubmitJobArgs(**global_args, job_params=job_params)

        case Command.ADMIN:
            admin_command = AdminCommand(args.admin_command)
            global_args["admin_command"] = admin_command

            match admin_command:
                case AdminCommand.LOGIN:
                    return AdminLogin(**global_args, username=args.username, password=args.password)
                case AdminCommand.LIST_USERS:
                    return AdminListUsers(**global_args)
                case AdminCommand.LIST_JOBS:
                    return AdminListJobs(**global_args, states=args.state, start_time=args.start_time, end_time=args.end_time)
                case AdminCommand.KILL_ALL:
                    return AdminKillAll(**global_args)

            assert False, f"Unrecognized admin command: {admin_command}"

    assert False, f"Unrecognized command: {command}"


def main() -> None:
    cli = PrettyCli()

    # Version printing handled separately because it would be very messy to integrate with the existing flow.
    if len(sys.argv) == 2 and sys.argv[1] in [ "-v", "--version" ]:
        project_info = get_project_info()
        cli.print(project_info.version)
        return

    args = parse_arguments()

    api = TisV2Api(
        env = args.env,
        cli = cli,
        print_http_call = False if (args.output_style == OutputStyle.JSON) else True,
        print_request_headers  = args.debug,
        print_request_body     = args.debug,
        print_response_headers = args.debug,
        print_response_body    = args.debug,
        token_file             = args.token_file,
    )

    if args.repeat < 1:
        return

    for _ in range(args.repeat):
        if args.delay > 0:
            time.sleep(args.delay)

        args.run_command(api)


if __name__ == "__main__":
    main()
